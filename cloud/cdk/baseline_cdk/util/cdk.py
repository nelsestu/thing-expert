import typing

import jsii
from aws_cdk import aws_ec2
from aws_cdk import core


def find_resource(scope: core.Construct, path: str) -> typing.Any:
    resource = scope
    for id in path.split('/'):
        resource = resource.node.try_find_child(id)
        if not resource: break
    return resource


def find_resources(scope: core.Construct, cls: typing.Any) -> typing.List[typing.Any]:
    resources: typing.List[typing.Type[core.Construct]] = []
    resource: typing.Type[core.Construct]
    for resource in scope.node.children:
        if isinstance(resource, cls):
            resources.append(resource)
        resources.extend(find_resources(resource, cls))
    return resources


def select_subnets(scope: core.Construct, subnet_type: aws_ec2.SubnetType) -> typing.List[aws_ec2.CfnSubnet]:
    subnets: typing.List[aws_ec2.CfnSubnet] = []
    subnet: aws_ec2.CfnSubnet
    for subnet in find_resources(scope, aws_ec2.CfnSubnet):
        if get_metadata(subnet, 'aws-cdk:subnet-type') == subnet_type.name:
            subnets.append(subnet)
    return subnets


def get_metadata(scope: core.Construct, key: str) -> typing.Any:
    for metadata in scope.node.metadata:
        if key == metadata.type: return metadata.data
    return None


def lazy_string_value(key: str):
    @jsii.implements(core.IStringProducer)
    class Producer:
        def produce(self, context):
            return lazy_values.get(key)

    # noinspection PyTypeChecker
    return core.Lazy.string_value(Producer())


lazy_values: typing.Dict[str, typing.Any] = {}

app_name: str
topic_prefix: str
account: str
region: str
outdir: str
availability_zones: int
debug_lambda_roles: bool
