from typing import cast, Any

from sqlalchemy.orm import Session
from alembic import op

from potato_util.dt import now_utc_dt
from potato_util.crypto import password as password_utils
from potato_util.io import create_dir

from api.config import config
from api.resources.scope.model import ScopeORM
from api.resources.role.model import RoleORM
from api.resources.role_scope.model import RoleScopeORM
from api.resources.role_scope import utils as role_scope_utils
from api.resources.user.schemas import UserStatusEnum
from api.resources.user.model import UserORM
from api.resources.user_role.model import UserRoleORM


def populate_scopes(session: Session) -> None:
    """Populate scopes into database.

    Args:
        session (Session): SQLAlchemy session for database connection.
    """

    _scopes: list[dict[str, Any]] = []
    for _scope in config.api.rbac.scopes:
        _scopes.append(
            {
                "value": _scope,
                "protected": True,
            }
        )

    ScopeORM.bulk_insert(session=session, raw_data=_scopes, returning=False)
    return


def populate_roles(session: Session) -> None:
    """Populate roles into database.

    Args:
        session (Session): SQLAlchemy session for database connection.
    """

    RoleORM.bulk_insert(
        session=session,
        raw_data=config.api.rbac.roles,
        returning=False,
    )
    return


def populate_role_scopes(session: Session) -> None:
    """Populate role scopes into database.

    Args:
        session (Session): SQLAlchemy session for database connection.
    """

    _all_scope_orms = cast(list[ScopeORM], ScopeORM.select(session=session, limit=0))

    for _role in config.api.rbac.roles:
        _target_scopes = _role.pop("scopes")
        _role_orm = cast(
            RoleORM,
            RoleORM.get_by_where(
                session=session,
                where=[{"column": "name", "value": _role["name"]}],
                allow_no_result=False,
            ),
        )

        _expanded_scope_orms = role_scope_utils.expand_scopes(
            target_scopes=_target_scopes, pool_scope_orms=_all_scope_orms
        )
        for _scope_orm in _expanded_scope_orms:
            RoleScopeORM.insert(
                session=session,
                role_name=_role_orm.name,
                scope_value=_scope_orm.value,
                returning=False,
            )

    return


def populate_users(session: Session) -> None:
    """Populate users into database.

    Args:
        session (Session): SQLAlchemy session for database connection.
    """

    _current_dt = now_utc_dt()

    for _user in config.api.user.users:
        _user_password_hash = password_utils.hash(
            password=_user.password,
            password_pepper=config.api.security.password.pepper,
        )
        UserORM.insert(
            session=session,
            password_hash=_user_password_hash,
            status=UserStatusEnum.ACTIVE,
            verified_at=_current_dt,
            returning=False,
            **_user.model_dump(exclude={"password", "roles"})
        )
        _user_dir = config.api.paths.user_dir.format(user_id=_user.id)
        create_dir(_user_dir)

    return


def populate_user_roles(session: Session) -> None:
    """Populate user roles into database.

    Args:
        session (Session): SQLAlchemy session for database connection.
    """

    for _user in config.api.user.users:
        for _role in _user.roles:
            _role_orm = cast(
                RoleORM,
                RoleORM.get_by_where(
                    session=session,
                    where=[{"column": "name", "value": _role}],
                    allow_no_result=False,
                ),
            )
            UserRoleORM.insert(
                session=session,
                user_id=_user.id,
                role_name=_role_orm.name,
                returning=False,
            )
    return


def populate_all(session: Session) -> None:
    """Populate all data into database.

    Args:
        session (Session): SQLAlchemy session for database connection.
    """

    populate_scopes(session=session)
    populate_roles(session=session)
    populate_role_scopes(session=session)
    populate_users(session=session)
    populate_user_roles(session=session)
    return


def drop_all() -> None:
    """Drop all data from database.

    Args:
        session (Session): SQLAlchemy session for database connection.
    """

    op.execute('DELETE FROM "fot_user_role";')
    op.execute('DELETE FROM "fot_user";')
    op.execute('DELETE FROM "fot_role_scope";')
    op.execute('DELETE FROM "fot_role";')
    op.execute('DELETE FROM "fot_scope";')
    return


__all__ = [
    "populate_scopes",
    "populate_roles",
    "populate_all",
    "drop_all",
]
