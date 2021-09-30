import functools
import importlib
import threading
import traceback
import typing
from inspect import isclass
from logging import ERROR

from baseline_cloud.core.logging import logger


def classname(obj: typing.Any) -> str:
    clazz = obj if isclass(obj) else obj.__class__
    module = clazz.__module__
    module = module + '.' if module else ''
    return module + clazz.__name__


def load_module(modname: str) -> typing.Any:
    try:
        return importlib.import_module(modname)
    except ModuleNotFoundError:
        return None


def parameterized(decorator: callable) -> callable:
    def __func__(*args, **kwargs) -> callable:
        if len(args) > 0 and callable(args[0]):
            return decorator(*args, **kwargs)
        else:
            def __layer__(func) -> callable:
                return decorator(func, *args, **kwargs)

            return __layer__

    return __func__


@parameterized
def safe_method(func: callable, msg: typing.Optional[str] = 'Unexpected exception caught', retval: typing.Optional[typing.Any] = None, log_level: typing.Optional[int] = ERROR) -> callable:
    @functools.wraps(func)
    def __func__(*args, **kwargs) -> callable:
        try:
            return func(*args, **kwargs)
        except KeyboardInterrupt:
            return retval
        except SystemExit:
            return retval
        except:
            if logger.isEnabledFor(log_level):
                stacktrace = traceback.format_exc().strip()
                stacktrace = stacktrace.split('\n')
                out = '\r'.join([msg, *stacktrace])
                logger._log(log_level, out, args=None)
            return retval

    return __func__


@parameterized
def consume_exception(func: callable, cls: typing.Any, msg: typing.Optional[str] = None, retval: typing.Optional[typing.Any] = None) -> callable:
    @functools.wraps(func)
    def __func__(*args, **kwargs) -> callable:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if type(e) == cls and (not msg or str(e) == msg):
                return retval
            else:
                raise e

    return __func__


@parameterized
def synchronized(func: callable, lock: threading.RLock) -> callable:
    @functools.wraps(func)
    def __func__(*args, **kwargs) -> callable:
        with lock:
            return func(*args, **kwargs)

    return __func__
