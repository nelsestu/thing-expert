import hashlib


def file_sha1(file: str) -> str:
    sha1 = hashlib.sha1()
    with open(file, 'rb') as f:
        buffer = f.read(65536)
        while len(buffer) > 0:
            sha1.update(buffer)
            buffer = f.read(65536)
    return sha1.hexdigest()


def str_sha1(s: str) -> str:
    sha1 = hashlib.sha1()
    sha1.update(s.encode('utf-8'))
    return sha1.hexdigest()
