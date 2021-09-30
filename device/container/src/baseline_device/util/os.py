import subprocess
import typing
from subprocess import CompletedProcess
from subprocess import DEVNULL


def shell(*popenargs, shell: typing.Optional[bool] = True, stdout: typing.Optional[int] = DEVNULL, stderr: typing.Optional[int] = DEVNULL, **kwargs) -> typing.Union[str, int, CompletedProcess]:
    if not stdout or stdout == DEVNULL:
        return subprocess.check_call(*popenargs, shell=shell, stdout=stdout, stderr=stderr, **kwargs)
    else:
        return subprocess.check_output(*popenargs, shell=shell, stderr=stderr, **kwargs)
