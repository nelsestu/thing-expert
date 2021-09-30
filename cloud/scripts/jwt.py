import json
import time

from jose import jwt

jwt_issuer = ''
jwt_secret = ''


def create(sub: str, minutes: int = 0, hours: int = 0, days: int = 0, **kwargs) -> str:
    iat = int(time.time())
    exp = (minutes * 60) + (hours * 3600) + (days * 86400)
    if exp > 0: kwargs['exp'] = iat + exp
    return jwt.encode({
        'sub': sub,
        'iss': jwt_issuer,
        'iat': iat,
        **kwargs
    }, key=jwt_secret, algorithm='HS256')


token = create(
    sub='00000000-0000-4000-8000-000000000000',
    scope='',
    days=7
)

claims = jwt.decode(token, key=jwt_secret, algorithms='HS256', issuer=jwt_issuer)

print(token)
print(json.dumps(claims, sort_keys=True, indent=4))
