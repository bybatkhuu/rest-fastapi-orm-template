class EmptyValueError(ValueError):
    """Class for catching required input empty errors.

    Inherits:
        ValueError: ValueError class from Python.
    """

    pass


class PrimaryKeyError(ValueError):
    """Class for catching primary key errors from database.

    Inherits:
        ValueError: ValueError class from Python.
    """

    pass


class UniqueKeyError(ValueError):
    """Class for catching unique constraint errors from database.

    Inherits:
        ValueError: ValueError class from Python.
    """

    pass


class NullConstraintError(ValueError):
    """Class for catching null constraint errors from database.

    Inherits:
        ValueError: ValueError class from Python.
    """

    pass


class ForeignKeyError(ValueError):
    """Class for catching foreign key constraint errors from database.

    Inherits:
        ValueError: ValueError class from Python.
    """

    pass


class RestrictViolationError(ValueError):
    """Class for catching restrict violation errors from database.

    Inherits:
        ValueError: ValueError class from Python.
    """

    pass


class CheckConstraintError(ValueError):
    """Class for catching check constraint errors from database.

    Inherits:
        ValueError: ValueError class from Python.
    """

    pass


class ExclusionConstraintError(ValueError):
    """Class for catching exclusion constraint errors from database.

    Inherits:
        ValueError: ValueError class from Python.
    """

    pass


class NotFoundError(ValueError):
    """Class for catching not found errors from database.

    Inherits:
        ValueError: ValueError class from Python.
    """

    pass


__all__ = [
    "EmptyValueError",
    "PrimaryKeyError",
    "UniqueKeyError",
    "NullConstraintError",
    "ForeignKeyError",
    "RestrictViolationError",
    "CheckConstraintError",
    "ExclusionConstraintError",
    "NotFoundError",
]
