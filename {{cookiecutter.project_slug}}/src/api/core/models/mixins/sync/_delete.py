import sys
from typing import Any, cast

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

from pydantic import validate_call
from sqlalchemy import Delete, delete, Result
from sqlalchemy.orm import DeclarativeBase, declarative_mixin, Session
from sqlalchemy.exc import NoResultFound, DBAPIError
from psycopg.errors import ForeignKeyViolation

from potato_util.constants import WarnEnum

from api.config import config
from api.core.exceptions import EmptyValueError, ForeignKeyError
from api.logger import logger

from ._read import ReadMixin


def _raise_fk_error(err: DBAPIError) -> None:
    """Raise ForeignKeyError if the error is a foreign key violation error.

    Args:
        err (DBAPIError, required): SQLAlchemy DBAPIError instance.

    Raises:
        ForeignKeyError: If the error is a foreign key violation error.
    """

    _err_orig = err.orig
    if isinstance(_err_orig, ForeignKeyViolation):
        _err_orig = cast(ForeignKeyViolation, _err_orig)
        _detail = _err_orig.diag.message_detail
        if _detail:
            _detail = (
                _detail.replace("Key ", "")
                .replace('"', "'")
                .replace(f"table '{config.db.prefix}", "'")
            )
        else:
            _detail = "Foreign key violation error occurred!"

        raise ForeignKeyError(_detail)

    return


