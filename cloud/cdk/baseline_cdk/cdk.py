import os

from aws_cdk import core

import baseline_cdk.resources.api_gateway
import baseline_cdk.resources.cfnres_iot_cacert
import baseline_cdk.resources.cfnres_iot_cert
import baseline_cdk.resources.cfnres_iot_fleet
import baseline_cdk.resources.cfnres_iot_thinggroup
import baseline_cdk.resources.cfnres_iot_thingtype
import baseline_cdk.resources.cloudfront
import baseline_cdk.resources.cloudwatch
import baseline_cdk.resources.cognito
import baseline_cdk.resources.iot_policy
import baseline_cdk.resources.iot_topic
import baseline_cdk.resources.lambda_apis
import baseline_cdk.resources.lambda_authorizer
import baseline_cdk.resources.lambda_ingest
import baseline_cdk.resources.redis
import baseline_cdk.resources.s3
import baseline_cdk.resources.secrets
import baseline_cdk.resources.ssm
import baseline_cdk.resources.vpc
import baseline_cdk.util.date
from baseline_cdk import resources
from baseline_cdk import util
from baseline_cdk.util import cdk

app = core.App()

cdk.app_name = app.node.try_get_context('app_name')
cdk.topic_prefix = app.node.try_get_context('topic_prefix')
cdk.account = os.environ['CDK_DEFAULT_ACCOUNT']
cdk.region = os.environ['CDK_DEFAULT_REGION']
cdk.outdir = os.environ['CDK_OUTDIR']
cdk.availability_zones = 1
cdk.debug_lambda_roles = app.node.try_get_context('debug_lambda_roles')

stack = core.Stack(
    app, 'Stack',
    stack_name=cdk.app_name,
    env=core.Environment(
        account=cdk.account,
        region=cdk.region
    ),
    tags={
        'baseline:user': os.getlogin(),
        'baseline:date': util.date.utcnow()
    }
)

resources.vpc.create(stack)
resources.cognito.create(stack)
resources.lambda_authorizer.create(stack)
resources.lambda_apis.create(stack)
resources.lambda_ingest.create(stack)
resources.api_gateway.create(stack)
resources.redis.create(stack)
resources.s3.create(stack)
resources.cloudfront.create(stack)
resources.iot_policy.create(stack)
resources.iot_topic.create(stack)
resources.cfnres_iot_thingtype.create(stack)
resources.cfnres_iot_thinggroup.create(stack)
resources.cfnres_iot_cacert.create(stack)
resources.cfnres_iot_cert.create(stack)
resources.cfnres_iot_fleet.create(stack)
resources.cloudwatch.create(stack)
resources.secrets.create(stack)
resources.ssm.create(stack)

app.synth()
