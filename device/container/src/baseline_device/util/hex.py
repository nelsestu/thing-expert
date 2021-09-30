import random


def rand(n: int) -> str:
    return ''.join(random.choices('0123456789abcdef', k=n))


def rand12() -> str:
    return rand(12)
