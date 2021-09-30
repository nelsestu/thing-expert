import http.client
import typing


class HttpErrorResponse(Exception):
    def __init__(self, code: int, message: str = None, headers: dict = None, body: typing.Any = None):
        if not message and code in http.client.responses: message = http.client.responses[code]
        super().__init__(message)
        self.code = code
        self.headers = headers or {}
        self.body = body
