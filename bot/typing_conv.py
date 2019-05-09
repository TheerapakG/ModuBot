import typing

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
                