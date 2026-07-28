from pydantic import validate_call

from api.externals.db.models.exceptions import NotFoundError
from api.resources.scope.model import ScopeORM


@validate_call(config={"arbitrary_types_allowed": True})
def expand_scopes(
    target_scopes: set[str] | list[str], pool_scope_orms: list[ScopeORM]
) -> list[ScopeORM]:
    """Expands the target scopes into a list of ScopeORM objects based on the provided available scopes.

    Args:
        target_scopes   (set[str] | list[str], required): Target scopes to expand.
        pool_scope_orms (list[ScopeORM]      , required): List of all available scope ORM objects.

    Raises:
        ValueError: If a target scope is not found in the available scopes.

    Returns:
        list[ScopeORM]: Expanded list of ScopeORM objects corresponding to the target scopes.
    """

    # ! Browser cookie limit is 4KB, so disabled to expand all scopes temporarily.
    # if ("all" in target_scopes) or ("*" in target_scopes):
    #     return pool_scope_orms

    _expanded_scopes = set()
    _scope_orm_map = {_scope_orm.value: _scope_orm for _scope_orm in pool_scope_orms}
    for _target_scope in target_scopes:
        if _target_scope in _scope_orm_map:
            _expanded_scopes.add(_scope_orm_map[_target_scope])
        else:
            raise NotFoundError(f"Not found scope: '{_target_scope}'!")

        if _target_scope.endswith(":all"):
            _prefix = _target_scope.removesuffix(":all")
            for _val, _scope_orm in _scope_orm_map.items():
                if _val.startswith(_prefix):
                    _expanded_scopes.add(_scope_orm)
        elif _target_scope.endswith(":*"):
            _prefix = _target_scope.removesuffix(":*")
            for _val, _scope_orm in _scope_orm_map.items():
                if _val.startswith(_prefix):
                    _expanded_scopes.add(_scope_orm)

    _expanded_scopes = list(_expanded_scopes)
    return _expanded_scopes


__all__ = [
    "expand_scopes",
]
