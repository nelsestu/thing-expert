import fnmatch
import os
import typing
from zipfile import ZipFile


def zip_all(zip: ZipFile, root: str, *filters: typing.Callable[[str], bool], path: typing.Optional[str] = '') -> None:
    def should_filter(file: str, *filters: typing.Callable[[str], bool]) -> bool:
        for filter in filters:
            if filter(file): return True
        return False

    for filename in os.listdir(os.path.join(root, path)):
        file = os.path.join(root, path, filename)
        if filters and should_filter(file, *filters): continue
        if os.path.isdir(file):
            zip_all(zip, root, *filters, path=os.path.join(path, filename))
            continue
        zip.write(file, arcname=os.path.join(path, filename))


def exclude_pycache(file: str) -> bool:
    return fnmatch.fnmatch(file, '*/__pycache__') \
           or fnmatch.fnmatch(file, '*.pyc') \
           or fnmatch.fnmatch(file, '*.pyo')
