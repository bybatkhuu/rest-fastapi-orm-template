# flake8: noqa

from ._base import router
from ._signup import *
from ._auth import *
from ._password import *
from ._inspect import *

__all__ = ["router"]
