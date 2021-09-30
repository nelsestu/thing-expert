def deep_update(a: dict, b: dict) -> dict:
    for k, v in b.items():
        if isinstance(v, dict):
            a[k] = deep_update(a.get(k, {}), v)
        else:
            a[k] = v
    return a
