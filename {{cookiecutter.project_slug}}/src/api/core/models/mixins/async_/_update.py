import sys
from typing import Any, cast

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

from pydantic import validate_call
from sqlalchemy import Update, update, Result
from sqlalchemy.orm import DeclarativeBase, declarative_mixin
from sqlalchemy.exc import NoResultFound, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from psycopg.errors import (
    NotNullViolation,
    UniqueViolation,
    ForeignKeyViolation,
    CheckViolation,
)

from potato_util.constants import WarnEnum

from api.config import config
from api.core.exceptions import (
    UniqueKeyError,
    EmptyValueError,
    NullConstraintError,
    ForeignKeyError,
    CheckConstraintError,
)
from api.logger import logger

from ._read import AsyncReadMixin


def _raise_integrity_error(err: IntegrityError) -> None:
    """Raise custom exceptions based on SQLAlchemy IntegrityError.

    Args:
        err (IntegrityError, required): SQLAlchemy IntegrityError instance.

    Raises:
        NullConstraintError : If null constraint error occurred.
        UniqueKeyError      : If unique constraint error occurred.
        ForeignKeyError     : If foreign key constraint error occurred.
        CheckConstraintError: If check constraint error occurred.
    """

    _err_orig = err.orig
    if isinstance(_err_orig, NotNullViolation):
        _err_orig = cast(NotNullViolation, _err_orig)
        raise NullConstraintError(f"`{_err_orig.diag.column_name}` cannot be NULL!")
    elif isinstance(_err_orig, UniqueViolation):
        _err_orig = cast(UniqueViolation, _err_orig)
        _detail = _err_orig.diag.message_detail
        _detail = (
            _detail.replace("Key ", "") if _detail else "Unique constraint violation!"
        )
        raise UniqueKeyError(_detail)
    elif isinstance(_err_orig, ForeignKeyViolation):
        _err_orig = cast(ForeignKeyViolation, _err_orig)
        _detail = _err_orig.diag.message_detail
        if _detail:
            _detail = (
                _detail.replace("Key ", "")
                .replace('"', "'")
                .replace(f"table '{config.db.prefix}", "'")
            )
        else:
            _detail = "Foreign key constraint violation!"

        raise ForeignKeyError(_detail)
    elif isinstance(_err_orig, CheckViolation):
        _err_orig = cast(CheckViolation, _err_orig)
        _detail = _err_orig.diag.message_detail
        _detail = (
            _detail.replace("Key ", "") if _detail else "Check constraint violation!"
        )
        raise CheckConstraintError(_detail)

    return


