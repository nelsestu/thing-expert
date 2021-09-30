import json
import typing

import jose.jwt

import baseline_cloud.core.aws.ssm
import baseline_cloud.core.dict
import baseline_cloud.core.jwt
from baseline_cloud import core
from baseline_cloud.authorizer.blueprints import AuthPolicy
from baseline_cloud.core import aws
from baseline_cloud.core.config import config
from baseline_cloud.core.py import safe_method


def handle(event: dict, context) -> dict:
    print(json.dumps(event, indent=4))

    method_arn = event['methodArn'].split(':')
    api_gateway_arn = method_arn[5].split('/')
    aws_account_id = method_arn[4]

    unverified_claims = get_unverified_claims(event) or {}
    principal = unverified_claims.get('sub') or 'anonymous'

    policy = AuthPolicy(principal, aws_account_id)
    policy.restApiId = api_gateway_arn[0]
    policy.region = method_arn[3]
    policy.stage = api_gateway_arn[1]

    verified_claims = get_verified_claims(event)
    access_paths = get_access_paths(verified_claims)

    if not access_paths:
        policy.denyAllMethods()
    else:
        for access_path in access_paths:
            policy.allowMethod(access_path['method'], access_path['path'])

    response = policy.build()

    # new! -- add additional key-value pairs associated with the authenticated principal
    # these are made available by APIGW like so: $context.authorizer.<key>
    # additional context is cached
    # response['context'] = {
    #     'key': 'value',  # $context.authorizer.key -> value
    #     'number': 1,
    #     'bool': True
    # }

    return response


@safe_method(retval=None)  # pylint: disable=E1120
def get_access_paths(claims: dict) -> typing.Optional[typing.List[dict]]:
    if not claims: return None

    if claims['iss'] == aws.ssm.get_parameter(f'/{config.app_name}/cognito-pool-url'):
        return [{'path': '*', 'method': '*'}]

    if claims['iss'] == aws.ssm.get_parameter(f'/{config.app_name}/jwt-issuer'):
        return [{'path': '*', 'method': '*'}]

    return None


@safe_method(retval=None)  # pylint: disable=E1120
def get_unverified_claims(event: dict) -> dict:
    headers = event['headers']
    token = core.dict.get_ignore_case(headers, 'Authorization')
    return jose.jwt.get_unverified_claims(token)


@safe_method(retval=None)  # pylint: disable=E1120
def get_verified_claims(event: dict) -> dict:
    headers = event['headers']
    token = core.dict.get_ignore_case(headers, 'Authorization')
    return core.jwt.authorize(token)
