from typing import Any

from pydantic import validate_call
from sqlalchemy import Select, select, Result, func
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import DeclarativeBase, declarative_mixin, Session

from potato_util.constants import WarnEnum

from api.config import config
from api.core.exceptions import EmptyValueError
from api.core.models.mixins import BaseMixin
from api.logger import logger


@declarative_mixin
class ReadMixin(BaseMixin):
    @classmethod
    @validate_call(config={"arbitrary_types_allowed": True})
    def select_by_where(
        cls,
        session: Session,
        where: list[dict[str, Any]] | dict[str, Any],
        offset: int = 0,
        limit: int = config.db.select_limit,
        order_by: list[str] | str | None = None,
        is_desc: bool = True,
        joins: list[str] | None = None,
        disable_limit: bool = False,
        allow_no_result: bool = True,
        warn_mode: WarnEnum = WarnEnum.DEBUG,
    ) -> list[DeclarativeBase]:
        """Select ORM objects from database by where filter conditions.

        Args:
            session         (Session                    , required): SQLAlchemy session for database connection.
            where           (Union[List[Dict[str, Any]],
                                         Dict[str, Any]], required): List of filter conditions.
            offset          (int                        , optional): Number of objects to skip. Defaults to 0.
            limit           (int                        , optional): Number of objects to limit. Defaults to `config.db.select_limit`.
            order_by        (Union[List[str], str, None], optional): List of order by columns. Defaults to None.
            is_desc         (bool                       , optional): Is sort descending or ascending. Defaults to True.
            joins           (Optional[List[str]]        , optional): List of joinable relationships. Defaults to None.
            disable_limit   (bool                       , optional): Disable select limit. Defaults to False.
            allow_no_result (bool                       , optional): Allow no result. Defaults to True.
            warn_mode       (WarnEnum                   , optional): Warning mode. Defaults to `WarnEnum.DEBUG`.

        Raises:
            NoResultFound: If no result found and `allow_no_result` is False.
            Exception    : If failed to get ORM objects from database by where filter conditions.

        Returns:
            List[DeclarativeBase]: List of ORM objects.
        """

        _orm_objects: list[cls] = []
        try:
            _stmt: Select = cls._build_select(
                where=where,
                offset=offset,
                limit=limit,
                order_by=order_by,
                is_desc=is_desc,
                joins=joins,
                disable_limit=disable_limit,
            )

            _result: Result = session.execute(_stmt)
            if joins:
                _result = _result.unique()

            _orm_objects: list[cls] = _result.scalars().all()
        except Exception:
            _message = f"Failed to get `{cls.__name__}` objects from database by filtering with '{where}'!"
            if warn_mode == WarnEnum.ALWAYS:
                logger.error(_message)
            elif warn_mode == WarnEnum.DEBUG:
                logger.debug(_message)

            raise

        if (not allow_no_result) and (not _orm_objects):
            raise NoResultFound(
                f"Not found any `{cls.__name__}` objects from database by filtering with '{where}'!"
            )

        return _orm_objects

    @classmethod
    @validate_call(config={"arbitrary_types_allowed": True})
    def select(
        cls,
        session: Session,
        offset: int = 0,
        limit: int = config.db.select_limit,
        is_desc: bool = True,
        joins: list[str] | None = None,
        disable_limit: bool = False,
        allow_no_result: bool = True,
        warn_mode: WarnEnum = WarnEnum.DEBUG,
    ) -> list[DeclarativeBase]:
        """Select ORM objects from database.

        Args:
            session         (Session            , required): SQLAlchemy session for database connection.
            offset          (int                , optional): Number of objects to skip. Defaults to 0.
            limit           (int                , optional): Number of objects to limit. Defaults to `config.db.select_limit`.
            is_desc         (bool               , optional): Is sort descending or ascending. Defaults to True.
            joins           (Optional[List[str]], optional): List of joinable relationships. Defaults to None.
            disable_limit   (bool               , optional): Disable select limit. Defaults to False.
            allow_no_result (bool               , optional): Allow no result. Defaults to True.
            warn_mode       (WarnEnum           , optional): Warning mode. Defaults to `WarnEnum.DEBUG`.

        Raises:
            Exception: Any exception from `select_by_where()`.

        Returns:
            List[DeclarativeBase]: List of ORM objects.
        """

        try:
            _orm_objects: list[cls] = cls.select_by_where(
                session=session,
                where=[],
                offset=offset,
                limit=limit,
                is_desc=is_desc,
                joins=joins,
                disable_limit=disable_limit,
                allow_no_result=allow_no_result,
                warn_mode=WarnEnum.IGNORE,
            )
        except Exception:
            _message = f"Failed to get `{cls.__name__}` objects from database!"
            if warn_mode == WarnEnum.ALWAYS:
                logger.error(_message)
            elif warn_mode == WarnEnum.DEBUG:
                logger.debug(_message)

            raise

        return _orm_objects

    @classmethod
    @validate_call(config={"arbitrary_types_allowed": True})
    def get(
        cls,
        session: Session,
        id: str,
        allow_no_result: bool = False,
        warn_mode: WarnEnum = WarnEnum.DEBUG,
    ) -> DeclarativeBase | None:
        """Get ORM object from database by ID.

        Args:
            session         (Session , required): SQLAlchemy session for database connection.
            id              (str     , required): ID of object.
            allow_no_result (bool    , optional): Allow no result. Defaults to False.
            warn_mode       (WarnEnum, optional): Warning mode. Defaults to `WarnEnum.DEBUG`.

        Raises:
            NoResultFound: If object ID doesn't exist in database and `allow_no_result` is False.
            Exception    : If failed to get ORM object from database by ID.

        Returns:
            Union[DeclarativeBase, None]: ORM object or None.
        """

        _orm_object: cls | None = None
        try:
            _orm_object: cls | None = session.get(cls, id)
        except Exception:
            _message = (
                f"Failed to get `{cls.__name__}` object with '{id}' ID from database!"
            )
            if warn_mode == WarnEnum.ALWAYS:
                logger.error(_message)
            elif warn_mode == WarnEnum.DEBUG:
                logger.debug(_message)

            raise

        if (not allow_no_result) and (not _orm_object):
            raise NoResultFound(
                f"Not found any `{cls.__name__}` object with '{id}' ID from database!"
            )

        return _orm_object

    @classmethod
    @validate_call(config={"arbitrary_types_allowed": True})
    def get_by_where(
        cls,
        session: Session,
        where: list[dict[str, Any]] | dict[str, Any],
        joins: list[str] | None = None,
        allow_no_result: bool = True,
        warn_mode: WarnEnum = WarnEnum.DEBUG,
    ) -> DeclarativeBase | None:
        """Get ORM object from database by where filter conditions.

        Args:
            session         (Session                    , required): SQLAlchemy session for database connection.
            where           (Union[List[Dict[str, Any]],
                                   Dict[str, Any]]      , required): List of filter conditions. Defaults to None.
            joins           (Optional[List[str]]        , optional): List of joinable relationships. Defaults to None.
            allow_no_result (bool                       , optional): Allow no result. Defaults to True.
            warn_mode       (WarnEnum                   , optional): Warning mode. Defaults to `WarnEnum.DEBUG`.

        Raises:
            NoResultFound: If no result found and `allow_no_result` is False.
            Exception    : Any exception from `select_by_where()`.

        Returns:
            Union[DeclarativeBase, None]: ORM object or None.
        """

        _orm_object: cls | None = None
        try:
            _orm_objects: list[cls] = cls.select_by_where(
                session=session,
                where=where,
                limit=1,
                joins=joins,
                allow_no_result=allow_no_result,
                warn_mode=WarnEnum.IGNORE,
            )
        except NoResultFound:
            raise
        except Exception:
            _message = f"Failed to get `{cls.__name__}` object from database by filtering with '{where}'!"
            if warn_mode == WarnEnum.ALWAYS:
                logger.error(_message)
            elif warn_mode == WarnEnum.DEBUG:
                logger.debug(_message)

            raise

        if _orm_objects:
            _orm_object: cls = _orm_objects[0]

        return _orm_object

    @classmethod
    @validate_call(config={"arbitrary_types_allowed": True})
    def get_by_ids(
        cls, session: Session, ids: list[str], warn_mode: WarnEnum = WarnEnum.DEBUG
    ) -> list[DeclarativeBase]:
        """Get ORM objects from database by IDs.

        Args:
            session   (Session  , required): SQLAlchemy session for database connection.
            ids       (List[str], required): List of IDs.
            warn_mode (WarnEnum , optional): Warning mode. Defaults to `WarnEnum.DEBUG`.

        Raises:
            EmptyValueError: If no IDs provided to select.
            NoResultFound  : If no result found.
            Exception      : If failed to get ORM objects from database by IDs.

        Returns:
            List[DeclarativeBase]: List of ORM objects.
        """

        if not ids:
            raise EmptyValueError("No IDs provided to select!")

        _orm_objects: list[cls] = []
        try:
            _stmt: Select = select(cls).where(cls.id.in_(ids))
            _result: Result = session.execute(_stmt)
            _orm_objects: list[cls] = _result.scalars().all()

            if not _orm_objects:
                raise NoResultFound(
                    f"Not found any `{cls.__name__}` objects with '{ids}' IDs from database!"
                )

        except NoResultFound:
            raise
        except Exception:
            _message = f"Failed to get `{cls.__name__}` objects with '{ids}' IDs from database!"
            if warn_mode == WarnEnum.ALWAYS:
                logger.error(_message)
            elif warn_mode == WarnEnum.DEBUG:
                logger.debug(_message)

            raise

        return _orm_objects

    @classmethod
    @validate_call(config={"arbitrary_types_allowed": True})
    def exists_by_id(
        cls, session: Session, id: str, warn_mode: WarnEnum = WarnEnum.DEBUG
    ) -> bool:
        """Check if ORM object exists in database by ID.

        Args:
            session   (Session , required): SQLAlchemy session for database connection.
            id        (str     , required): ID of object.
            warn_mode (WarnEnum, optional): Warning mode. Defaults to `WarnEnum.DEBUG`.

        Raises:
            Exception: If failed to check if ORM object exists in database by ID.

        Returns:
            bool: True if exists, False otherwise.
        """

        _is_exists = False
        try:
            _stmt: Select = select(cls.id).where(cls.id == id)
            _result: Result = session.execute(_stmt)
            if _result.scalar():
                _is_exists = True

        except Exception:
            _message = f"Failed to check if `{cls.__name__}` object by '{id}' ID exists in database!"
            if warn_mode == WarnEnum.ALWAYS:
                logger.error(_message)
            elif warn_mode == WarnEnum.DEBUG:
                logger.debug(_message)

            raise

        return _is_exists

    @validate_call(config={"arbitrary_types_allowed": True})
    def exists(self, session: Session, warn_mode: WarnEnum = WarnEnum.DEBUG) -> bool:
        """Check if ORM object exists in database.

        Args:
            session   (Session , required): SQLAlchemy session for database connection.
            warn_mode (WarnEnum, optional): Warning mode. Defaults to `WarnEnum.DEBUG`.

        Raises:
            Exception: If failed to check if ORM object exists in database.

        Returns:
            bool: True if exists, False otherwise.
        """

        _is_exists = False
        try:
            _is_exists = self.__class__.exists_by_id(
                session=session,
                id=self.id,
                warn_mode=WarnEnum.IGNORE,
            )
        except Exception:
            _message = f"Failed to check if `{self.__class__.__name__}` object '{self.id}' ID exists in database!"
            if warn_mode == WarnEnum.ALWAYS:
                logger.error(_message)
            elif warn_mode == WarnEnum.DEBUG:
                logger.debug(_message)

            raise

        return _is_exists

    @classmethod
    @validate_call(config={"arbitrary_types_allowed": True})
    def count_by_where(
        cls,
        session: Session,
        where: list[dict[str, Any]] | dict[str, Any],
        warn_mode: WarnEnum = WarnEnum.DEBUG,
    ) -> int:
        """Count ORM objects in database by filter conditions.

        Args:
            session   (Session                    , required): SQLAlchemy session for database connection.
            where     (Union[List[Dict[str, Any]],
                             Dict[str, Any]]      , required): List of filter conditions.
            warn_mode (WarnEnum                   , optional): Warning mode. Defaults to `WarnEnum.DEBUG`.

        Raises:
            Exception: If failed to count ORM objects in database by filter conditions.

        Returns:
            int: Count of ORM objects in database.
        """

        _count = 0
        try:
            _stmt: Select = select(func.count()).select_from(cls)
            if where:
                _stmt: Select = cls._build_where(stmt=_stmt, where=where)

            _result: Result = session.execute(_stmt)
            _count: int = _result.scalar()
        except Exception:
            _message = f"Failed to count `{cls.__name__}` objects by '{where}' filter in database!"
            if warn_mode == WarnEnum.ALWAYS:
                logger.error(_message)
            elif warn_mode == WarnEnum.DEBUG:
                logger.debug(_message)

            raise

        return _count

    @classmethod
    @validate_call(config={"arbitrary_types_allowed": True})
    def count(cls, session: Session, warn_mode: WarnEnum = WarnEnum.DEBUG) -> int:
        """Count all ORM objects in database.

        Args:
            session   (Session , required): SQLAlchemy session for database connection.
            warn_mode (WarnEnum, optional): Warning mode. Defaults to `WarnEnum.DEBUG`.

        Raises:
            Exception: If failed to count ORM objects in database.

        Returns:
            int: Count of ORM objects in database.
        """

        _count = 0
        try:
            _count: int = cls.count_by_where(
                session=session,
                where=[],
                warn_mode=WarnEnum.IGNORE,
            )
        except Exception:
            _message = f"Failed to count all `{cls.__name__}` objects from database!"
            if warn_mode == WarnEnum.ALWAYS:
                logger.error(_message)
            elif warn_mode == WarnEnum.DEBUG:
                logger.debug(_message)

            raise

        return _count


__all__ = ["ReadMixin"]
