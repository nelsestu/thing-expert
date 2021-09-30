import typing

import boto3

ssm_client = boto3.client('ssm')

parameters = {}


def get_parameter(name: str) -> typing.Union[str, typing.List[str]]:
    if name not in parameters:
        response = ssm_client.get_parameter(Name=name, WithDecryption=True)
        parameters[name] = response['Parameter']['Value']
    return parameters.get(name)
