from aws_cdk import aws_logs
from aws_cdk import core
from aws_cdk.core import RemovalPolicy

from baseline_cdk.util import cdk


def create(stack: core.Stack) -> None:
    things_log_group = aws_logs.CfnLogGroup(
        stack, 'ThingsLogGroup',
        log_group_name=f'{cdk.app_name}/things',
        retention_in_days=7,
    )

    things_log_group.apply_removal_policy(policy=RemovalPolicy.DESTROY)
