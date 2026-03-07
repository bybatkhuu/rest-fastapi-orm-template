from sqlalchemy.orm import declarative_mixin

from .async_ import AsyncCreateMixin, AsyncDeleteMixin
from .sync import CreateMixin, DeleteMixin


@declarative_mixin
class AsyncCRUDMixin(AsyncCreateMixin, AsyncDeleteMixin):
    """Mixin class for CRUD operations and other common attributes/methods.

    Inherits:
        AsyncCreateMixin: Mixin class for async create/update operation.
        AsyncDeleteMixin: Mixin class for async delete/read/basic operation.
    """

    pass


@declarative_mixin
class CRUDMixin(CreateMixin, DeleteMixin):
    """Mixin class for CRUD operations and other common attributes/methods.

    Inherits:
        CreateMixin: Mixin class for create/update operation.
        DeleteMixin: Mixin class for delete/read/basic operation.
    """

    pass


__all__ = [
    "AsyncCRUDMixin",
    "CRUDMixin",
]
