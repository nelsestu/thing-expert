import json

import boto3

from baseline_cloud.core.json import JSONEncoder


def respond(event, status, **payload) -> None:
    if 'topic' not in event: return

    topic = event['topic']
    if topic.startswith('$aws/rules/'):
        topic = topic[len('$aws/rules/'):]

    if 'clientToken' in event:
        payload['clientToken'] = event['clientToken']

    client = boto3.client('iot-data')
    client.publish(
        topic=f'{topic}/{status}',
        payload=json.dumps(payload, cls=JSONEncoder),
        qos=1
    )
