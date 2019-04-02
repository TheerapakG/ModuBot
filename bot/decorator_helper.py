from functools import wraps

# TODO: test memoize time vs not
def decorate_cog_command(name, *args, **kwargs):
    def decorate_use_name(func):
        @wraps(func)
        async def wrapper(self, ctx, *fargs, **fkwargs):
            func_template = ctx.bot.crossmodule.decorate(name, *args, **kwargs)
            func_exec = func_template(func)
            coro = func_exec(self, ctx, *fargs, **fkwargs)
            return await coro
        return wrapper
    return decorate_use_name