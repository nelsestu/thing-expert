import typing

import boto3

iot_client = boto3.client('iot')


def describe_thing(thing_name: str) -> dict:
    thing = iot_client.describe_thing(thingName=thing_name)
    thing.pop('ResponseMetadata', None)
    return thing


def list_things_in_thing_group(thing_group_name: str, callback: typing.Callable[[str], None]) -> None:
    response = None
    while not response or 'nextToken' in response:

        kwargs = {}
        if response and 'nextToken' in response:
            kwargs['nextToken'] = response['nextToken']

        response = iot_client.list_things_in_thing_group(
            thingGroupName=thing_group_name,
            recursive=True,
            maxResults=100,
            **kwargs
        )

        for thing_name in response['things']:
            callback(thing_name)


def search_index(query: str, index_name: str = 'AWS_Things') -> typing.List[str]:
    things = []

    response_list = None

    while not response_list or 'nextToken' in response_list:

        kwargs = {}
        if response_list and 'nextToken' in response_list:
            kwargs['nextToken'] = response_list['nextToken']

        response_list = iot_client.search_index(
            indexName=index_name,
            queryString=query,
            **kwargs)

        things.extend(response_list['things'])

    return things
