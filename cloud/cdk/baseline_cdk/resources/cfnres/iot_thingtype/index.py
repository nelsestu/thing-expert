import json
import logging
import time
import typing
from datetime import datetime, timezone

import boto3
from crhelper import CfnResource

helper = CfnResource(log_level='DEBUG', polling_interval=17)
logger = logging.getLogger(__name__)

iot_client = boto3.client('iot')
lambda_client = boto3.client('lambda')


@helper.create
def create(event: dict, context) -> str:
    properties = event['ResourceProperties']
    thing_type_name = properties['ThingTypeName']

    try:
        thing_type = iot_client.describe_thing_type(thingTypeName=thing_type_name)
        return thing_type['thingTypeArn']
    except iot_client.exceptions.ResourceNotFoundException:
        pass

    tags = resource_tags(event)

    thing_type = iot_client.create_thing_type(
        thingTypeName=thing_type_name,
        tags=[{
            'Key': k,
            'Value': v
        } for k, v in tags.items()]
    )

    return thing_type['thingTypeArn']


@helper.update
def update(event: dict, context) -> str:
    properties_old = event['OldResourceProperties']
    properties = event['ResourceProperties']

    thing_type_arn = event['PhysicalResourceId']
    if thing_type_arn.find('arn:aws:iot:') != 0 or ':thingtype/' not in thing_type_arn:
        return thing_type_arn  # not a valid thingtype arn

    if properties['ThingTypeName'] != properties_old['ThingTypeName']:
        # Here you can create the new thing type, and re-associate all things to the new type.
        # Returning the new thing_type_arn will cause delete() to be called on the old arn.
        # Re-associating may require using @helper.poll_update instead
        raise Exception(f'Renaming a ThingType is not supported.')

    tags = resource_tags(event)

    tag_thing_type(thing_type_arn, tags)

    return thing_type_arn


@helper.poll_delete
def delete(event: dict, context) -> typing.Union[str, None]:
    try:

        thing_type_arn = event['PhysicalResourceId']
        if thing_type_arn.find('arn:aws:iot:') != 0 or ':thingtype/' not in thing_type_arn:
            return thing_type_arn  # not a valid thingtype arn

        thing_type_name = thing_type_arn.rsplit(maxsplit=1, sep='/')[1]

        try:
            thing_type = iot_client.describe_thing_type(thingTypeName=thing_type_name)
            thing_type_metadata = thing_type['thingTypeMetadata']
        except iot_client.exceptions.ResourceNotFoundException:
            return thing_type_arn

        LambdaTimeout.check_and_raise(context)

        if not thing_type_metadata.get('deprecated'):
            iot_client.deprecate_thing_type(thingTypeName=thing_type_name)
            deprecated_at = datetime.utcnow().replace(tzinfo=timezone.utc)
        else:
            deprecated_at = thing_type_metadata.get('deprecationDate')

        LambdaTimeout.check_and_raise(context)

        def seconds_since_deprecation() -> float:
            now = datetime.utcnow().replace(tzinfo=timezone.utc)
            return (now - deprecated_at).total_seconds()

        # after deprecating, wait at least 5 minutes
        while 300 - seconds_since_deprecation() > 0:
            time.sleep(10)

            LambdaTimeout.check_and_raise(context)

        iot_client.delete_thing_type(thingTypeName=thing_type_name)

        return thing_type_arn

    except LambdaTimeout:
        return None


def resource_tags(event: dict) -> dict:
    lambda_tags = list_lambda_tags(event['ServiceToken'])
    return {
        **{f'x-{k}' if k.startswith('aws:') else k: v for k, v in lambda_tags.items()},
        'x-aws:cloudformation:stack-name': event['StackId'].rsplit(sep='/', maxsplit=2)[1],
        'x-aws:cloudformation:stack-id': event['StackId'],
        'x-aws:cloudformation:logical-id': event['LogicalResourceId']
    }


def list_lambda_tags(arn: str) -> dict:
    response = lambda_client.list_tags(
        Resource=arn
    )
    return response['Tags']


def tag_thing_type(arn: str, tags: dict) -> None:
    iot_client.tag_resource(
        resourceArn=arn,
        tags=[{
            'Key': k,
            'Value': v
        } for k, v in tags.items()]
    )


class LambdaTimeout(Exception):
    @staticmethod
    def check_and_raise(context) -> None:
        if context.get_remaining_time_in_millis() <= 60000:
            raise LambdaTimeout()


def handle(event: dict, context) -> None:
    logger.info(json.dumps(event))
    helper(event, context)
