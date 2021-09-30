import decimal
import json
import typing
from datetime import datetime

import baseline_cloud.core.date
from baseline_cloud import core


class JSONEncoder(json.JSONEncoder):
    def default(self, o: typing.Any) -> typing.Any:
        if isinstance(o, datetime):
            return core.date.format_utc(o)
        if isinstance(o, decimal.Decimal):
            return float(o)
        return super(JSONEncoder, self).default(o)
