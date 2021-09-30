import json

import baseline_cloud.core.aws.iot
from baseline_cloud.core import aws
from baseline_cloud.core.config import config
from baseline_cloud.core.json import JSONEncoder


def get(event: dict, context) -> dict:
    things = []

    def listed_thing(thing_name: str) -> None:
        thing = aws.iot.describe_thing(thing_name)
        things.append({
            'name': thing['thingName'],
            'attributes': thing.get('attributes')
        })

    aws.iot.list_things_in_thing_group(f'{config.app_name}-verified', listed_thing)

    return {
        'statusCode': 200,
        'body': json.dumps({
            'things': things
        }, cls=JSONEncoder),
        'headers': {
            'Content-Type': 'application/json'
        }
    }
