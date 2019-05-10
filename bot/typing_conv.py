import typing
import collections.abc
from datetime import timedelta

def check_typing(obj, typehintobj):
    try:
        origin = typehintobj.__origin__
    except AttributeError:
        if typehintobj is typing.Any:
            return True
        return isinstance(obj, typehintobj)
    else:
        if origin is typing.Union:
            for typehint in typehintobj.__args__:
                if check_typing(obj, typehint):
                    return True
            return False
        else:
            if isinstance(obj, origin):
                if typehintobj.__args__:
                    for subobj in enumerate(obj):
                        if len(subobj) != typehintobj.__args__:
                            return False
                        for ctuple in zip(subobj, typehintobj.__args__):
                            if not check_typing(*ctuple):
                                return False
                return True
            return False

def comparer_typing(typehintobj) -> typing.Callable:
    try:
        origin = typehintobj.__origin__
    except AttributeError:
        if typehintobj is int or typehintobj is timedelta:
            return lambda a, b: a >= b
        return lambda a, b: a == b
    else:
        if origin is typing.Union:
            if len(typehintobj.__args__) == 2 and type(None) in typehintobj.__args__:
                return lambda a, b: True if a is None else comparer_typing(typehintobj.__args__[0])(a, b)
        else:
            if issubclass(origin, collections.abc.Set):
                return lambda a, b: a <= b if isinstance(a, collections.abc.Set) else a in b
            return False