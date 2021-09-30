import time
import typing

from jose import jwk, jwt
from jose.utils import base64url_decode


# https://github.com/awslabs/aws-support-tools/blob/master/Cognito/decode-verify-jwt/decode-verify-jwt.py
def verify_token(keys: typing.List[dict], token: str) -> dict:
    headers = jwt.get_unverified_headers(token)

    kid = headers['kid']
    kidx = -1

    for i in range(len(keys)):
        if kid == keys[i]['kid']:
            kidx = i
            break

    if kidx == -1: raise Exception('Signature key not found')

    public_key = jwk.construct(keys[kidx])
    message, encoded_signature = str(token).rsplit('.', 1)
    decoded_signature = base64url_decode(encoded_signature.encode('utf-8'))

    if not public_key.verify(message.encode("utf8"), decoded_signature):
        raise Exception('Signature verification failed')

    claims = jwt.get_unverified_claims(token)

    if time.time() > claims['exp']:
        raise Exception('Token has expired')

    return claims
