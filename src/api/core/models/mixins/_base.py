import sys
import json
from uuid import UUID
from datetime import datetime
from typing import Any, cast
from collections.abc import Sequence

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self


from pydantic import validate_call
from sqlalchemy import (
    BigInteger,
    Uuid,
    String,
    DateTime,
    func,
    desc,
    asc,
    inspect,
    Select,
    select,
    Update,
    Delete,
    Subquery,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    declarative_mixin,
    Mapped,
    mapped_column,
    joinedload,
)
from sqlalchemy.util import ReadOnlyProperties

from potato_util.constants import WarnEnum
from potato_util.generator import gen_unique_id

from api.config import config
from api.logger import logger


@declarative_mixin
class IdStrMixin:
    id: Mapped[str] = mapped_column(String(64), primary_key=True, sort_order=-100)


@declarative_mixin
class IdUUIDMixin:
    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, sort_order=-100
    )


@declarative_mixin
class IdIntMixin:
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, sort_order=-100)


@declarative_mixin
class IdIntAutoMixin:
    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, sort_order=-100
    )


@declarative_mixin
class TimestampMixin:
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.CURRENT_TIMESTAMP(),
        sort_order=1001,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        index=True,
        nullable=False,
        server_default=func.CURRENT_TIMESTAMP(),
        sort_order=1002,
    )


