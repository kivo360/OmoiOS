"""Analytics proxy routes for bypassing ad blockers.

This module provides proxy endpoints for PostHog analytics that route through
your own domain. Ad blockers typically block requests to known analytics domains
(like us.i.posthog.com), but they can't block requests to your own API.

The frontend should be configured to use these proxy endpoints instead of
sending requests directly to PostHog.
"""

import httpx
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from omoi_os.config import get_app_settings
from omoi_os.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)

# PostHog endpoints that need to be proxied
# These are the endpoints the PostHog JS SDK calls
POSTHOG_HOST = "https://us.i.posthog.com"


async def proxy_to_posthog(
    request: Request,
    path: str,
    method: str = "POST",
) -> Response:
    """Proxy a request to PostHog.

    Args:
        request: The incoming FastAPI request
        path: The PostHog API path (e.g., "/batch", "/decide")
        method: HTTP method to use

    Returns:
        The response from PostHog
    """
    settings = get_app_settings()
    posthog_host = (
        settings.posthog.host if hasattr(settings, "posthog") else POSTHOG_HOST
    )

    # Build the target URL
    target_url = f"{posthog_host}{path}"

    # Get request body
    body = await request.body()

    # Forward relevant headers
    headers = {
        "Content-Type": request.headers.get("Content-Type", "application/json"),
        "User-Agent": request.headers.get("User-Agent", ""),
    }

    # Add origin header for CORS
    if "Origin" in request.headers:
        headers["Origin"] = request.headers["Origin"]

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            if method == "GET":
                response = await client.get(
                    target_url,
                    headers=headers,
                    params=dict(request.query_params),
                )
            else:
                response = await client.post(
                    target_url,
                    headers=headers,
                    content=body,
                    params=dict(request.query_params),
                )

        # Return the response with same status and headers
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers={
                "Content-Type": response.headers.get(
                    "Content-Type", "application/json"
                ),
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
            },
        )

    except httpx.TimeoutException:
        logger.warning("PostHog proxy timeout", path=path)
        return JSONResponse(
            status_code=504,
            content={"error": "Gateway timeout"},
        )
    except Exception as e:
        logger.error("PostHog proxy error", path=path, error=str(e))
        return JSONResponse(
            status_code=502,
            content={"error": "Bad gateway"},
        )


# ============================================================================
# PostHog Ingest Proxy Endpoints
# These are the main endpoints the PostHog SDK calls
# ============================================================================


@router.post("/e")
@router.post("/e/")
async def proxy_capture(request: Request) -> Response:
    """Proxy event capture requests to PostHog.

    This is the main endpoint for capturing events, pageviews, etc.
    The PostHog SDK sends events here.
    """
    return await proxy_to_posthog(request, "/e/")


@router.post("/batch")
@router.post("/batch/")
async def proxy_batch(request: Request) -> Response:
    """Proxy batch event requests to PostHog.

    The SDK batches multiple events and sends them together.
    """
    return await proxy_to_posthog(request, "/batch/")


@router.post("/capture")
@router.post("/capture/")
async def proxy_capture_alt(request: Request) -> Response:
    """Alternative capture endpoint.

    Some SDK versions use this endpoint instead of /e/.
    """
    return await proxy_to_posthog(request, "/capture/")


@router.post("/track")
@router.post("/track/")
async def proxy_track(request: Request) -> Response:
    """Proxy track requests to PostHog.

    Alternative tracking endpoint used by some integrations.
    """
    return await proxy_to_posthog(request, "/track/")


@router.get("/decide")
@router.post("/decide")
@router.get("/decide/")
@router.post("/decide/")
async def proxy_decide(request: Request) -> Response:
    """Proxy feature flag decide requests to PostHog.

    This endpoint is used for feature flags, A/B testing, and surveys.
    """
    method = request.method
    return await proxy_to_posthog(request, "/decide/", method=method)


@router.post("/engage")
@router.post("/engage/")
async def proxy_engage(request: Request) -> Response:
    """Proxy engage requests to PostHog.

    Used for user identification and properties.
    """
    return await proxy_to_posthog(request, "/engage/")


@router.get("/array/{path:path}")
@router.post("/array/{path:path}")
async def proxy_array(request: Request, path: str) -> Response:
    """Proxy array requests to PostHog.

    Static assets for session recording, heatmaps, etc.
    """
    method = request.method
    return await proxy_to_posthog(request, f"/array/{path}", method=method)


@router.post("/s")
@router.post("/s/")
async def proxy_session_recording(request: Request) -> Response:
    """Proxy session recording data to PostHog.

    Session recording snapshots are sent here.
    """
    return await proxy_to_posthog(request, "/s/")


@router.get("/flags")
@router.post("/flags")
@router.get("/flags/")
@router.post("/flags/")
async def proxy_flags(request: Request) -> Response:
    """Proxy feature flags requests to PostHog.

    Used to fetch feature flag values for the current user.
    """
    method = request.method
    return await proxy_to_posthog(request, "/flags/", method=method)


@router.get("/static/{path:path}")
async def proxy_static(request: Request, path: str) -> Response:
    """Proxy static JS files from PostHog.

    PostHog loads additional JS files for features like:
    - dead-clicks-autocapture.js
    - posthog-recorder.js
    - toolbar.js
    - surveys.js
    - exception-autocapture.js
    """
    return await proxy_to_posthog(request, f"/static/{path}", method="GET")


@router.api_route("/i/v0/e/", methods=["GET", "POST"])
@router.api_route("/i/v0/e", methods=["GET", "POST"])
async def proxy_ingest_v0(request: Request) -> Response:
    """Proxy ingest v0 requests to PostHog.

    Some SDK versions use this newer ingest path format.
    """
    method = request.method
    return await proxy_to_posthog(request, "/i/v0/e/", method=method)


@router.api_route("/{path:path}", methods=["GET", "POST"])
async def proxy_catchall(request: Request, path: str) -> Response:
    """Catch-all proxy for any other PostHog paths.

    This handles any PostHog endpoint we haven't explicitly defined.
    """
    method = request.method
    return await proxy_to_posthog(request, f"/{path}", method=method)


@router.options("/{path:path}")
async def options_handler(path: str) -> Response:
    """Handle CORS preflight requests.

    All analytics proxy endpoints need to handle OPTIONS for CORS.
    """
    return Response(
        content="",
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
            "Access-Control-Max-Age": "86400",
        },
    )
