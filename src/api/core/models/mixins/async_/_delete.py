from typing import Any

from pydantic import validate_call
from sqlalchemy import Delete, delete, Result
from sqlalchemy.orm import DeclarativeBase, declarative_mixin
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from potato_util.constants import WarnEnum

from api.config import config

if config.db.dialect == "postgresql":
    from psycopg.errors import ForeignKeyViolation
# else:
#     from sqlalchemy.exc import IntegrityError as ForeignKeyViolation
from api.core.exceptions import EmptyValueError, ForeignKeyError
from api.logger import logger

from ._read import AsyncReadMixin


@declarative_mixin
class AsyncDeleteMixin(AsyncReadMixin):
    @validate_call(config={"arbitrary_types_allowed": True})
    async def async_delete(
        self,
        async_session: AsyncSession,
        auto_commit: bool = False,
        warn_mode: WarnEnum = WarnEnum.DEBUG,
    ) -> None:
        """Delete ORM object from database.

        Args:
            async_session (AsyncSession, required): SQLAlchemy async_session for database connection.
            auto_commit   (bool        , optional): Auto commit. Defaults to False.
            warn_mode     (WarnEnum    , optional): Warning mode. Defaults to `WarnEnum.DEBUG`.

        Raises:
            NoResultFound: If ORM object not found in database.
            Exception    : If failed to delete ORM object from database.
        """

        try:
            await async_session.delete(self)

            if auto_commit:
                await async_session.commit()

        except Exception as err:
            if auto_commit:
                await async_session.rollback()

            if isinstance(err, NoResultFound):
                raise
            elif hasattr(err, "orig") and isinstance(err.orig, ForeignKeyViolation):
                _detail = (
                    err.orig.diag.message_detail.replace("Key ", "")
                    .replace('"', "'")
                    .replace(f"table '{config.db.prefix}", "'")
                )
                raise ForeignKeyError(_detail)

            _message = f"Failed to delete `{self.__class__.__name__}` object (self) '{self.id}' ID from database!"
            if warn_mode == WarnEnum.ALWAYS:
                logger.error(_message)
            elif warn_mode == WarnEnum.ONCE:
                logger.warning(_message)

            raise

        return

    @classmethod
    @validate_call(config={"arbitrary_types_allowed": True})
    async def async_delete_by_id(
        cls,
        async_session: AsyncSession,
        id: str,
        orm_way: bool = False,
        auto_commit: bool = False,
        warn_mode: WarnEnum = WarnEnum.DEBUG,
    ) -> None:
        """Delete ORM object from database by ID.

        Args:
            async_session (AsyncSession, required): SQLAlchemy async_session for database connection.
            id            (str         , required): ORM object ID.
            auto_commit   (bool        , optional): Auto commit. Defaults to False.
            warn_mode     (WarnEnum    , optional): Warning mode. Defaults to `WarnEnum.DEBUG`.

        Raises:
            NoResultFound: If ORM object ID not found in database.
            Exception    : If failed to delete ORM object from database by ID.
        """

        if orm_way:
            _orm_object: cls = await cls.async_get(
                async_session=async_session, id=id, warn_mode=warn_mode
            )
            await _orm_object.async_delete(
                async_session=async_session,
                auto_commit=auto_commit,
                warn_mode=warn_mode,
            )
        else:
            try:
                _stmt: Delete = delete(cls).where(cls.id == id)
                _result: Result = await async_session.execute(_stmt)

                if auto_commit:
                    await async_session.commit()

                logger.debug(
                    f"Deleted '{_result.rowcount}' row from `{cls.__name__}` ORM table."
                )

                if _result.rowcount == 0:
                    raise NoResultFound(
                        f"Not found any `{cls.__name__}` object with '{id}' ID from database!"
                    )

            except Exception as err:
                if auto_commit:
                    await async_session.rollback()

                if isinstance(err, NoResultFound):
                    raise
                elif hasattr(err, "orig") and isinstance(err.orig, ForeignKeyViolation):
                    _detail = (
                        err.orig.diag.message_detail.replace("Key ", "")
                        .replace('"', "'")
                        .replace(f"table '{config.db.prefix}", "'")
                    )
                    raise ForeignKeyError(_detail)

                _message = (
                    f"Failed to delete `{cls.__name__}` object '{id}' ID from database!"
                )
                if warn_mode == WarnEnum.ALWAYS:
                    logger.error(_message)
                elif warn_mode == WarnEnum.DEBUG:
                    logger.debug(_message)

                raise

        return

    @classmethod
    @validate_call(config={"arbitrary_types_allowed": True})
    async def async_delete_by_ids(
        cls,
        async_session: AsyncSession,
        ids: list[str],
        auto_commit: bool = False,
        warn_mode: WarnEnum = WarnEnum.DEBUG,
    ) -> None:
        """Delete rows/ORM objects from database by ID list.

        Args:
            async_session (AsyncSession, required): SQLAlchemy async_session for database connection.
            ids           (list[str]   , required): List of IDs.
            auto_commit   (bool        , optional): Auto commit. Defaults to False.
            warn_mode     (WarnEnum    , optional): Warning mode. Defaults to `WarnEnum.DEBUG`.

        Raises:
            EmptyValueError: If no IDs provided to delete.
            NoResultFound  : If no result found for IDs.
            Exception      : If failed to delete rows/ORM objects from database.
        """

        if not ids:
            raise EmptyValueError("No IDs provided to delete!")

        try:
            _stmt: Delete = delete(cls).where(cls.id.in_(ids))
            _result: Result = await async_session.execute(_stmt)

            if auto_commit:
                await async_session.commit()

            logger.debug(
                f"Deleted '{_result.rowcount}' row(s) from `{cls.__name__}` ORM table."
            )

            if _result.rowcount == 0:
                raise NoResultFound(
                    f"Not found any `{cls.__name__}` objects with '{ids}' IDs from database!"
                )

        except Exception as err:
            if auto_commit:
                await async_session.rollback()

            if isinstance(err, NoResultFound):
                raise
            elif hasattr(err, "orig") and isinstance(err.orig, ForeignKeyViolation):
                _detail = (
                    err.orig.diag.message_detail.replace("Key ", "")
                    .replace('"', "'")
                    .replace(f"table '{config.db.prefix}", "'")
                )
                raise ForeignKeyError(_detail)

            _message = f"Failed to delete `{cls.__name__}` objects by '{ids}' IDs from database!"
            if warn_mode == WarnEnum.ALWAYS:
                logger.error(_message)
            elif warn_mode == WarnEnum.DEBUG:
                logger.debug(_message)

            raise

        return

    @classmethod
    @validate_call(config={"arbitrary_types_allowed": True})
    async def async_delete_objects(
        cls,
        async_session: AsyncSession,
        orm_objects: list[DeclarativeBase],
        auto_commit: bool = False,
        warn_mode: WarnEnum = WarnEnum.DEBUG,
    ) -> None:
        """Delete ORM objects from database.

        Args:
            async_session (AsyncSession         , required): SQLAlchemy
            objects       (list[DeclarativeBase], required): List of ORM objects.
            auto_commit   (bool                 , optional): Auto commit. Defaults to False.
            warn_mode     (WarnEnum             , optional): Warning mode. Defaults to `WarnEnum.DEBUG`.

        Raises:
            EmptyValueError: If no ORM objects provided to delete.
            NoResultFound  : If no result found for ORM objects.
            Exception      : If failed to delete ORM objects from database.
        """

        if not orm_objects:
            raise EmptyValueError("No ORM objects provided to delete!")

        try:
            for _orm_object in orm_objects:
                await async_session.delete(_orm_object)

            if auto_commit:
                await async_session.commit()

        except Exception as err:
            if auto_commit:
                await async_session.rollback()

            if isinstance(err, NoResultFound):
                raise
            elif hasattr(err, "orig") and isinstance(err.orig, ForeignKeyViolation):
                _detail = (
                    err.orig.diag.message_detail.replace("Key ", "")
                    .replace('"', "'")
                    .replace(f"table '{config.db.prefix}", "'")
                )
                raise ForeignKeyError(_detail)

            _message = f"Failed to delete `{cls.__name__}` objects from database!"
            if warn_mode == WarnEnum.ALWAYS:
                logger.error(_message)
            elif warn_mode == WarnEnum.DEBUG:
                logger.debug(_message)

            raise

        return

    @classmethod
    @validate_call(config={"arbitrary_types_allowed": True})
    async def async_delete_by_where(
        cls,
        async_session: AsyncSession,
        where: list[dict[str, Any]] | dict[str, Any],
        orm_way: bool = False,
        auto_commit: bool = False,
        allow_no_result: bool = False,
        warn_mode: WarnEnum = WarnEnum.DEBUG,
    ) -> None:
        """Delete ORM objects from database by filter conditions.

        Args:
            async_session   (AsyncSession          , required): SQLAlchemy async_session for database connection.
            where           (list[dict[str, Any]] |
                                     dict[str, Any], required): List of filter conditions.
            orm_way         (bool                  , optional): Use ORM way to delete objects. Defaults to False.
            auto_commit     (bool                  , optional): Auto commit. Defaults to False.
            allow_no_result (bool                  , optional): Allow no result found. Defaults to False.
            warn_mode       (WarnEnum              , optional): Warning mode. Defaults to `WarnEnum.DEBUG`.

        Raises:
            Exception: If failed to delete ORM objects from database by filter conditions.
        """

        if orm_way:
            _orm_objects: list[cls] = await cls.async_select_by_where(
                async_session=async_session,
                where=where,
                disable_limit=True,
                warn_mode=warn_mode,
            )

            if _orm_objects:
                await cls.async_delete_objects(
                    async_session=async_session,
                    orm_objects=_orm_objects,
                    auto_commit=auto_commit,
                    warn_mode=warn_mode,
                )
            elif not allow_no_result:
                raise NoResultFound(
                    f"Not found any `{cls.__name__}` objects by '{where}' filter from database!"
                )
        else:
            try:
                _stmt: Delete = delete(cls)
                _stmt = cls._build_where_stmt(stmt=_stmt, where=where)
                _result: Result = await async_session.execute(_stmt)

                if auto_commit:
                    await async_session.commit()

                logger.debug(
                    f"Deleted '{_result.rowcount}' row(s) from `{cls.__name__}` ORM table."
                )

                if (not allow_no_result) and (_result.rowcount == 0):
                    raise NoResultFound(
                        f"Not found any `{cls.__name__}` objects by '{where}' filter from database!"
                    )

            except Exception as err:
                if auto_commit:
                    await async_session.rollback()

                if isinstance(err, NoResultFound):
                    raise
                elif hasattr(err, "orig") and isinstance(err.orig, ForeignKeyViolation):
                    _detail = (
                        err.orig.diag.message_detail.replace("Key ", "")
                        .replace('"', "'")
                        .replace(f"table '{config.db.prefix}", "'")
                    )
                    raise ForeignKeyError(_detail)

                _message = f"Failed to delete `{cls.__name__}` object by '{where}' filter from database!"
                if warn_mode == WarnEnum.ALWAYS:
                    logger.error(_message)
                elif warn_mode == WarnEnum.DEBUG:
                    logger.debug(_message)

                raise

        return

    @classmethod
    @validate_call(config={"arbitrary_types_allowed": True})
    async def async_delete_all(
        cls,
        async_session: AsyncSession,
        auto_commit: bool = False,
        warn_mode: WarnEnum = WarnEnum.DEBUG,
    ) -> None:
        """Delete all ORM objects from database.

        Args:
            async_session (AsyncSession, required): SQLAlchemy async_session for database connection.
            auto_commit   (bool        , optional): Auto commit. Defaults to False.
            warn_mode     (WarnEnum    , optional): Warning mode. Defaults to `WarnEnum.DEBUG`.

        Raises:
            Exception: If failed to delete all ORM objects from database.
        """

        try:
            _stmt = delete(cls)
            _result: Result = await async_session.execute(_stmt)

            if auto_commit:
                await async_session.commit()

            logger.debug(
                f"Deleted '{_result.rowcount}' row(s) from `{cls.__name__}` ORM table."
            )
        except Exception as err:
            if auto_commit:
                await async_session.rollback()

            if hasattr(err, "orig") and isinstance(err.orig, ForeignKeyViolation):
                _detail = (
                    err.orig.diag.message_detail.replace("Key ", "")
                    .replace('"', "'")
                    .replace(f"table '{config.db.prefix}", "'")
                )
                raise ForeignKeyError(_detail)

            _message = f"Failed to delete all `{cls.__name__}` objects from database!"
            if warn_mode == WarnEnum.ALWAYS:
                logger.error(_message)
            elif warn_mode == WarnEnum.DEBUG:
                logger.debug(_message)

            raise

        return


__all__ = ["AsyncDeleteMixin"]
