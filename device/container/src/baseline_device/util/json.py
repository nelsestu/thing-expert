import decimal
import json
import typing
from contextlib import contextmanager
from datetime import datetime

import baseline_device.util.date
from baseline_device import util


@contextmanager
def open_json(*args, **kwargs) -> str:
    with open(*args, **kwargs) as f:
        yield json.load(f)


class JSONEncoder(json.JSONEncoder):
    def default(self, o) -> typing.Any:  # pylint: disable=E0202
        if isinstance(o, datetime):
            return util.date.format_utc(o)
        if isinstance(o, decimal.Decimal):
            return float(o)
        return super(JSONEncoder, self).default(o)