@declarative_mixin
class AsyncUpdateMixin(AsyncReadMixin):
    @validate_call(config={"arbitrary_types_allowed": True})
    async def async_update(
        self,
        async_session: AsyncSession,
        auto_commit: bool = False,
        warn_mode: WarnEnum = WarnEnum.DEBUG,
        **kwargs,
    ) -> Self | DeclarativeBase:
        """Update ORM object into database.

        Args:
            async_session (AsyncSession  , required): SQLAlchemy async_session for database connection.
            auto_commit   (bool          , optional): Auto commit. Defaults to False.
            warn_mode     (WarnEnum      , optional): Warning mode. Defaults to `WarnEnum.DEBUG`.
            **kwargs      (dict[str, Any], optional): Dictionary of update data.

        Raises:
            NoResultFound       : If ORM object ID not found in database.
            NullConstraintError : If null constraint error occurred.
            UniqueKeyError      : If unique constraint error occurred.
            ForeignKeyError     : If foreign key constraint error occurred.
            CheckConstraintError: If check constraint error occurred.
            Exception           : If failed to update object into database.

        Returns:
            Self | DeclarativeBase: Updated ORM object.
        """

        if "id" in kwargs:
            del kwargs["id"]

        try:
            for _key, _val in kwargs.items():
                setattr(self, _key, _val)

            if auto_commit:
                await async_session.commit()

        except Exception as err:
            if auto_commit:
                await async_session.rollback()

            if isinstance(err, NoResultFound):
                raise
            elif isinstance(err, IntegrityError):
                _raise_integrity_error(err=err)

            _message = f"Failed to update `{self.__class__.__name__}` object (self) '{self.id}' ID into database!"
            if warn_mode == WarnEnum.ALWAYS:
                logger.error(_message)
            elif warn_mode == WarnEnum.DEBUG:
                logger.debug(_message)

            raise

        return self

    @classmethod
    @validate_call(config={"arbitrary_types_allowed": True})
    async def async_update_by_id(
        cls,
        async_session: AsyncSession,
        id: str,
        orm_way: bool = False,
        returning: bool = True,
        auto_commit: bool = False,
        warn_mode: WarnEnum = WarnEnum.DEBUG,
        **kwargs,
    ) -> DeclarativeBase | Self:
        """Update ORM object into database by ID.

        Args:
            async_session   (AsyncSession  , required): SQLAlchemy async_session for database connection.
            id              (str           , required): ID of object.
            orm_way         (bool          , optional): Use ORM way to update object into database. Defaults to False.
            returning       (bool          , optional): Return updated ORM object. Defaults to True.
            auto_commit     (bool          , optional): Auto commit. Defaults to False.
            warn_mode       (WarnEnum      , optional): Warning mode. Defaults to `WarnEnum.DEBUG`.
            **kwargs        (dict[str, Any], required): Dictionary of update data.

        Raises:
            EmptyValueError     : If no data provided to update.
            NoResultFound       : If ORM object ID not found in database.
            NullConstraintError : If null constraint error occurred.
            UniqueKeyError      : If unique constraint error occurred.
            ForeignKeyError     : If foreign key constraint error occurred.
            CheckConstraintError: If check constraint error occurred.
            Exception           : If failed to update object into database.

        Returns:
            DeclarativeBase | Self: Updated ORM object.
        """

        if not kwargs:
            raise EmptyValueError("No data provided to update!")

        if "id" in kwargs:
            del kwargs["id"]

        _orm_object: DeclarativeBase | Self | None = None
        if orm_way:
            _orm_object = cast(
                DeclarativeBase | Self,
                await cls.async_get(
                    async_session=async_session,
                    id=id,
                    warn_mode=warn_mode,
                ),
            )
            _orm_object = await cast(Self, _orm_object).async_update(
                async_session=async_session,
                auto_commit=auto_commit,
                warn_mode=warn_mode,
                **kwargs,
            )
        else:
            try:
                _stmt: Update = update(cls).where(cls.id == id).values(**kwargs)
                if returning:
                    _stmt = _stmt.returning(cls)

                _result: Result = await async_session.execute(_stmt)
                if returning:
                    _orm_object = cast(
                        DeclarativeBase | Self | None, _result.scalars().one()
                    )

                    if not _orm_object:
                        raise NoResultFound(
                            f"Not found any `{cls.__name__}` object with '{id}' ID from database!"
                        )

                if auto_commit:
                    await async_session.commit()

                if not returning:
                    _rowcount = getattr(_result, "rowcount", 0)
                    logger.debug(
                        f"Updated '{_rowcount}' row into `{cls.__name__}` ORM table."
                    )

                    if _rowcount == 0:
                        raise NoResultFound(
                            f"Not found any `{cls.__name__}` object with '{id}' ID from database!"
                        )

            except Exception as err:
                if auto_commit:
                    await async_session.rollback()

                if isinstance(err, NoResultFound):
                    raise
                elif isinstance(err, IntegrityError):
                    _raise_integrity_error(err=err)

                _message = f"Failed to update `{cls.__name__}` object with '{id}' ID into database!"
                if warn_mode == WarnEnum.ALWAYS:
                    logger.error(_message)
                elif warn_mode == WarnEnum.DEBUG:
                    logger.debug(_message)

                raise

        _orm_object = cast(DeclarativeBase | Self, _orm_object)
        return _orm_object

    @classmethod
    @validate_call(config={"arbitrary_types_allowed": True})
    async def async_update_by_ids(
        cls,
        async_session: AsyncSession,
        ids: list[str],
        returning: bool = True,
        auto_commit: bool = False,
        warn_mode: WarnEnum = WarnEnum.DEBUG,
        **kwargs,
    ) -> list[DeclarativeBase | Self]:
        """Update ORM objects into database by ID list.

        Args:
            async_session   (AsyncSession  , required): SQLAlchemy async_session for database connection.
            ids             (list[str]     , required): List of IDs.
            returning       (bool          , optional): Return updated ORM object. Defaults to True.
            auto_commit     (bool          , optional): Auto commit. Defaults to False.
            warn_mode       (WarnEnum      , optional): Warning mode. Defaults to `WarnEnum.DEBUG`.
            **kwargs        (dict[str, Any], required): Dictionary of update data.

        Raises:
            EmptyValueError     : If no IDs or data provided to update.
            NoResultFound       : If no ORM objects found with IDs in database.
            NullConstraintError : If null constraint error occurred.
            UniqueKeyError      : If unique constraint error occurred.
            ForeignKeyError     : If foreign key constraint error occurred.
            CheckConstraintError: If check constraint error occurred.
            Exception           : If failed to update objects into database.

        Returns:
            list[DeclarativeBase | Self]: List of updated ORM objects.
        """

        if not ids:
            raise EmptyValueError("No IDs provided to update!")

        if not kwargs:
            raise EmptyValueError("No data provided to update!")

        if "id" in kwargs:
            del kwargs["id"]

        _orm_objects: list[DeclarativeBase | Self] = []
        try:
            _stmt: Update = update(cls).where(cls.id.in_(ids)).values(**kwargs)
            if returning:
                _stmt = _stmt.returning(cls)

            _result: Result = await async_session.execute(_stmt)
            if returning:
                _orm_objects = cast(
                    list[DeclarativeBase | Self], _result.scalars().all()
                )

                if not _orm_objects:
                    raise NoResultFound(
                        f"Not found any `{cls.__name__}` objects with '{ids}' IDs from database!"
                    )

            if auto_commit:
                await async_session.commit()

            if not returning:
                _rowcount = getattr(_result, "rowcount", 0)
                logger.debug(
                    f"Updated '{_rowcount}' row(s) into `{cls.__name__}` ORM table."
                )

                if _rowcount == 0:
                    raise NoResultFound(
                        f"Not found any `{cls.__name__}` objects with '{ids}' IDs from database!"
                    )

        except Exception as err:
            if auto_commit:
                await async_session.rollback()

            if isinstance(err, NoResultFound):
                raise
            elif isinstance(err, IntegrityError):
                _raise_integrity_error(err=err)

            _message = f"Failed to update `{cls.__name__}` objects by '{ids}' IDs into database!"
            if warn_mode == WarnEnum.ALWAYS:
                logger.error(_message)
            elif warn_mode == WarnEnum.DEBUG:
                logger.debug(_message)

            raise

        return _orm_objects

    @classmethod
    @validate_call(config={"arbitrary_types_allowed": True})
    async def async_update_objects(
        cls,
        async_session: AsyncSession,
        orm_objects: list[DeclarativeBase],
        auto_commit: bool = False,
        warn_mode: WarnEnum = WarnEnum.DEBUG,
        **kwargs,
    ) -> list[DeclarativeBase | Self]:
        """Update ORM objects into database.

        Args:
            async_session (AsyncSession         , required): SQLAlchemy async_session for database connection.
            orm_objects   (list[DeclarativeBase], required): List of ORM objects.
            auto_commit   (bool                 , optional): Auto commit. Defaults to False.
            warn_mode     (WarnEnum             , optional): Warning mode. Defaults to `WarnEnum.DEBUG`.
            **kwargs      (dict[str, Any]       , required): Dictionary of update data.

        Raises:
            EmptyValueError     : If no ORM objects or data provided to update.
            NoResultFound       : If no ORM objects found with IDs in database.
            NullConstraintError : If null constraint error occurred.
            UniqueKeyError      : If unique constraint error occurred.
            ForeignKeyError     : If foreign key constraint error occurred.
            CheckConstraintError: If check constraint error occurred.
            Exception           : If failed to update objects into database.

        Returns:
            list[DeclarativeBase | Self]: List of updated ORM objects.
        """

        _orm_objects = cast(list[DeclarativeBase | Self], orm_objects)

        if not _orm_objects:
            raise EmptyValueError("No objects provided to update!")

        if not kwargs:
            raise EmptyValueError("No data provided to update!")

        if "id" in kwargs:
            del kwargs["id"]

        try:
            for _orm_object in _orm_objects:
                for _key, _val in kwargs.items():
                    setattr(_orm_object, _key, _val)

            if auto_commit:
                await async_session.commit()

        except Exception as err:
            if auto_commit:
                await async_session.rollback()

            if isinstance(err, NoResultFound):
                raise
            elif isinstance(err, IntegrityError):
                _raise_integrity_error(err=err)

            _message = f"Failed to update `{cls.__name__}` objects into database!"
            if warn_mode == WarnEnum.ALWAYS:
                logger.error(_message)
            elif warn_mode == WarnEnum.DEBUG:
                logger.debug(_message)

            raise

        return _orm_objects

    @classmethod
    @validate_call(config={"arbitrary_types_allowed": True})
    async def async_update_by_where(
        cls,
        async_session: AsyncSession,
        where: list[dict[str, Any]] | dict[str, Any],
        orm_way: bool = False,
        returning: bool = False,
        auto_commit: bool = False,
        allow_no_result: bool = True,
        warn_mode: WarnEnum = WarnEnum.DEBUG,
        **kwargs,
    ) -> list[DeclarativeBase | Self]:
        """Update ORM objects into database by filter conditions.

        Args:
            async_session   (AsyncSession          , required): SQLAlchemy async_session for database connection.
            where           (list[dict[str, Any]] |
                                     dict[str, Any], required): List of filter conditions.
            orm_way         (bool                  , optional): Use ORM way to update object into database.
                                                                    Defaults to False.
            returning       (bool                  , optional): Return updated ORM object. Defaults to False.
            auto_commit     (bool                  , optional): Auto commit. Defaults to False.
            allow_no_result (bool                  , optional): Allow no result. Defaults to True.
            warn_mode       (WarnEnum              , optional): Warning mode. Defaults to `WarnEnum.DEBUG`.
            **kwargs        (dict[str, Any]        , required): Dictionary of update data.

        Raises:
            EmptyValueError     : If no data provided to update.
            NullConstraintError : If null constraint error occurred.
            UniqueKeyError      : If unique constraint error occurred.
            ForeignKeyError     : If foreign key constraint error occurred.
            CheckConstraintError: If check constraint error occurred.
            Exception           : If failed to update objects into database.

        Returns:
            list[DeclarativeBase | Self]: List of updated ORM objects.
        """

        if not kwargs:
            raise EmptyValueError("No data provided to update!")

        if "id" in kwargs:
            del kwargs["id"]

        _affected_count = 0
        _orm_objects: list[DeclarativeBase | Self] = []
        if orm_way:
            _orm_objects = await cls.async_select_by_where(
                async_session=async_session,
                where=where,
                disable_limit=True,
                warn_mode=warn_mode,
            )

            if _orm_objects:
                _orm_objects = await cls.async_update_objects(
                    async_session=async_session,
                    objects=_orm_objects,
                    auto_commit=auto_commit,
                    warn_mode=warn_mode,
                    **kwargs,
                )
                _affected_count = len(_orm_objects)
        else:
            try:
                _stmt: Update = update(cls)
                _stmt = cast(Update, cls._build_where(stmt=_stmt, where=where))
                _stmt = _stmt.values(**kwargs)
                if returning:
                    _stmt = _stmt.returning(cls)

                _result: Result = await async_session.execute(_stmt)
                if returning:
                    _orm_objects = cast(
                        list[DeclarativeBase | Self], _result.scalars().all()
                    )
                    _affected_count = len(_orm_objects)

                if auto_commit:
                    await async_session.commit()

                if not returning:
                    _affected_count = getattr(_result, "rowcount", 0)
                    logger.debug(
                        f"Updated '{_affected_count}' row(s) into `{cls.__name__}` ORM table."
                    )

            except Exception as err:
                if auto_commit:
                    await async_session.rollback()

                if isinstance(err, IntegrityError):
                    _raise_integrity_error(err=err)

                _message = f"Failed to update `{cls.__name__}` object(s) by '{where}' filter into database!"
                if warn_mode == WarnEnum.ALWAYS:
                    logger.error(_message)
                elif warn_mode == WarnEnum.DEBUG:
                    logger.debug(_message)

                raise

        if (not allow_no_result) and (_affected_count == 0):
            raise NoResultFound(
                f"Not found any `{cls.__name__}` object(s) by '{where}' filter from database!"
            )

        return _orm_objects

    @classmethod
    @validate_call(config={"arbitrary_types_allowed": True})
    async def async_update_all(
        cls,
        async_session: AsyncSession,
        auto_commit: bool = False,
        warn_mode: WarnEnum = WarnEnum.DEBUG,
        **kwargs,
    ) -> None:
        """Update all current table ORM objects in database.

        Args:
            async_session (AsyncSession  , required): SQLAlchemy async_session for database connection.
            auto_commit   (bool          , optional): Auto commit. Defaults to False.
            warn_mode     (WarnEnum      , optional): Warning mode. Defaults to `WarnEnum.DEBUG`.
            **kwargs      (dict[str, Any], required): Dictionary of update data.

        Raises:
            EmptyValueError     : If no data provided to update.
            NullConstraintError : If null constraint error occurred.
            UniqueKeyError      : If unique constraint error occurred.
            ForeignKeyError     : If foreign key constraint error occurred.
            CheckConstraintError: If check constraint error occurred.
            Exception           : If failed to update objects into database.
        """

        if not kwargs:
            raise EmptyValueError("No data provided to update!")

        if "id" in kwargs:
            del kwargs["id"]

        try:
            _stmt: Update = update(cls).values(**kwargs)
            _result: Result = await async_session.execute(_stmt)

            if auto_commit:
                await async_session.commit()

            _rowcount = getattr(_result, "rowcount", 0)
            logger.debug(
                f"Updated '{_rowcount}' row(s) into `{cls.__name__}` ORM table."
            )
        except Exception as err:
            if auto_commit:
                await async_session.rollback()

            if isinstance(err, IntegrityError):
                _raise_integrity_error(err=err)

            _message = f"Failed to update all `{cls.__name__}` objects into database!"
            if warn_mode == WarnEnum.ALWAYS:
                logger.error(_message)
            elif warn_mode == WarnEnum.DEBUG:
                logger.debug(_message)

            raise

        return


__all__ = ["AsyncUpdateMixin"]
