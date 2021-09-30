import typing
from datetime import datetime
from datetime import timezone


def format(dt: typing.Optional[datetime] = None, format: typing.Optional[str] = '%Y-%m-%d %H:%M:%S') -> str:
    if not dt: dt = datetime.utcnow()
    return dt.strftime(format)


def format_utc(dt: typing.Optional[datetime] = None) -> str:
    if not dt: dt = datetime.utcnow()
    ms = dt.microsecond / 1000.0
    return dt.strftime(f'%Y-%m-%dT%H:%M:%S.{ms:03.0f}Z')


def parse_utc(s: str) -> datetime:
    dt = datetime.strptime(s, '%Y-%m-%dT%H:%M:%S.%fZ')
    dt = dt.replace(tzinfo=timezone.utc)
    return dt
