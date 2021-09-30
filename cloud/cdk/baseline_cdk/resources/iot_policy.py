import json

from aws_cdk import aws_iot
from aws_cdk import core

from baseline_cdk.util import cdk
from baseline_cdk.util.hash import str_sha1


def create_initial_policy(stack: core.Stack, iot_scope: core.Construct) -> None:
    policy_document = {
        'Version': '2012-10-17',
        'Statement': [
            {
                'Effect': 'Allow',
                'Action': 'iot:Connect',
                'Resource': f'arn:aws:iot:{stack.region}:{stack.account}:client/${{iot:ClientId}}',
                'Condition': {
                    'StringLike': {
                        # force iot:ClientId to be 128 characters to avoid collisions when randomly selected by new clients.
                        # https://docs.aws.amazon.com/general/latest/gr/iot-core.html#iot-protocol-limits
                        'iot:ClientId': '?' * 128
                    }
                }
            },
            {
                'Effect': 'Allow',
                'Action': 'iot:Publish',
                'Resource': f'arn:aws:iot:{stack.region}:{stack.account}:topic/$aws/rules/{cdk.topic_prefix}/clients/${{iot:ClientId}}/provision'
            },
            {
                'Effect': 'Allow',
                'Action': 'iot:Subscribe',
                'Resource': [
                    f'arn:aws:iot:{stack.region}:{stack.account}:topicfilter/{cdk.topic_prefix}/clients/${{iot:ClientId}}/provision/accepted',
                    f'arn:aws:iot:{stack.region}:{stack.account}:topicfilter/{cdk.topic_prefix}/clients/${{iot:ClientId}}/provision/rejected'
                ]
            },
            {
                'Effect': 'Allow',
                'Action': 'iot:Receive',
                'Resource': [
                    f'arn:aws:iot:{stack.region}:{stack.account}:topic/{cdk.topic_prefix}/clients/${{iot:ClientId}}/provision/accepted',
                    f'arn:aws:iot:{stack.region}:{stack.account}:topic/{cdk.topic_prefix}/clients/${{iot:ClientId}}/provision/rejected'
                ]
            }
        ]
    }

    # we cannot update a policy through cloudformation if we give it a custom name,
    # so use a hash within the name to have cloudformation replace it. save it's ref
    # to an systems manager parameter for looking it up later.
    policy_hash = str_sha1(json.dumps(policy_document, sort_keys=True))

    aws_iot.CfnPolicy(
        iot_scope, 'InitialPolicy',
        policy_name=f'{cdk.app_name}-initial-{policy_hash[:8]}',
        policy_document=policy_document
    )


def create_intermediate_policy(stack: core.Stack, iot_scope: core.Construct) -> None:
    policy_document = {
        'Version': '2012-10-17',
        'Statement': [
            {
                'Effect': 'Allow',
                'Action': 'iot:Connect',
                'Resource': f'arn:aws:iot:{stack.region}:{stack.account}:client/${{iot:Connection.Thing.ThingName}}',
                'Condition': {
                    'StringLike': {
                        'iot:ClientId': '????????-????-????-????-????????????',
                        'iot:Certificate.Issuer.CommonName': cdk.app_name,
                        'iot:Connection.Thing.ThingTypeName': cdk.app_name
                    },
                    'Bool': {
                        'iot:Connection.Thing.IsAttached': True
                    }
                }
            },
            {
                'Effect': 'Allow',
                'Action': 'iot:Publish',
                'Resource': f'arn:aws:iot:{stack.region}:{stack.account}:topic/$aws/rules/{cdk.topic_prefix}/things/${{iot:Connection.Thing.ThingName}}/provision'
            },
            {
                'Effect': 'Allow',
                'Action': 'iot:Subscribe',
                'Resource': [
                    f'arn:aws:iot:{stack.region}:{stack.account}:topicfilter/{cdk.topic_prefix}/things/${{iot:Connection.Thing.ThingName}}/provision/accepted',
                    f'arn:aws:iot:{stack.region}:{stack.account}:topicfilter/{cdk.topic_prefix}/things/${{iot:Connection.Thing.ThingName}}/provision/rejected'
                ]
            },
            {
                'Effect': 'Allow',
                'Action': 'iot:Receive',
                'Resource': [
                    f'arn:aws:iot:{stack.region}:{stack.account}:topic/{cdk.topic_prefix}/things/${{iot:Connection.Thing.ThingName}}/provision/accepted',
                    f'arn:aws:iot:{stack.region}:{stack.account}:topic/{cdk.topic_prefix}/things/${{iot:Connection.Thing.ThingName}}/provision/rejected'
                ]
            }
        ]
    }

    # we cannot update a policy through cloudformation if we give it a custom name,
    # so use a hash within the name to have cloudformation replace it. save it's ref
    # to an systems manager parameter for looking it up later.
    policy_hash = str_sha1(json.dumps(policy_document, sort_keys=True))

    aws_iot.CfnPolicy(
        iot_scope, 'IntermediatePolicy',
        policy_name=f'{cdk.app_name}-intermediate-{policy_hash[:8]}',
        policy_document=policy_document
    )


