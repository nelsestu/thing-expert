import copy
import typing


def rename_key(d: dict, old: str, new: str) -> None:
    if old in d:
        d[new] = d[old]
        d.pop(old, None)


def deep_update(a: dict, b: dict) -> dict:
    for k, v in b.items():
        if isinstance(v, dict):
            a[k] = deep_update(a.get(k, {}), v)
        else:
            a[k] = v
    return a


def deep_copy(d: dict) -> dict:
    return copy.deepcopy(d)


def diff(a: dict, b: dict) -> typing.Tuple[dict, dict, dict]:
    added = {k: b[k] for k in set(b) - set(a)}
    removed = {k: a[k] for k in set(a) - set(b)}
    changed = {k: b[k] for k in a if k in b and a[k] != b[k]}
    return added, removed, changed


def dpath_read(d: dict, path: str, sep: typing.Optional[str] = '.') -> typing.Any:
    current = d
    for part in path.split(sep):
        if not isinstance(current, dict): return None
        if part not in current: return None
        if not current[part]: return None
        current = current[part]
    return current


def dpath_write(d: dict, path: str, value: typing.Any, sep: typing.Optional[str] = '.') -> None:
    current = d
    parts = path.split(sep)
    for part in parts[:-1]:
        current[part] = current.get(part, {})
        current = current[part]
    current[parts[-1]] = value


def get_ignore_case(d: dict, key: str, default: typing.Optional[typing.Any] = None) -> typing.Any:
    if key in d: return d[key]

    key_lower = key.lower()
    if key_lower in d: return d[key_lower]

    for k, v in d.items():
        if k.lower() == key_lower: return v

    return default
