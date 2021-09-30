import traceback
import typing

import boto3

import baseline_cloud.core.aws.redis
import baseline_cloud.core.mqtt
from baseline_cloud import core
from baseline_cloud.core import aws
from baseline_cloud.core.config import config
from . import RE_UUID

RULE = rf'^\$aws/rules/{config.topic_prefix}/things/{RE_UUID}/log$'

cloudwatch_client = boto3.client('logs')


def handle(event: dict, context) -> None:
    # {
    #     "level": "string",
    #     "message": "string",
    #     "timestamp": float,
    #     "exception": "string"
    # }

    try:

        client_id = event['clientId']

        group_name = f'{config.app_name}/things'
        stream_name = f'{client_id}/{event["process"]}'

        log_events = [{
            'timestamp': event['timestamp'],
            'message': f'[{event["level"]}] {event["message"]}'
        }]

        if 'exception' in event:
            log_events.append({
                'timestamp': event['timestamp'],
                'message': event['exception']
            })

        sequence_token_key = f'{group_name}/{stream_name}/sequence_token'
        sequence_token = aws.redis.get(sequence_token_key)

        sequence_token = put_log_events(group_name, stream_name, log_events, sequence_token)

        aws.redis.set(sequence_token_key, sequence_token)

        core.mqtt.respond(event, 'accepted')

    except:

        core.mqtt.respond(event, 'rejected', error=traceback.format_exc())

        raise


def put_log_events(group_name: str, stream_name: str, log_events: typing.List[dict], sequence_token: typing.Optional[str]) -> str:
    try:

        return try_put_log_events(group_name, stream_name, log_events, sequence_token)

    except cloudwatch_client.exceptions.ResourceNotFoundException as e:

        create_stream = False

        if 'The specified log group does not exist.' in e.response['Error']['Message']:
            create_stream = True
            try:
                cloudwatch_client.create_log_group(logGroupName=group_name)
                cloudwatch_client.put_retention_policy(logGroupName=group_name, retentionInDays=7)
            except cloudwatch_client.exceptions.ResourceAlreadyExistsException:
                pass

        if create_stream or 'The specified log stream does not exist.' in e.response['Error']['Message']:
            try:
                cloudwatch_client.create_log_stream(logGroupName=group_name, logStreamName=stream_name)
            except cloudwatch_client.exceptions.ResourceAlreadyExistsException:
                pass

        return try_put_log_events(group_name, stream_name, log_events, None)

    except cloudwatch_client.exceptions.InvalidSequenceTokenException as e:
        # {
        #     "Error": {
        #         "Code": "InvalidSequenceTokenException",
        #         "Message": "The given sequenceToken is invalid. The next expected sequenceToken is: xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
        #     },
        #     "ResponseMetadata": {...}
        # }
        sequence_token = e.response['Error']['Message'].rsplit(maxsplit=1)[1]
        return try_put_log_events(group_name, stream_name, log_events, sequence_token)

    except cloudwatch_client.exceptions.DataAlreadyAcceptedException as e:
        return e.response['Error']['Message'].rsplit(maxsplit=1)[1]


def try_put_log_events(group_name: str, stream_name: str, log_events: typing.List[dict], sequence_token: typing.Optional[str]) -> str:
    kwargs = {}
    if sequence_token: kwargs['sequenceToken'] = sequence_token
    response = cloudwatch_client.put_log_events(
        logGroupName=group_name,
        logStreamName=stream_name,
        logEvents=log_events,
        **kwargs)
    if 'nextSequenceToken' not in response:
        raise Exception('Log events were rejected')
    return response['nextSequenceToken']