def create_standard_policy(stack: core.Stack, iot_scope: core.Construct) -> None:
    policy_document = {
        'Version': '2012-10-17',
        'Statement': [
            {
                'Effect': 'Allow',
                'Action': 'iot:Connect',
                'Resource': f'arn:aws:iot:{stack.region}:{stack.account}:client/${{iot:Connection.Thing.ThingName}}',
                'Condition': {
                    'StringLike': {
                        'iot:ClientId': '????????-????-????-????-????????????',
                        'iot:Certificate.Issuer.CommonName': cdk.app_name,
                        'iot:Connection.Thing.ThingTypeName': cdk.app_name
                    },
                    'Bool': {
                        'iot:Connection.Thing.IsAttached': True
                    }
                }
            },
            {
                'Effect': 'Allow',
                'Action': 'iot:Publish',
                'Resource': [
                    f'arn:aws:iot:{stack.region}:{stack.account}:topic/$aws/things/${{iot:Connection.Thing.ThingName}}/shadow/*',
                    f'arn:aws:iot:{stack.region}:{stack.account}:topic/$aws/things/${{iot:Connection.Thing.ThingName}}/jobs/*',
                    f'arn:aws:iot:{stack.region}:{stack.account}:topic/$aws/rules/{cdk.topic_prefix}/things/${{iot:Connection.Thing.ThingName}}/*'
                ]
            },
            {
                'Effect': 'Allow',
                'Action': 'iot:Subscribe',
                'Resource': [
                    f'arn:aws:iot:{stack.region}:{stack.account}:topicfilter/$aws/things/${{iot:Connection.Thing.ThingName}}/shadow/*',
                    f'arn:aws:iot:{stack.region}:{stack.account}:topicfilter/$aws/things/${{iot:Connection.Thing.ThingName}}/jobs/*',
                    f'arn:aws:iot:{stack.region}:{stack.account}:topicfilter/{cdk.topic_prefix}/things/${{iot:Connection.Thing.ThingName}}/*'
                ]
            },
            {
                'Effect': 'Allow',
                'Action': 'iot:Receive',
                'Resource': [
                    f'arn:aws:iot:{stack.region}:{stack.account}:topic/$aws/things/${{iot:Connection.Thing.ThingName}}/shadow/*',
                    f'arn:aws:iot:{stack.region}:{stack.account}:topic/$aws/things/${{iot:Connection.Thing.ThingName}}/jobs/*',
                    f'arn:aws:iot:{stack.region}:{stack.account}:topic/{cdk.topic_prefix}/things/${{iot:Connection.Thing.ThingName}}/*'
                ]
            },
            {
                'Effect': 'Allow',
                'Action': [
                    'iot:GetThingShadow',
                    'iot:UpdateThingShadow',
                    'iot:DeleteThingShadow',
                    'iot:DescribeJobExecution',
                    'iot:UpdateJobExecution',
                    'iot:GetPendingJobExecutions',
                    'iot:StartNextPendingJobExecution'
                ],
                'Resource': f'arn:aws:iot:{stack.region}:{stack.account}:thing/${{iot:Connection.Thing.ThingName}}'
            }
        ]
    }

    # we cannot update a policy through cloudformation if we give it a custom name,
    # so use a hash within the name to have cloudformation replace it. save it's ref
    # to an systems manager parameter for looking it up later.
    policy_hash = str_sha1(json.dumps(policy_document, sort_keys=True))

    aws_iot.CfnPolicy(
        iot_scope, 'Policy',
        policy_name=f'{cdk.app_name}-{policy_hash[:8]}',
        policy_document=policy_document
    )


def create(stack: core.Stack) -> None:
    iot_scope = cdk.find_resource(stack, 'Iot')
    if not iot_scope: iot_scope = core.Construct(stack, 'Iot')

    create_initial_policy(stack, iot_scope)
    create_intermediate_policy(stack, iot_scope)
    create_standard_policy(stack, iot_scope)
