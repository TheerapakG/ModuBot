from functools import wraps

_decorators = dict()

def register_decorator(decorator):
    _decorators[decorator.__name__] = decorator

def unregister_decorator(decorator):
    del _decorators[decorator.__name__]

def decorate(name, *args, **kwargs):
    def decorate_use_name(func):
        @wraps(func)
        def wrapper(*fargs, **fkwargs):
            return (_decorators[name](*args, **kwargs)(func))(*fargs, **fkwargs)
        return wrapper
    return decorate_use_name