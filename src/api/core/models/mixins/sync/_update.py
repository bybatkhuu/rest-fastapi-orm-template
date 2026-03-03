from typing import List, Dict, Union, Any

from pydantic import validate_call
from sqlalchemy import Update, update, Result
from sqlalchemy.orm import DeclarativeBase, declarative_mixin, Session
from sqlalchemy.exc import NoResultFound, IntegrityError

from api.core.constants import WarnEnum
from api.config import config

if config.db.dialect == "postgresql":
    from psycopg.errors import (
        NotNullViolation,
        UniqueViolation,
        ForeignKeyViolation,
        CheckViolation,
    )
from api.core.exceptions import (
    UniqueKeyError,
    EmptyValueError,
    NullConstraintError,
    ForeignKeyError,
    CheckConstraintError,
)
from api.logger import logger

from ._read import ReadMixin


@declarative_mixin
class UpdateMixin(ReadMixin):
    @validate_call(config={"arbitrary_types_allowed": True})
    def update(
        self,
        session: Session,
        auto_commit: bool = False,
        warn_mode: WarnEnum = WarnEnum.DEBUG,
        **kwargs,
    ) -> DeclarativeBase:
        """Update ORM object into database.

        Args:
            session     (Session       , required): SQLAlchemy session for database connection.
            auto_commit (bool          , optional): Auto commit. Defaults to False.
            warn_mode   (WarnEnum      , optional): Warning mode. Defaults to `WarnEnum.DEBUG`.
            **kwargs    (Dict[str, Any], optional): Dictionary of update data.

        Raises:
            NoResultFound       : If ORM object ID not found in database.
            NullConstraintError : If null constraint error occurred.
            UniqueKeyError      : If unique constraint error occurred.
            ForeignKeyError     : If foreign key constraint error occurred.
            CheckConstraintError: If check constraint error occurred.
            Exception           : If failed to update object into database.

        Returns:
            DeclarativeBase: Updated ORM object.
        """

        if "id" in kwargs:
            del kwargs["id"]

        try:
            for _key, _val in kwargs.items():
                setattr(self, _key, _val)

            if auto_commit:
                session.commit()

        except Exception as err:
            if auto_commit:
                session.rollback()

            if isinstance(err, NoResultFound):
                raise
            elif isinstance(err, IntegrityError):
                if isinstance(err.orig, NotNullViolation):
                    raise NullConstraintError(
                        f"`{err.orig.diag.column_name}` cannot be NULL."
                    )
                elif isinstance(err.orig, UniqueViolation):
                    _detail = err.orig.diag.message_detail.replace("Key ", "")
                    raise UniqueKeyError(_detail)
                elif isinstance(err.orig, ForeignKeyViolation):
                    _detail = (
                        err.orig.diag.message_detail.replace("Key ", "")
                        .replace('"', "'")
                        .replace(f"table '{config.db.prefix}", "'")
                    )
                    raise ForeignKeyError(_detail)
                elif isinstance(err.orig, CheckViolation):
                    _detail = err.orig.diag.message_detail.replace("Key ", "")
                    raise CheckConstraintError(_detail)

            _message = f"Failed to update `{self.__class__.__name__}` object (self) '{self.id}' ID into database!"
            if warn_mode == WarnEnum.ALWAYS:
                logger.error(_message)
            elif warn_mode == WarnEnum.DEBUG:
                logger.debug(_message)

            raise

        return self

    @classmethod
    @validate_call(config={"arbitrary_types_allowed": True})
    def update_by_id(
        cls,
        session: Session,
        id: str,
        orm_way: bool = False,
        returning: bool = True,
        auto_commit: bool = False,
        warn_mode: WarnEnum = WarnEnum.DEBUG,
        **kwargs,
    ) -> DeclarativeBase:
        """Update ORM object into database by ID.

        Args:
            session     (Session       , required): SQLAlchemy session for database connection.
            id          (str           , required): ID of object.
            orm_way     (bool          , optional): Use ORM way to update object into database. Defaults to False.
            returning   (bool          , optional): Return updated ORM object. Defaults to True.
            auto_commit (bool          , optional): Auto commit. Defaults to False.
            warn_mode   (WarnEnum      , optional): Warning mode. Defaults to `WarnEnum.DEBUG`.
            **kwargs    (Dict[str, Any], required): Dictionary of update data.

        Raises:
            EmptyValueError     : If no data provided to update.
            NoResultFound       : If ORM object ID not found in database.
            NullConstraintError : If null constraint error occurred.
            UniqueKeyError      : If unique constraint error occurred.
            ForeignKeyError     : If foreign key constraint error occurred.
            CheckConstraintError: If check constraint error occurred.
            Exception           : If failed to update object into database.

        Returns:
            DeclarativeBase: Updated ORM object.
        """

        if not kwargs:
            raise EmptyValueError("No data provided to update!")

        if "id" in kwargs:
            del kwargs["id"]

        _orm_object: Union[cls, None] = None
        if orm_way:
            _orm_object: cls = cls.get(
                session=session,
                id=id,
                warn_mode=warn_mode,
            )
            _orm_object: cls = _orm_object.update(
                session=session,
                auto_commit=auto_commit,
                warn_mode=warn_mode,
                **kwargs,
            )
        else:
            try:
                _stmt: Update = update(cls).where(cls.id == id).values(**kwargs)
                if returning:
                    _stmt = _stmt.returning(cls)

                _result: Result = session.execute(_stmt)
                if returning:
                    _orm_object: Union[cls, None] = _result.scalars().one()

                    if not _orm_object:
                        raise NoResultFound(
                            f"Not found any `{cls.__name__}` object with '{id}' ID from database!"
                        )

                if auto_commit:
                    session.commit()

                if not returning:
                    logger.debug(
                        f"Updated '{_result.rowcount}' row into `{cls.__name__}` ORM table."
                    )

                    if _result.rowcount == 0:
                        raise NoResultFound(
                            f"Not found any `{cls.__name__}` object with '{id}' ID from database!"
                        )

            except Exception as err:
                if auto_commit:
                    session.rollback()

                if isinstance(err, NoResultFound):
                    raise
                elif isinstance(err, IntegrityError):
                    if isinstance(err.orig, NotNullViolation):
                        raise NullConstraintError(
                            f"`{err.orig.diag.column_name}` cannot be NULL."
                        )
                    elif isinstance(err.orig, UniqueViolation):
                        _detail = err.orig.diag.message_detail.replace("Key ", "")
                        raise UniqueKeyError(_detail)
                    elif isinstance(err.orig, ForeignKeyViolation):
                        _detail = (
                            err.orig.diag.message_detail.replace("Key ", "")
                            .replace('"', "'")
                            .replace(f"table '{config.db.prefix}", "'")
                        )
                        raise ForeignKeyError(_detail)
                    elif isinstance(err.orig, CheckViolation):
                        _detail = err.orig.diag.message_detail.replace("Key ", "")
                        raise CheckConstraintError(_detail)

                _message = f"Failed to update `{cls.__name__}` object with '{id}' ID into database!"
                if warn_mode == WarnEnum.ALWAYS:
                    logger.error(_message)
                elif warn_mode == WarnEnum.DEBUG:
                    logger.debug(_message)

                raise

        return _orm_object

    @classmethod
    @validate_call(config={"arbitrary_types_allowed": True})
    def update_by_ids(
        cls,
        session: Session,
        ids: List[str],
        returning: bool = True,
        auto_commit: bool = False,
        warn_mode: WarnEnum = WarnEnum.DEBUG,
        **kwargs,
    ) -> List[DeclarativeBase]:
        """Update ORM objects into database by ID list.

        Args:
            session     (Session       , required): SQLAlchemy session for database connection.
            ids         (List[str]     , required): List of IDs.
            returning   (bool          , optional): Return updated ORM object. Defaults to True.
            auto_commit (bool          , optional): Auto commit. Defaults to False.
            warn_mode   (WarnEnum      , optional): Warning mode. Defaults to `WarnEnum.DEBUG`.
            **kwargs    (Dict[str, Any], required): Dictionary of update data.

        Raises:
            EmptyValueError     : If no IDs or data provided to update.
            NoResultFound       : If no ORM objects found with IDs in database.
            NullConstraintError : If null constraint error occurred.
            UniqueKeyError      : If unique constraint error occurred.
            ForeignKeyError     : If foreign key constraint error occurred.
            CheckConstraintError: If check constraint error occurred.
            Exception           : If failed to update objects into database.

        Returns:
            List[DeclarativeBase]: List of updated ORM objects.
        """

        if not ids:
            raise EmptyValueError("No IDs provided to update!")

        if not kwargs:
            raise EmptyValueError("No data provided to update!")

        if "id" in kwargs:
            del kwargs["id"]

        _orm_objects: List[cls] = []
        try:
            _stmt: Update = update(cls).where(cls.id.in_(ids)).values(**kwargs)
            if returning:
                _stmt = _stmt.returning(cls)

            _result: Result = session.execute(_stmt)
            if returning:
                _orm_objects: List[cls] = _result.scalars().all()

                if not _orm_objects:
                    raise NoResultFound(
                        f"Not found any `{cls.__name__}` objects with '{ids}' IDs from database!"
                    )

            if auto_commit:
                session.commit()

            if not returning:
                logger.debug(
                    f"Updated '{_result.rowcount}' row(s) into `{cls.__name__}` ORM table."
                )

                if _result.rowcount == 0:
                    raise NoResultFound(
                        f"Not found any `{cls.__name__}` objects with '{ids}' IDs from database!"
                    )

        except Exception as err:
            if auto_commit:
                session.rollback()

            if isinstance(err, NoResultFound):
                raise
            elif isinstance(err, IntegrityError):
                if isinstance(err.orig, NotNullViolation):
                    raise NullConstraintError(
                        f"`{err.orig.diag.column_name}` cannot be NULL."
                    )
                elif isinstance(err.orig, UniqueViolation):
                    _detail = err.orig.diag.message_detail.replace("Key ", "")
                    raise UniqueKeyError(_detail)
                elif isinstance(err.orig, ForeignKeyViolation):
                    _detail = (
                        err.orig.diag.message_detail.replace("Key ", "")
                        .replace('"', "'")
                        .replace(f"table '{config.db.prefix}", "'")
                    )
                    raise ForeignKeyError(_detail)
                elif isinstance(err.orig, CheckViolation):
                    _detail = err.orig.diag.message_detail.replace("Key ", "")
                    raise CheckConstraintError(_detail)

            _message = f"Failed to update `{cls.__name__}` objects by '{ids}' IDs into database!"
            if warn_mode == WarnEnum.ALWAYS:
                logger.error(_message)
            elif warn_mode == WarnEnum.DEBUG:
                logger.debug(_message)

            raise

        return _orm_objects

    @classmethod
    @validate_call(config={"arbitrary_types_allowed": True})
    def update_objects(
        cls,
        session: Session,
        orm_objects: List[DeclarativeBase],
        auto_commit: bool = False,
        warn_mode: WarnEnum = WarnEnum.DEBUG,
        **kwargs,
    ) -> List[DeclarativeBase]:
        """Update ORM objects into database.

        Args:
            session     (Session              , required): SQLAlchemy session for database connection.
            orm_objects (List[DeclarativeBase], required): List of ORM objects.
            auto_commit (bool                 , optional): Auto commit. Defaults to False.
            warn_mode   (WarnEnum             , optional): Warning mode. Defaults to `WarnEnum.DEBUG`.
            **kwargs    (Dict[str, Any]       , required): Dictionary of update data.

        Raises:
            EmptyValueError     : If no ORM objects or data provided to update.
            NoResultFound       : If no ORM objects found with IDs in database.
            NullConstraintError : If null constraint error occurred.
            UniqueKeyError      : If unique constraint error occurred.
            ForeignKeyError     : If foreign key constraint error occurred.
            CheckConstraintError: If check constraint error occurred.
            Exception           : If failed to update objects into database.

        Returns:
            List[DeclarativeBase]: List of updated ORM objects.
        """

        if not orm_objects:
            raise EmptyValueError("No objects provided to update!")

        if not kwargs:
            raise EmptyValueError("No data provided to update!")

        if "id" in kwargs:
            del kwargs["id"]

        try:
            for _orm_object in orm_objects:
                for _key, _val in kwargs.items():
                    setattr(_orm_object, _key, _val)

            if auto_commit:
                session.commit()

        except Exception as err:
            if auto_commit:
                session.rollback()

            if isinstance(err, NoResultFound):
                raise
            elif isinstance(err, IntegrityError):
                if isinstance(err.orig, NotNullViolation):
                    raise NullConstraintError(
                        f"`{err.orig.diag.column_name}` cannot be NULL."
                    )
                elif isinstance(err.orig, UniqueViolation):
                    _detail = err.orig.diag.message_detail.replace("Key ", "")
                    raise UniqueKeyError(_detail)
                elif isinstance(err.orig, ForeignKeyViolation):
                    _detail = (
                        err.orig.diag.message_detail.replace("Key ", "")
                        .replace('"', "'")
                        .replace(f"table '{config.db.prefix}", "'")
                    )
                    raise ForeignKeyError(_detail)
                elif isinstance(err.orig, CheckViolation):
                    _detail = err.orig.diag.message_detail.replace("Key ", "")
                    raise CheckConstraintError(_detail)

            _message = f"Failed to update `{cls.__name__}` objects into database!"
            if warn_mode == WarnEnum.ALWAYS:
                logger.error(_message)
            elif warn_mode == WarnEnum.DEBUG:
                logger.debug(_message)

            raise

        return orm_objects

    @classmethod
    @validate_call(config={"arbitrary_types_allowed": True})
    def update_by_where(
        cls,
        session: Session,
        where: Union[List[Dict[str, Any]], Dict[str, Any]],
        orm_way: bool = False,
        returning: bool = False,
        auto_commit: bool = False,
        allow_no_result: bool = True,
        warn_mode: WarnEnum = WarnEnum.DEBUG,
        **kwargs,
    ) -> List[DeclarativeBase]:
        """Update ORM objects into database by filter conditions.

        Args:
            session         (Session                    , required): SQLAlchemy session for database connection.
            where           (Union[List[Dict[str, Any]],
                                   Dict[str, Any]]      , required): List of filter conditions.
            orm_way         (bool                       , optional): Use ORM way to update object into database. Defaults to False.
            returning       (bool                       , optional): Return updated ORM object. Defaults to False.
            auto_commit     (bool                       , optional): Auto commit. Defaults to False.
            allow_no_result (bool                       , optional): Allow no result. Defaults to True.
            warn_mode       (WarnEnum                   , optional): Warning mode. Defaults to `WarnEnum.DEBUG`.
            **kwargs        (Dict[str, Any]             , required): Dictionary of update data.

        Raises:
            EmptyValueError     : If no data provided to update.
            NullConstraintError : If null constraint error occurred.
            UniqueKeyError      : If unique constraint error occurred.
            ForeignKeyError     : If foreign key constraint error occurred.
            CheckConstraintError: If check constraint error occurred.
            Exception           : If failed to update objects into database.

        Returns:
            List[DeclarativeBase]: List of updated ORM objects.
        """

        if not kwargs:
            raise EmptyValueError("No data provided to update!")

        if "id" in kwargs:
            del kwargs["id"]

        _affected_count = 0
        _orm_objects: List[cls] = []
        if orm_way:
            _orm_objects: List[cls] = cls.select_by_where(
                session=session,
                where=where,
                disable_limit=True,
                warn_mode=warn_mode,
            )

            if _orm_objects:
                _orm_objects: List[cls] = cls.update_objects(
                    session=session,
                    objects=_orm_objects,
                    auto_commit=auto_commit,
                    warn_mode=warn_mode,
                    **kwargs,
                )
                _affected_count = len(_orm_objects)
        else:
            try:
                _stmt: Update = update(cls)
                _stmt = cls._build_where(stmt=_stmt, where=where)
                _stmt = _stmt.values(**kwargs)
                if returning:
                    _stmt = _stmt.returning(cls)

                _result: Result = session.execute(_stmt)
                if returning:
                    _orm_objects: List[cls] = _result.scalars().all()
                    _affected_count = len(_orm_objects)

                if auto_commit:
                    session.commit()

                if not returning:
                    _affected_count = _result.rowcount
                    logger.debug(
                        f"Updated '{_result.rowcount}' row(s) into `{cls.__name__}` ORM table."
                    )

            except Exception as err:
                if auto_commit:
                    session.rollback()

                if isinstance(err, IntegrityError):
                    if isinstance(err.orig, NotNullViolation):
                        raise NullConstraintError(
                            f"`{err.orig.diag.column_name}` cannot be NULL."
                        )
                    elif isinstance(err.orig, UniqueViolation):
                        _detail = err.orig.diag.message_detail.replace("Key ", "")
                        raise UniqueKeyError(_detail)
                    elif isinstance(err.orig, ForeignKeyViolation):
                        _detail = (
                            err.orig.diag.message_detail.replace("Key ", "")
                            .replace('"', "'")
                            .replace(f"table '{config.db.prefix}", "'")
                        )
                        raise ForeignKeyError(_detail)
                    elif isinstance(err.orig, CheckViolation):
                        _detail = err.orig.diag.message_detail.replace("Key ", "")
                        raise CheckConstraintError(_detail)

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
    def update_all(
        cls,
        session: Session,
        auto_commit: bool = False,
        warn_mode: WarnEnum = WarnEnum.DEBUG,
        **kwargs,
    ) -> None:
        """Update all current table ORM objects in database.

        Args:
            session     (Session       , required): SQLAlchemy session for database connection.
            auto_commit (bool          , optional): Auto commit. Defaults to False.
            warn_mode   (WarnEnum      , optional): Warning mode. Defaults to `WarnEnum.DEBUG`.
            **kwargs    (Dict[str, Any], required): Dictionary of update data.

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
            _result: Result = session.execute(_stmt)

            if auto_commit:
                session.commit()

            logger.debug(
                f"Updated '{_result.rowcount}' row(s) into `{cls.__name__}` ORM table."
            )
        except Exception as err:
            if auto_commit:
                session.rollback()

            if isinstance(err, IntegrityError):
                if isinstance(err.orig, NotNullViolation):
                    raise NullConstraintError(
                        f"`{err.orig.diag.column_name}` cannot be NULL."
                    )
                elif isinstance(err.orig, UniqueViolation):
                    _detail = err.orig.diag.message_detail.replace("Key ", "")
                    raise UniqueKeyError(_detail)
                elif isinstance(err.orig, ForeignKeyViolation):
                    _detail = (
                        err.orig.diag.message_detail.replace("Key ", "")
                        .replace('"', "'")
                        .replace(f"table '{config.db.prefix}", "'")
                    )
                    raise ForeignKeyError(_detail)
                elif isinstance(err.orig, CheckViolation):
                    _detail = err.orig.diag.message_detail.replace("Key ", "")
                    raise CheckConstraintError(_detail)

            _message = f"Failed to update all `{cls.__name__}` objects into database!"
            if warn_mode == WarnEnum.ALWAYS:
                logger.error(_message)
            elif warn_mode == WarnEnum.DEBUG:
                logger.debug(_message)

            raise

        return


__all__ = ["UpdateMixin"]
