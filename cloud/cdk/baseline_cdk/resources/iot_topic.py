from aws_cdk import aws_iam
from aws_cdk import aws_iot
from aws_cdk import aws_lambda
from aws_cdk import core

from baseline_cdk.util import cdk


def create(stack: core.Stack) -> None:
    iot_scope = cdk.find_resource(stack, 'Iot')
    if not iot_scope: iot_scope = core.Construct(stack, 'Iot')

    lambda_function: aws_lambda.CfnFunction = cdk.find_resource(stack, 'IngestLambda/Function')

    republish_role = aws_iam.CfnRole(
        iot_scope, 'MqttRepublishRole',
        role_name=f'{cdk.app_name}-mqtt-republish',
        assume_role_policy_document={
            'Version': '2012-10-17',
            'Statement': [{
                'Effect': 'Allow',
                'Action': 'sts:AssumeRole',
                'Principal': {
                    'Service': 'iot.amazonaws.com'
                }
            }]
        },
        policies=[aws_iam.CfnRole.PolicyProperty(
            policy_name=f'{cdk.app_name}-mqtt-republish',
            policy_document={
                'Version': '2012-10-17',
                'Statement': [{
                    'Effect': 'Allow',
                    'Action': 'iot:Publish',
                    'Resource': f'arn:aws:iot:{stack.region}:{stack.account}:topic/{cdk.topic_prefix}/*'
                }]
            }
        )]
    )

    # noinspection SqlDialectInspection
    # noinspection SqlNoDataSourceInspection
    topic_rule = aws_iot.CfnTopicRule(
        iot_scope, 'TopicRule',
        rule_name=cdk.topic_prefix,
        topic_rule_payload=aws_iot.CfnTopicRule.TopicRulePayloadProperty(
            aws_iot_sql_version='2016-03-23',
            sql='\n'.join([
                f'select concat("$aws/rules/{cdk.topic_prefix}/", topic()) as topic,',
                f'       traceid() as traceId,',
                f'       clientid() as clientId,',
                f'       principal() as principal,',
                f'       *',
                f' where not endswith(topic(), "/accepted")',
                f'   and not endswith(topic(), "/rejected")',
            ]),
            actions=[aws_iot.CfnTopicRule.ActionProperty(
                lambda_=aws_iot.CfnTopicRule.LambdaActionProperty(
                    function_arn=lambda_function.attr_arn
                )
            )],
            error_action=aws_iot.CfnTopicRule.ActionProperty(
                republish=aws_iot.CfnTopicRule.RepublishActionProperty(
                    role_arn=republish_role.attr_arn,
                    topic=f'{cdk.topic_prefix}/${{topic()}}/rejected',
                    qos=1
                )
            ),
            rule_disabled=False
        )
    )

    topic_rule.add_depends_on(lambda_function)
    topic_rule.add_depends_on(republish_role)


def strip_sides(s: str) -> str:
    lines = []
    cutoff = None
    for line in s.split('\n'):
        if not line: continue
        if not cutoff:
            l = line.strip()
            cutoff = len(line) - len(l)
            print(cutoff)
        else:
            l = line[cutoff:]
        lines.append(l)
    return '\n'.join(lines)
