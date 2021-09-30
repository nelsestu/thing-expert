from datetime import datetime


def utcnow() -> str:
    now = datetime.utcnow()
    millis = now.microsecond / 1000.0
    return now.strftime(f'%Y-%m-%dT%H:%M:%S.{millis:03.0f}Z')
