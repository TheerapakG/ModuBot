"""
ModuBot: A modular discord bot with dependency management
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The MIT License (MIT)

Copyright (c) 2019 TheerapakG

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
"""

import typing
import collections.abc
from datetime import timedelta

def check_typing(obj: object, typehintobj) -> bool:
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
    '''
    first: value we had
    second: value query
    '''
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
                return lambda a, b: b <= a if isinstance(b, collections.abc.Set) else b in a
            return False