from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from scalar_fastapi import get_scalar_api_reference, Theme, AgentScalarConfig

from potato_util.http.fastapi import get_base_url

from api.config import config

router = APIRouter(include_in_schema=False)


@router.get(
    "/",
    summary="Root - Redirection",
    description=f"Redirect to base endpoint: '{config.api.prefix}/'",
    status_code=307,
)
async def get_root_redirect():
    return RedirectResponse(url=f"{config.api.prefix}/")


if config.api.docs.enabled:
    if config.api.docs.openapi_url:

        @router.get(
            "/openapi.json",
            summary="OpenAPI JSON - Redirection",
            description=f"Redirect to OpenAPI JSON: '{config.api.docs.openapi_url}'",
            status_code=307,
        )
        async def get_openapi_json_redirect():
            return RedirectResponse(url=f"{config.api.docs.openapi_url}")

    if config.api.docs.docs_url:

        @router.get(
            "/docs",
            summary="Swagger UI docs - Redirection",
            description=f"Redirect to Swagger UI docs: '{config.api.docs.docs_url}'",
            status_code=307,
        )
        async def get_docs_redirect():
            return RedirectResponse(url=f"{config.api.docs.docs_url}")

    if config.api.docs.redoc_url:

        @router.get(
            "/redoc",
            summary="Redoc - Redirection",
            description=f"Redirect to Redoc: '{config.api.docs.redoc_url}'",
            status_code=307,
        )
        async def get_redoc_redirect():
            return RedirectResponse(url=f"{config.api.docs.redoc_url}")

    if config.api.docs.scalar_url:

        @router.get(
            "/scalar",
            summary="Scalar API Docs - Redirection",
            description=f"Redirect to Scalar API Docs: '{config.api.docs.scalar_url}'",
            status_code=307,
        )
        async def get_scalar_redirect():
            return RedirectResponse(url=f"{config.api.docs.scalar_url}")

        @router.get(
            f"{config.api.docs.scalar_url}",
            summary="Scalar API Docs",
            description="Get scalar API reference documentation.",
        )
        async def get_scalar(request: Request):

            _base_url = get_base_url(request)
            _html_response = get_scalar_api_reference(
                title=config.api.title,
                openapi_url=config.api.docs.openapi_url,
                theme=Theme.BLUE_PLANET,
                servers=[
                    {
                        "url": _base_url,
                        "description": "Local API server",
                    },
                    {
                        "url": "https://staging-api.example.com",
                        "description": "Staging API server",
                    },
                    {
                        "url": "https://api.example.com",
                        "description": "Production API server",
                    },
                ],
                default_open_all_tags=True,
                expand_all_responses=True,
                hide_models=True,
                hide_client_button=True,
                agent=AgentScalarConfig(disabled=True),
                telemetry=False,
            )
            return _html_response


__all__ = ["router"]
