import json
import logging

import boto3
from crhelper import CfnResource

helper = CfnResource(log_level='DEBUG')
logger = logging.getLogger(__name__)

iot_client = boto3.client('iot')
lambda_client = boto3.client('lambda')


@helper.create
def create(event: dict, context) -> str:
    thing_group_arn = None

    try:

        properties = event['ResourceProperties']
        thing_group_name = properties['ThingGroupName']

        try:
            thing_group = iot_client.describe_thing_group(thingGroupName=thing_group_name)
            return thing_group['thingGroupArn']
        except iot_client.exceptions.ResourceNotFoundException:
            pass

        tags = resource_tags(event)

        thing_group = iot_client.create_thing_group(
            thingGroupName=thing_group_name,
            tags=[{
                'Key': k,
                'Value': v
            } for k, v in tags.items()]
        )

        thing_group_arn = thing_group['thingGroupArn']

        attach_policy(thing_group_arn, properties['ThingGroupPolicy'])

        return thing_group_arn

    except:

        if thing_group_arn:
            event['PhysicalResourceId'] = thing_group_arn
            delete(event, context)

        raise


@helper.update
def update(event: dict, context) -> str:
    properties_old = event['OldResourceProperties']
    properties = event['ResourceProperties']

    thing_group_arn = event['PhysicalResourceId']
    if thing_group_arn.find('arn:aws:iot:') != 0 or ':thinggroup/' not in thing_group_arn:
        return thing_group_arn  # not a valid thinggroup arn

    if properties['ThingGroupName'] != properties_old['ThingGroupName']:
        # Here you can create the new thing group, and re-associate all things to the new group.
        # Returning the new thing_group_arn will cause delete() to be called on the old arn.
        # Re-associating may require using @helper.poll_update instead
        raise Exception('Renaming a ThingGroup is not supported.')

    if properties['ThingGroupPolicy'] != properties_old['ThingGroupPolicy']:
        attach_policy(thing_group_arn, properties['ThingGroupPolicy'])
        detach_policy(thing_group_arn, properties_old['ThingGroupPolicy'])

    tags = resource_tags(event)

    tag_thing_group(thing_group_arn, tags)

    return thing_group_arn


@helper.delete
def delete(event: dict, context) -> str:
    thing_group_arn = event['PhysicalResourceId']
    if thing_group_arn.find('arn:aws:iot:') != 0 or ':thinggroup/' not in thing_group_arn:
        return thing_group_arn  # not a valid thinggroup arn

    thing_group_name = thing_group_arn.rsplit(maxsplit=1, sep='/')[1]

    try:
        iot_client.delete_thing_group(thingGroupName=thing_group_name)
    except iot_client.exceptions.ResourceNotFoundException:
        pass

    return thing_group_arn


def resource_tags(event: dict) -> dict:
    lambda_tags = list_lambda_tags(event['ServiceToken'])
    return {
        **{f'x-{k}' if k.startswith('aws:') else k: v for k, v in lambda_tags.items()},
        'x-aws:cloudformation:stack-name': event['StackId'].rsplit(sep='/', maxsplit=2)[1],
        'x-aws:cloudformation:stack-id': event['StackId'],
        'x-aws:cloudformation:logical-id': event['LogicalResourceId']
    }


def list_lambda_tags(arn: str) -> dict:
    response = lambda_client.list_tags(Resource=arn)
    return response['Tags']


def tag_thing_group(arn: str, tags: dict) -> None:
    iot_client.tag_resource(
        resourceArn=arn,
        tags=[{
            'Key': k,
            'Value': v
        } for k, v in tags.items()]
    )


def attach_policy(thing_group: str, policy: str) -> None:
    iot_client.attach_policy(
        policyName=policy,
        target=thing_group
    )


def detach_policy(thing_group: str, policy: str) -> None:
    iot_client.detach_policy(
        policyName=policy,
        target=thing_group
    )


def handle(event: dict, context) -> None:
    logger.info(json.dumps(event))
    helper(event, context)
