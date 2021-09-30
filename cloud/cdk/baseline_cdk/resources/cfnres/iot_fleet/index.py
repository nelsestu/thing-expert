import json
import logging
import time
import typing

import boto3
from crhelper import CfnResource

helper = CfnResource(log_level='DEBUG', polling_interval=17)
logger = logging.getLogger(__name__)

iot_client = boto3.client('iot')


@helper.create
def create(event: dict, context) -> str:
    return event['LogicalResourceId']


@helper.update
def update(event: dict, context) -> str:
    return event['PhysicalResourceId']


@helper.poll_delete
def delete(event: dict, context) -> typing.Union[str, None]:
    try:

        properties = event['ResourceProperties']

        if properties['ThingRemovalPolicy'] == 'destroy':
            thing_type_name = properties['ThingTypeName']
            destroy_things(event, context, thing_type_name)

            LambdaTimeout.check_and_raise(context)

        return event['PhysicalResourceId']

    except LambdaTimeout:
        return None


def destroy_things(event: dict, context, thing_type_name: str) -> None:
    response = None
    next_token = None

    while not response or next_token:
        kwargs = {}
        if next_token: kwargs['nextToken'] = next_token

        response = iot_client.list_things(
            thingTypeName=thing_type_name,
            maxResults=100,
            **kwargs
        )

        next_token = response.get('nextToken')

        things = response.get('things', [])
        if not things: continue

        LambdaTimeout.check_and_raise(context)

        destroy_thing_principals(event, context, things)

        LambdaTimeout.check_and_raise(context)

        for thing in things:
            thing_name = thing['thingName']
            iot_client.delete_thing(thingName=thing_name)

            LambdaTimeout.check_and_raise(context)

        LambdaTimeout.check_and_raise(context)


def destroy_thing_principals(event: dict, context, things: list) -> None:
    thing_principals = []

    # detaching is async, so detach the batch first, then go through them one at a time
    for thing in things:
        thing_name = thing['thingName']
        principals = detach_thing_principals(event, context, thing_name)
        for principal in principals:
            thing_principals.append((thing_name, principal))

        LambdaTimeout.check_and_raise(context)

    if thing_principals:
        time.sleep(10)

        LambdaTimeout.check_and_raise(context)

    for thing_name, principal in thing_principals:

        while thing_has_principal_attached(thing_name, principal):
            iot_client.detach_thing_principal(thingName=thing_name, principal=principal)
            time.sleep(5)

            LambdaTimeout.check_and_raise(context)

        if principal_has_things_attached(principal):
            continue  # this principal has other things, skip it for now

        LambdaTimeout.check_and_raise(context)

        destroy_principal(event, context, principal)

        LambdaTimeout.check_and_raise(context)


def detach_thing_principals(event: dict, context, thing_name: str) -> typing.List[str]:
    response = iot_client.list_thing_principals(thingName=thing_name)
    principals = response.get('principals', [])
    for principal in principals:
        iot_client.detach_thing_principal(thingName=thing_name, principal=principal)
        LambdaTimeout.check_and_raise(context)
    return principals


def destroy_principal(event: dict, context, principal: str) -> None:
    certificate_id = principal.rsplit(sep='/', maxsplit=1)[1]

    iot_client.update_certificate(
        certificateId=certificate_id,
        newStatus='INACTIVE'
    )

    detach_policies(event, context, principal)

    iot_client.delete_certificate(
        certificateId=certificate_id,
        forceDelete=False
    )


def detach_policies(event: dict, context, principal: str) -> None:
    response = iot_client.list_attached_policies(target=principal)
    for policy in response.get('policies', []):
        iot_client.detach_policy(
            target=principal,
            policyName=policy['policyName']
        )

        LambdaTimeout.check_and_raise(context)


def thing_has_principal_attached(thing_name: str, principal: str) -> bool:
    response = iot_client.list_thing_principals(thingName=thing_name)
    return principal in response.get('principals', [])


def principal_has_things_attached(principal: str) -> bool:
    response = iot_client.list_principal_things(
        principal=principal,
        maxResults=1
    )
    return len(response.get('things', [])) > 0


class LambdaTimeout(Exception):
    @staticmethod
    def check_and_raise(context) -> None:
        if context.get_remaining_time_in_millis() <= 60000:
            raise LambdaTimeout()


def handle(event: dict, context) -> None:
    logger.info(json.dumps(event))
    helper(event, context)
