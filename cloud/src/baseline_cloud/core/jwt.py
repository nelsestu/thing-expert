import time
import typing

import requests
from jose import jwt

import baseline_cloud.core.aws.cognito
import baseline_cloud.core.aws.secrets
import baseline_cloud.core.aws.ssm
from baseline_cloud.core import aws
from baseline_cloud.core.config import config


def create(sub: str, minutes: typing.Optional[int] = 0, hours: typing.Optional[int] = 0, days: typing.Optional[int] = 0, **kwargs) -> str:
    iat = int(time.time())
    exp = (minutes * 60) + (hours * 3600) + (days * 86400)
    if exp > 0: kwargs['exp'] = iat + exp
    return jwt.encode({
        'sub': sub,
        'iss': jwt_issuer,
        'iat': iat,
        **kwargs
    }, key=jwt_secret, algorithm='HS256')


def authorize(token: str) -> dict:
    claims = jwt.get_unverified_claims(token)
    if claims['iss'] == jwt_issuer:
        return jwt.decode(token, key=jwt_secret, algorithms='HS256', issuer=jwt_issuer)
    if claims['iss'] == cognito_pool_url:
        return aws.cognito.verify_token(cognito_keys, token)
    raise Exception('Unknown issuer')


def download_cognito_jwks() -> typing.List[dict]:
    response = requests.get(url=f'{cognito_pool_url}/.well-known/jwks.json')
    response.raise_for_status()
    return response.json()


jwt_secret = aws.secrets.get_secret_value(f'/{config.app_name}/jwt-secret')
jwt_issuer = aws.ssm.get_parameter(f'/{config.app_name}/jwt-issuer')

# only load the jwks file on cold-start
cognito_pool_url = aws.ssm.get_parameter(f'/{config.app_name}/cognito-pool-url')
cognito_keys = download_cognito_jwks()
