import base64

import baseline_cloud.core.aws.secrets
import baseline_cloud.core.dict
import baseline_cloud.core.exceptions
import baseline_cloud.core.jwt
from baseline_cloud import core
from baseline_cloud.core import aws
from baseline_cloud.core.config import config


def get(event: dict, context) -> dict:
    headers = event.get('headers')

    password = core.dict.get_ignore_case(headers, 'Authorization')
    if password: password = base64.b64decode(password).decode('utf-8')

    if not password:
        raise core.exceptions.HttpErrorResponse(code=400)

    if password == aws.secrets.get_secret_value(f'/{config.app_name}/web-password'):
        return {
            'statusCode': 200,
            'body': core.jwt.create(sub=config.app_name, scope='web', days=7),
            'headers': {
                'Content-Type': 'text/plain'
            }
        }

    raise core.exceptions.HttpErrorResponse(code=401)
