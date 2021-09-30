import os

from redis import Redis

import baseline_cloud.core.aws.ssm
from baseline_cloud.core import aws
from baseline_cloud.core.config import config

if os.environ.get('USE_MOCK_REDIS') == '1':
    class Redis(object):

        def __init__(self, *args, **kwargs) -> None:
            super().__init__()
            self.data = {}

        def set(self, name: str, value: str, *args, **kwargs) -> None:
            self.data[name] = value

        def get(self, name: str) -> str:
            return self.data.get(name)

        def delete(self, *names: str) -> None:
            for name in names:
                self.data.pop(name, None)

redis_client = Redis(
    host=aws.ssm.get_parameter(f'/{config.app_name}/redis-address'),
    port=int(aws.ssm.get_parameter(f'/{config.app_name}/redis-port'))
)


def set(key: str, value: str, ttl: int = 86400) -> None:
    redis_client.set(name=key, value=value, ex=ttl)


def delete(key: str) -> None:
    redis_client.delete(key)


def get(key: str) -> str:
    value = redis_client.get(key)
    if value and type(value) == bytes:
        value = value.decode('utf-8')
    return value
