import shutil
import tempfile
from contextlib import contextmanager


@contextmanager
def mkdtemp() -> str:
    dir = tempfile.mkdtemp()
    try:
        yield dir
    finally:
        shutil.rmtree(dir)
