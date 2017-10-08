#!/usr/bin/env python

from apc.utility import APC  # noqa
from apc.utility import APC_DEFAULT_HOST  # noqa
from apc.utility import APC_DEFAULT_USER  # noqa
from apc.utility import APC_DEFAULT_PASSWORD  # noqa

# Release data
from apc import release

__version__ = release.__version__
__date__ = release.__date__
