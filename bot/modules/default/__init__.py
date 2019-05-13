cogs = set()
deps = set()
from . import modulemanage
from . import appearance
cogs.update(modulemanage.cogs)
deps.update(modulemanage.deps)
cogs.update(appearance.cogs)
deps.update(appearance.deps)