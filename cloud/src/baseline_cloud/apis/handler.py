import functools
import json
import traceback
import typing

import baseline_cloud.apis.apis
import baseline_cloud.core.dict
import baseline_cloud.core.exceptions
import baseline_cloud.core.py
from baseline_cloud import core
from baseline_cloud.core.config import config
from baseline_cloud.core.py import parameterized


@parameterized
def inject_response_header(func: callable, name: str, value: typing.Any = None) -> callable:
    @functools.wraps(func)
    def __func__(*args, **kwargs) -> callable:
        response = func(*args, **kwargs)
        if 'headers' not in response:
            response['headers'] = {}
        response['headers'][name] = value() if callable(value) else value
        return response

    return __func__


@inject_response_header(name='Access-Control-Allow-Origin', value='*')  # pylint: disable=E1120
def handle(event: dict, context) -> dict:
    print(json.dumps(event, indent=4))

    try:

        http_path = get_http_path(event)
        http_module_path = '.'.join(http_path)

        api_module_path = f'{baseline_cloud.apis.apis.__name__}.{http_module_path}'
        api_module = core.py.load_module(api_module_path)

        if not api_module:
            raise core.exceptions.HttpErrorResponse(code=404)

        http_method = event['httpMethod'].lower()

        if http_method not in ['get', 'post', 'delete']:
            raise core.exceptions.HttpErrorResponse(code=404)

        api_method = getattr(api_module, http_method) \
            if hasattr(api_module, http_method) else None

        if not api_method or not callable(api_method):
            raise core.exceptions.HttpErrorResponse(code=404)

        return api_method(event, context)

    except core.exceptions.HttpErrorResponse as e:

        headers = {**e.headers}

        content_type = core.dict.get_ignore_case(headers, 'Content-Type')
        if not content_type: headers['Content-Type'] = 'application/json'

        return {
            'statusCode': e.code,
            'headers': headers,
            'body': e.body if e.body else {
                'error': str(e),
                'stacktrace': traceback.format_exc()
            } if config.debug_api_gateway_errors else None
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': {
                'error': str(e),
                'stacktrace': traceback.format_exc()
            } if config.debug_api_gateway_errors else None
        }


def get_http_path(event: dict) -> typing.List[str]:
    pathParameters = event.get('pathParameters') or {}
    resource = event['resource']

    if '{proxy+}' in resource:
        resource = resource.replace('{proxy+}', pathParameters['proxy'])

    for key, value in pathParameters.items():
        resource = resource.replace('{{{}+}}'.format(key), key)
        resource = resource.replace('{{{}}}'.format(key), key)

    resource = resource.split('/')
    resource = resource[1:]  # trim the first because it starts with /

    return resource
