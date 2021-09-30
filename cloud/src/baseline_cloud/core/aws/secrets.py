import base64
import typing

import boto3

secrets_client = boto3.client('secretsmanager')


def get_secret_value(name: str) -> typing.Union[str, bytes]:
    response = secrets_client.get_secret_value(SecretId=name)
    if 'SecretString' in response: return response['SecretString']
    return base64.b64decode(response['SecretBinary'])
