from aws_cdk import aws_ec2
from aws_cdk import aws_elasticache
from aws_cdk import core

from baseline_cdk.util import cdk


def create(stack: core.Stack) -> None:
    redis_scope = core.Construct(stack, 'Redis')

    vpc: aws_ec2.CfnVPC = cdk.find_resource(stack, 'Vpc')
    vpc_subnets = cdk.select_subnets(vpc, aws_ec2.SubnetType.PRIVATE)

    redis_security_group = aws_ec2.CfnSecurityGroup(
        redis_scope, 'SecurityGroup',
        group_name=f'{cdk.app_name}-redis',
        group_description=f'{cdk.app_name}-redis',
        security_group_ingress=[
            aws_ec2.CfnSecurityGroup.IngressProperty(
                description='Allow all inbound tcp traffic on port 6379',
                cidr_ip='0.0.0.0/0',
                ip_protocol='tcp',
                from_port=6379,
                to_port=6379
            )
        ],
        security_group_egress=[
            aws_ec2.CfnSecurityGroup.EgressProperty(
                description='Allow all outbound traffic by default',
                cidr_ip='0.0.0.0/0',
                ip_protocol='-1'
            )
        ],
        vpc_id=vpc.ref,
        tags=[core.CfnTag(key='Name', value=f'{cdk.app_name}-redis')]
    )

    redis_subnet_group = aws_elasticache.CfnSubnetGroup(
        redis_scope, 'SubnetGroup',
        description=cdk.app_name,
        subnet_ids=[subnet.ref for subnet in vpc_subnets],
        cache_subnet_group_name=cdk.app_name
    )

    aws_elasticache.CfnCacheCluster(
        redis_scope, 'CacheCluster',
        cluster_name=cdk.app_name,
        engine='redis',
        cache_node_type='cache.t3.micro',
        num_cache_nodes=1,
        port=6379,
        vpc_security_group_ids=[redis_security_group.ref],
        cache_subnet_group_name=redis_subnet_group.ref
    )
