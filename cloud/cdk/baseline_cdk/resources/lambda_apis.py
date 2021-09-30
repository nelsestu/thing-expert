import fnmatch
import json
import os
import zipfile

from aws_cdk import aws_ec2
from aws_cdk import aws_iam
from aws_cdk import aws_lambda
from aws_cdk import aws_logs
from aws_cdk import core
from aws_cdk.core import RemovalPolicy

import baseline_cdk.util.dict
from baseline_cdk import util
from baseline_cdk.util import cdk
from baseline_cdk.util.hash import file_sha1
from baseline_cdk.util.os import shell
from baseline_cdk.util.zip import exclude_pycache
from baseline_cdk.util.zip import zip_all

lambda_type = 'apis'


def create_layer_zip() -> str:
    this_dir = os.path.abspath(os.path.dirname(os.path.abspath(__file__)))
    cloud_dir = os.path.abspath(f'{this_dir}/../../..')

    layer_dir = f'{cdk.outdir}/{cdk.app_name}/lambda-{lambda_type}-layer'
    layer_zip = f'{cdk.outdir}/{cdk.app_name}/lambda-{lambda_type}-layer.zip'

    if not os.path.exists(layer_dir):
        os.makedirs(layer_dir)

    shell(f'bash {cloud_dir}/scripts/aws-lambda-pip.sh'
          f'  -pyver 3.8'
          f'  -out "{layer_dir}/python/lib/python3.8/site-packages"'
          f'  -req "{this_dir}/lambda_{lambda_type}.txt"')

    with zipfile.ZipFile(layer_zip, 'w', zipfile.ZIP_DEFLATED) as zip:
        zip_all(zip, f'{layer_dir}', exclude_pycache, path='python')

    return layer_zip


def create_lambda_zip() -> str:
    this_dir = os.path.abspath(os.path.dirname(os.path.abspath(__file__)))
    cloud_dir = os.path.abspath(f'{this_dir}/../../..')

    lambda_dir = f'{cdk.outdir}/{cdk.app_name}/lambda-{lambda_type}'
    lambda_zip = f'{cdk.outdir}/{cdk.app_name}/lambda-{lambda_type}.zip'

    if not os.path.exists(lambda_dir):
        os.makedirs(lambda_dir)

    with open(f'{cloud_dir}/config.json', 'r') as fin:
        config = json.load(fin)
        with open(f'{lambda_dir}/config.json', 'w') as fout:
            json.dump(util.dict.deep_update({
                'app_name': cdk.app_name,
                'topic_prefix': cdk.topic_prefix
            }, config), fout, sort_keys=True)

    def exclude_source(file: str) -> bool:
        return file != f'{cloud_dir}/src/baseline_cloud' and \
               file.rsplit(sep='/', maxsplit=1)[0] != f'{cloud_dir}/src/baseline_cloud' and \
               not fnmatch.fnmatch(file, f'{cloud_dir}/src/baseline_cloud/{lambda_type}/*') and \
               not fnmatch.fnmatch(file, f'{cloud_dir}/src/baseline_cloud/core/*')

    with zipfile.ZipFile(lambda_zip, 'w', zipfile.ZIP_DEFLATED) as zip:
        zip_all(zip, f'{cloud_dir}/src', exclude_source, exclude_pycache)
        zip.write(f'{lambda_dir}/config.json', arcname='config.json')

    return lambda_zip


def create(stack: core.Stack) -> None:
    lambda_scope = core.Construct(stack, 'ApisLambda')

    vpc: aws_ec2.CfnVPC = cdk.find_resource(stack, 'Vpc')
    vpc_subnets = cdk.select_subnets(vpc, aws_ec2.SubnetType.PRIVATE)

    layer_zip = create_layer_zip()
    lambda_zip = create_lambda_zip()

    layer_asset = stack.synthesizer.add_file_asset(
        file_name=layer_zip,
        packaging=core.FileAssetPackaging.FILE,
        source_hash=file_sha1(layer_zip)
    )

    lambda_asset = stack.synthesizer.add_file_asset(
        file_name=lambda_zip,
        packaging=core.FileAssetPackaging.FILE,
        source_hash=file_sha1(lambda_zip)
    )

    lambda_role = aws_iam.CfnRole(
        lambda_scope, 'ExecutionRole',
        role_name=f'{cdk.app_name}-lambda-{lambda_type}',
        assume_role_policy_document={
            'Version': '2012-10-17',
            'Statement': [{
                'Effect': 'Allow',
                'Action': 'sts:AssumeRole',
                'Principal': {
                    'Service': 'lambda.amazonaws.com',
                    **({'AWS': f'arn:aws:iam::{stack.account}:root'} if cdk.debug_lambda_roles else {})
                }
            }]
        },
        managed_policy_arns=[
            'arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole'
        ],
        policies=[aws_iam.CfnRole.PolicyProperty(
            policy_name=f'{cdk.app_name}-lambda-{lambda_type}',
            policy_document={
                'Version': '2012-10-17',
                'Statement': [{
                    'Effect': 'Allow',
                    'Action': [
                        'iot:DescribeThing',
                        'iot:ListThingsInThingGroup',
                        'secretsmanager:GetSecretValue',
                        'ssm:GetParameter',
                        'ssm:GetParameters'
                    ],
                    'Resource': '*'
                }]
            }
        )]
    )

    lambda_security_group = aws_ec2.CfnSecurityGroup(
        lambda_scope, 'SecurityGroup',
        group_name=f'{cdk.app_name}-lambda-{lambda_type}',
        group_description=f'{cdk.app_name}-lambda-{lambda_type}',
        security_group_egress=[
            aws_ec2.CfnSecurityGroup.EgressProperty(
                description='Allow all outbound traffic by default',
                cidr_ip='0.0.0.0/0',
                ip_protocol='-1'
            )
        ],
        vpc_id=vpc.ref,
        tags=[core.CfnTag(key='Name', value=f'{cdk.app_name}-lambda-{lambda_type}')]
    )

    lambda_layer = aws_lambda.CfnLayerVersion(
        lambda_scope, 'Layer',
        layer_name=f'{cdk.app_name}-{lambda_type}',
        compatible_runtimes=['python3.8'],
        content=aws_lambda.CfnLayerVersion.ContentProperty(
            s3_bucket=layer_asset.bucket_name,
            s3_key=layer_asset.object_key
        )
    )

    lambda_function = aws_lambda.CfnFunction(
        lambda_scope, 'Function',
        function_name=f'{cdk.app_name}-{lambda_type}',
        runtime='python3.8',
        code=aws_lambda.CfnFunction.CodeProperty(
            s3_bucket=lambda_asset.bucket_name,
            s3_key=lambda_asset.object_key
        ),
        handler=f'baseline_cloud.{lambda_type}.handler.handle',
        layers=[lambda_layer.ref],
        memory_size=128,
        timeout=30,
        role=lambda_role.attr_arn,
        vpc_config=aws_lambda.CfnFunction.VpcConfigProperty(
            subnet_ids=[subnet.ref for subnet in vpc_subnets],
            security_group_ids=[
                lambda_security_group.attr_group_id
            ]
        )
    )

    lambda_function.add_depends_on(lambda_security_group)
    lambda_function.add_depends_on(lambda_role)

    lambda_log_group = aws_logs.CfnLogGroup(
        lambda_scope, 'LogGroup',
        log_group_name=f'/aws/lambda/{lambda_function.ref}',
        retention_in_days=7,
    )

    lambda_log_group.apply_removal_policy(policy=RemovalPolicy.DESTROY)