@declarative_mixin
class BaseMixin(TimestampMixin, IdStrMixin):
    def __init__(self, warn_mode: WarnEnum = WarnEnum.ALWAYS, **kwargs):
        if "id" not in kwargs:
            kwargs["id"] = self.__class__.gen_unique_id()

        for _key, _val in kwargs.items():
            try:
                getattr(self, _key)
                setattr(self, _key, _val)
            except AttributeError:
                _message = f"Not found '{_key}' attribute in `{self.__class__.__name__}` class."
                if warn_mode == WarnEnum.ALWAYS:
                    logger.warning(_message)
                elif warn_mode == WarnEnum.DEBUG:
                    logger.debug(_message)
                elif warn_mode == WarnEnum.ERROR:
                    logger.error(_message)
                    raise

        super().__init__()

    @classmethod
    def gen_unique_id(cls) -> str:
        """Generate unique ID for ORM object.

        Returns:
            str: Unique ID.
        """

        _prefix = cls.__name__[0:3]
        _id = gen_unique_id(prefix=_prefix)
        return _id

    @validate_call
    def to_dict(
        self,
        excludes: list[str] | None = None,
        load_relations: list[str] | None = None,
    ) -> dict[str, Any]:
        """Convert ORM object to dictionary.

        Args:
            excludes       (list[str] | None, optional): List of attributes to exclude. Defaults to None.
            load_relations (list[str] | None, optional): List of relationships to include. Defaults to None.

        Returns:
            dict[str, Any]: Dictionary of ORM object.
        """

        _dict = {}
        _inspect = inspect(self)
        assert _inspect is not None, "Failed to inspect ORM object!"

        _columns: ReadOnlyProperties = _inspect.mapper.column_attrs
        for _column in _columns:
            _column_name = _column.key
            if (not excludes) or (_column_name not in excludes):
                _dict[_column_name] = getattr(self, _column_name)

        if load_relations:
            for _relation in load_relations:
                if _relation and hasattr(self.__class__, _relation):
                    _attr = getattr(self, _relation)
                    if (not isinstance(_attr, str)) and isinstance(_attr, Sequence):
                        _dict[_relation] = []
                        for _item in _attr:
                            if isinstance(_item, DeclarativeBase):
                                _dict[_relation].append(cast(Self, _item).to_dict())
                    elif isinstance(_attr, DeclarativeBase):
                        _dict[_relation] = cast(Self, _attr).to_dict()
                    elif _attr is None:
                        _dict[_relation] = None
                    else:
                        logger.warning(f"Can't include '{_relation}' relationship!")

        return _dict

    @validate_call
    def to_json(
        self,
        excludes: list[str] | None = None,
        load_relations: list[str] | None = None,
    ) -> str:
        """Convert ORM object to JSON string.

        Args:
            excludes       (list[str] | None, optional): List of attributes to exclude. Defaults to None.
            load_relations (list[str] | None, optional): List of relationships to include. Defaults to None.

        Returns:
            str: JSON string of ORM object.
        """

        _json = json.dumps(
            self.to_dict(excludes=excludes, load_relations=load_relations),
            default=str,
            ensure_ascii=False,
        )
        return _json

    @classmethod
    @validate_call(config={"arbitrary_types_allowed": True})
    def to_dict_list(
        cls,
        orm_objects: list[Self],
        excludes: list[str] | None = None,
        load_relations: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Convert list of ORM objects to list of dictionaries.

        Args:
            orm_objects    (list[DeclarativeBase], required): List of ORM objects.
            excludes       (list[str] | None, optional): List of attributes to exclude. Defaults to None.
            load_relations (list[str] | None, optional): List of relationships to include. Defaults to None.

        Returns:
            list[dict[str, Any]]: List of dictionaries from ORM objects.
        """

        _dict_list = []
        for _orm_object in orm_objects:
            _dict_list.append(
                _orm_object.to_dict(excludes=excludes, load_relations=load_relations)
            )

        return _dict_list

    @classmethod
    @validate_call
    def from_json(cls, json_str: str) -> Self:
        """Convert JSON string to ORM object.

        Args:
            json_str (str, required): JSON string.

        Returns:
            Self: ORM object.
        """

        _dict = json.loads(json_str)
        _orm_object = cls(**_dict)
        return _orm_object

    def __str__(self) -> str:
        """Convert ORM object to string representation.

        Returns:
            str: String representation of ORM object.
        """

        _str = self.to_json()
        return _str

    @classmethod
    @validate_call(config={"arbitrary_types_allowed": True})
    def _build_where(
        cls,
        stmt: Select | Update | Delete,
        where: list[dict[str, Any]] | dict[str, Any],
    ) -> Select | Update | Delete:
        """Build SQLAlchemy SQL statement with `where` filter conditions.

        Args:
            stmt  (Select | Update | Delete    , required): SQLAlchemy SQL statement.
            where (list[dict[str, Any]] | dict[str, Any], required): List of filter conditions

        Raises:
            ValueError: If `column` or `value` key doesn't exist in `where` filter.

        Returns:
            Select | Update | Delete: Built SQLAlchemy SQL statement.
        """

        if isinstance(where, dict):
            where = [where]

        for _where in where:
            if "column" not in _where:
                raise ValueError("Not found 'column' key in 'where'!")

            if "value" not in _where:
                raise ValueError("Not found 'value' key in 'where'!")

            if (
                ("op" not in _where)
                or (_where["op"] == "eq")
                or (_where["op"] == "equal")
                or (_where["op"] == "=")
                or (_where["op"] == "==")
            ):
                stmt = stmt.where(getattr(cls, _where["column"]) == _where["value"])
            elif (
                (_where["op"] == "ne")
                or (_where["op"] == "not_equal")
                or (_where["op"] == "!=")
            ):
                stmt = stmt.where(getattr(cls, _where["column"]) != _where["value"])
            elif _where["op"] == "like":
                stmt = stmt.where(
                    getattr(cls, _where["column"]).like(f'%{_where["value"]}%')
                )
            elif (_where["op"] == "gt") or (_where["op"] == ">"):
                stmt = stmt.where(getattr(cls, _where["column"]) > _where["value"])
            elif (_where["op"] == "ge") or (_where["op"] == ">="):
                stmt = stmt.where(getattr(cls, _where["column"]) >= _where["value"])
            elif (_where["op"] == "lt") or (_where["op"] == "<"):
                stmt = stmt.where(getattr(cls, _where["column"]) < _where["value"])
            elif (_where["op"] == "le") or (_where["op"] == "<="):
                stmt = stmt.where(getattr(cls, _where["column"]) <= _where["value"])
            elif _where["op"] == "between":
                stmt = stmt.where(
                    getattr(cls, _where["column"]).between(
                        _where["value"][0], _where["value"][1]
                    )
                )

        return stmt

    @classmethod
    @validate_call
    def _build_select(
        cls,
        where: list[dict[str, Any]] | dict[str, Any] | None = None,
        offset: int = 0,
        limit: int = config.db.select_limit,
        order_by: list[str] | str | None = None,
        is_desc: bool = True,
        joins: list[str] | None = None,
        disable_limit: bool = False,
    ) -> Select:
        """Build SQLAlchemy select statement for ORM object.

        Args:
            where          (list[dict[str, Any]] |
                                  dict[str, Any] | None, optional): List of filter conditions. Defaults to None.
            offset         (int                        , optional): Offset number. Defaults to 0.
            limit          (int                        , optional): Limit number. Defaults to `config.db.select_limit`.
            order_by       (list[str] | str | None     , optional): List of order by columns. Defaults to None.
            is_desc        (bool                       , optional): Is sort descending or ascending. Defaults to True.
            joins          (list[str] | None           , optional): List of joinable relationships. Defaults to None.
            disable_limit  (bool                       , optional): Disable select limit. Defaults to False.

        Returns:
            Select: Built SQLAlchemy select statement.
        """

        _sort_direct = desc
        if not is_desc:
            _sort_direct = asc

        # Deffered join to improve performance:
        # Subquery:
        _sub_select: Select = select(cls.id)
        if where:
            _sub_select = cast(Select, cls._build_where(stmt=_sub_select, where=where))

        if order_by:
            if isinstance(order_by, str):
                order_by = [order_by]

            if isinstance(order_by, list):
                for _order_by in order_by:
                    if hasattr(cls, _order_by):
                        _sub_select = _sub_select.order_by(
                            _sort_direct(getattr(cls, _order_by))
                        )

        _sub_select: Select = _sub_select.order_by(_sort_direct(cls.id))

        if not disable_limit:
            _sub_select = _sub_select.limit(limit).offset(offset)

        # Make into subquery:
        _sub_query: Subquery = _sub_select.subquery()

        # Main query:
        _stmt: Select = select(cls).join(_sub_query, cls.id == _sub_query.c.id)

        if joins:
            for _join in joins:
                if _join and hasattr(cls, _join):
                    _stmt = _stmt.options(joinedload(getattr(cls, _join)))

        if order_by:
            for _order_by in order_by:
                if hasattr(cls, _order_by):
                    _stmt = _stmt.order_by(_sort_direct(getattr(cls, _order_by)))

        _stmt = _stmt.order_by(_sort_direct(cls.id))
        return _stmt


__all__ = [
    "IdStrMixin",
    "IdUUIDMixin",
    "IdIntMixin",
    "IdIntAutoMixin",
    "TimestampMixin",
    "BaseMixin",
]
