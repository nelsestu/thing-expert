import json
import os
import typing

this_dir = os.path.abspath(os.path.dirname(os.path.abspath(__file__)))


class Config(object):

    def __init__(self) -> None:
        with open(f'{this_dir}/../../config.json', 'r') as f:
            self.values = json.load(f)

    def __getattr__(self, name: str) -> typing.Any:
        values = object.__getattribute__(self, 'values')
        if name in values: return values[name]
        return None


config = Config()