@declarative_mixin
class DeleteMixin(ReadMixin):
    @validate_call(config={"arbitrary_types_allowed": True})
    def delete(
        self,
        session: Session,
        auto_commit: bool = False,
        warn_mode: WarnEnum = WarnEnum.DEBUG,
    ) -> None:
        """Delete ORM object from database.

        Args:
            session     (Session , required): SQLAlchemy session for database connection.
            auto_commit (bool    , optional): Auto commit. Defaults to False.
            warn_mode   (WarnEnum, optional): Warning mode. Defaults to `WarnEnum.DEBUG`.

        Raises:
            NoResultFound: If ORM object not found in database.
            Exception    : If failed to delete ORM object from database.
        """

        try:
            session.delete(self)

            if auto_commit:
                session.commit()

        except Exception as err:
            if auto_commit:
                session.rollback()

            if isinstance(err, NoResultFound):
                raise
            if isinstance(err, DBAPIError):
                _raise_fk_error(err=err)

            _message = f"Failed to delete `{self.__class__.__name__}` object (self) '{self.id}' ID from database!"
            if warn_mode == WarnEnum.ALWAYS:
                logger.error(_message)
            elif warn_mode == WarnEnum.DEBUG:
                logger.debug(_message)

            raise

        return

    @classmethod
    @validate_call(config={"arbitrary_types_allowed": True})
    def delete_by_id(
        cls,
        session: Session,
        id: str,
        orm_way: bool = False,
        auto_commit: bool = False,
        warn_mode: WarnEnum = WarnEnum.DEBUG,
    ) -> None:
        """Delete ORM object from database by ID.

        Args:
            session     (Session , required): SQLAlchemy session for database connection.
            id          (str     , required): ORM object ID.
            auto_commit (bool    , optional): Auto commit. Defaults to False.
            warn_mode   (WarnEnum, optional): Warning mode. Defaults to `WarnEnum.DEBUG`.

        Raises:
            NoResultFound: If ORM object ID not found in database.
            Exception    : If failed to delete ORM object from database by ID.
        """

        if orm_way:
            _orm_object = cast(
                Self, cls.get(session=session, id=id, warn_mode=warn_mode)
            )
            _orm_object.delete(
                session=session,
                auto_commit=auto_commit,
                warn_mode=warn_mode,
            )
        else:
            try:
                _stmt: Delete = delete(cls).where(cls.id == id)
                _result: Result = session.execute(_stmt)

                if auto_commit:
                    session.commit()

                _rowcount = getattr(_result, "rowcount", 0)
                logger.debug(
                    f"Deleted '{_rowcount}' row from `{cls.__name__}` ORM table."
                )

                if _rowcount == 0:
                    raise NoResultFound(
                        f"Not found any `{cls.__name__}` object with '{id}' ID from database!"
                    )

            except Exception as err:
                if auto_commit:
                    session.rollback()

                if isinstance(err, NoResultFound):
                    raise
                if isinstance(err, DBAPIError):
                    _raise_fk_error(err=err)

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
    def delete_by_ids(
        cls,
        session: Session,
        ids: list[str],
        auto_commit: bool = False,
        warn_mode: WarnEnum = WarnEnum.DEBUG,
    ) -> None:
        """Delete rows/ORM objects from database by ID list.

        Args:
            session     (Session  , required): SQLAlchemy session for database connection.
            ids         (list[str], required): List of IDs.
            auto_commit (bool     , optional): Auto commit. Defaults to False.
            warn_mode   (WarnEnum , optional): Warning mode. Defaults to `WarnEnum.DEBUG`.

        Raises:
            EmptyValueError: If no IDs provided to delete.
            NoResultFound  : If no result found for IDs.
            Exception      : If failed to delete rows/ORM objects from database.
        """

        if not ids:
            raise EmptyValueError("No IDs provided to delete!")

        try:
            _stmt: Delete = delete(cls).where(cls.id.in_(ids))
            _result: Result = session.execute(_stmt)

            if auto_commit:
                session.commit()

            _rowcount = getattr(_result, "rowcount", 0)
            logger.debug(
                f"Deleted '{_rowcount}' row(s) from `{cls.__name__}` ORM table."
            )

            if _rowcount == 0:
                raise NoResultFound(
                    f"Not found any `{cls.__name__}` objects with '{ids}' IDs from database!"
                )

        except Exception as err:
            if auto_commit:
                session.rollback()

            if isinstance(err, NoResultFound):
                raise
            if isinstance(err, DBAPIError):
                _raise_fk_error(err=err)

            _message = f"Failed to delete `{cls.__name__}` objects by '{ids}' IDs from database!"
            if warn_mode == WarnEnum.ALWAYS:
                logger.error(_message)
            elif warn_mode == WarnEnum.DEBUG:
                logger.debug(_message)

            raise

        return

    @classmethod
    @validate_call(config={"arbitrary_types_allowed": True})
    def delete_objects(
        cls,
        session: Session,
        orm_objects: list[DeclarativeBase],
        auto_commit: bool = False,
        warn_mode: WarnEnum = WarnEnum.DEBUG,
    ) -> None:
        """Delete ORM objects from database.

        Args:
            session     (Session              , required): SQLAlchemy
            objects     (list[DeclarativeBase], required): List of ORM objects.
            auto_commit (bool                 , optional): Auto commit. Defaults to False.
            warn_mode   (WarnEnum             , optional): Warning mode. Defaults to `WarnEnum.DEBUG`.

        Raises:
            EmptyValueError: If no ORM objects provided to delete.
            NoResultFound  : If no result found for ORM objects.
            Exception      : If failed to delete ORM objects from database.
        """

        _orm_objects = cast(list[DeclarativeBase | Self], orm_objects)

        if not _orm_objects:
            raise EmptyValueError("No ORM objects provided to delete!")

        try:
            for _orm_object in _orm_objects:
                session.delete(_orm_object)

            if auto_commit:
                session.commit()

        except Exception as err:
            if auto_commit:
                session.rollback()

            if isinstance(err, NoResultFound):
                raise
            if isinstance(err, DBAPIError):
                _raise_fk_error(err=err)

            _message = f"Failed to delete `{cls.__name__}` objects from database!"
            if warn_mode == WarnEnum.ALWAYS:
                logger.error(_message)
            elif warn_mode == WarnEnum.DEBUG:
                logger.debug(_message)

            raise

        return

    @classmethod
    @validate_call(config={"arbitrary_types_allowed": True})
    def delete_by_where(
        cls,
        session: Session,
        where: list[dict[str, Any]] | dict[str, Any],
        orm_way: bool = False,
        auto_commit: bool = False,
        allow_no_result: bool = False,
        warn_mode: WarnEnum = WarnEnum.DEBUG,
    ) -> None:
        """Delete ORM objects from database by filter conditions.

        Args:
            session         (Session               , required): SQLAlchemy session for database connection.
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
            _orm_objects = cast(
                list[DeclarativeBase],
                cls.select_by_where(
                    session=session,
                    where=where,
                    disable_limit=True,
                    warn_mode=warn_mode,
                ),
            )

            if _orm_objects:
                cls.delete_objects(
                    session=session,
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
                _stmt = cast(Delete, cls._build_where(stmt=_stmt, where=where))
                _result: Result = session.execute(_stmt)

                if auto_commit:
                    session.commit()

                _rowcount = getattr(_result, "rowcount", 0)
                logger.debug(
                    f"Deleted '{_rowcount}' row(s) from `{cls.__name__}` ORM table."
                )

                if (not allow_no_result) and (_rowcount == 0):
                    raise NoResultFound(
                        f"Not found any `{cls.__name__}` objects by '{where}' filter from database!"
                    )

            except Exception as err:
                if auto_commit:
                    session.rollback()

                if isinstance(err, NoResultFound):
                    raise
                if isinstance(err, DBAPIError):
                    _raise_fk_error(err=err)

                _message = f"Failed to delete `{cls.__name__}` object by '{where}' filter from database!"
                if warn_mode == WarnEnum.ALWAYS:
                    logger.error(_message)
                elif warn_mode == WarnEnum.DEBUG:
                    logger.debug(_message)

                raise

        return

    @classmethod
    @validate_call(config={"arbitrary_types_allowed": True})
    def delete_all(
        cls,
        session: Session,
        auto_commit: bool = False,
        warn_mode: WarnEnum = WarnEnum.DEBUG,
    ) -> None:
        """Delete all ORM objects from database.

        Args:
            session     (Session , required): SQLAlchemy session for database connection.
            auto_commit (bool    , optional): Auto commit. Defaults to False.
            warn_mode   (WarnEnum, optional): Warning mode. Defaults to `WarnEnum.DEBUG`.

        Raises:
            Exception: If failed to delete all ORM objects from database.
        """

        try:
            _stmt = delete(cls)
            _result: Result = session.execute(_stmt)

            if auto_commit:
                session.commit()

            _rowcount = getattr(_result, "rowcount", 0)
            logger.debug(
                f"Deleted '{_rowcount}' row(s) from `{cls.__name__}` ORM table."
            )
        except Exception as err:
            if auto_commit:
                session.rollback()

            if isinstance(err, DBAPIError):
                _raise_fk_error(err=err)

            _message = f"Failed to delete all `{cls.__name__}` objects from database!"
            if warn_mode == WarnEnum.ALWAYS:
                logger.error(_message)
            elif warn_mode == WarnEnum.DEBUG:
                logger.debug(_message)

            raise

        return


__all__ = ["DeleteMixin"]
