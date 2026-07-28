import os
import pathlib

from pydantic import validate_call
from fastapi import FastAPI

from fastapi.staticfiles import StaticFiles

_current_file_dir = pathlib.Path(__file__).resolve().parent


@validate_call(config={"arbitrary_types_allowed": True})
def add_mounts(app: FastAPI) -> None:
    """Add mounts to FastAPI app.

    Args:
        app (FastAPI): FastAPI app instance.
    """

    app.mount(
        "/static",
        StaticFiles(directory=os.path.join(_current_file_dir, "static")),
        name="static",
    )
    # Add mounts here

    return


__all__ = ["add_mounts"]
