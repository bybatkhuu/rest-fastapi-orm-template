from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase, declared_attr
from sqlalchemy.ext.asyncio import AsyncAttrs

from potato_util import camel_to_snake

from api.config import config

from .mixins import AsyncCRUDMixin, CRUDMixin

_NAMING_CONVENTION = {
    "ix": "ix__%(table_name)s__%(column_0_name)s",
    "uq": "uq__%(table_name)s__%(column_0_name)s",
    "ck": "ck__%(table_name)s__%(constraint_name)s",
    "fk": "fk__%(table_name)s__%(column_0_name)s",
    "pk": "pk__%(table_name)s",
}


class AsyncBaseORM(AsyncCRUDMixin, AsyncAttrs, DeclarativeBase):
    """Async base class for all ORM models.

    Inherits:
        AsyncCRUDMixin : Async mixin class for CRUD operations and other common attributes/methods.
        AsyncAttrs     : Mixin class for async attributes support (awaitable).
        DeclarativeBase: Base class for ORM models.
    """

    __table_args__ = {"extend_existing": True}

    metadata = MetaData(naming_convention=_NAMING_CONVENTION)

    @declared_attr.directive
    def __tablename__(cls) -> str:
        _table_name = camel_to_snake(cls.__name__).replace("_orm", "")
        _table_name = f"{config.db.prefix}{_table_name}"
        return _table_name


class SyncBaseORM(CRUDMixin, DeclarativeBase):
    """Base class for all ORM models.

    Inherits:
        CRUDMixin      : Mixin class for CRUD operations and other common attributes/methods.
        AsyncAttrs     : Mixin class for async attributes support (awaitable).
        DeclarativeBase: Base class for ORM models.
    """

    __table_args__ = {"extend_existing": True}

    metadata = MetaData(naming_convention=_NAMING_CONVENTION)

    @declared_attr.directive
    def __tablename__(cls) -> str:
        _table_name = camel_to_snake(cls.__name__).replace("_orm", "")
        _table_name = f"{config.db.prefix}{_table_name}"
        return _table_name


class BaseORM(CRUDMixin, AsyncCRUDMixin, AsyncAttrs, DeclarativeBase):
    """Base class for all ORM models.

    Inherits:
        CRUDMixin      : Mixin class for CRUD operations and other common attributes/methods.
        AsyncCRUDMixin : Async mixin class for CRUD operations and other common attributes/methods.
        AsyncAttrs     : Mixin class for async attributes support (awaitable).
        DeclarativeBase: Base class for ORM models.
    """

    __table_args__ = {"extend_existing": True}

    metadata = MetaData(naming_convention=_NAMING_CONVENTION)

    @declared_attr.directive
    def __tablename__(cls) -> str:
        _table_name = camel_to_snake(cls.__name__).replace("_orm", "")
        _table_name = f"{config.db.prefix}{_table_name}"
        return _table_name


__all__ = [
    "AsyncBaseORM",
    "SyncBaseORM",
    "BaseORM",
]
