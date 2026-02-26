import time
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.core.logging import logger


async def error_handler_middleware(request: Request, call_next):
    start = time.time()
    try:
        response = await call_next(request)
        duration = round((time.time() - start) * 1000, 2)
        logger.info(
            "Request completed",
            method=request.method,
            url=str(request.url),
            status=response.status_code,
            duration_ms=duration,
        )
        return response
    except Exception as exc:
        duration = round((time.time() - start) * 1000, 2)
        logger.error(
            "Unhandled exception",
            method=request.method,
            url=str(request.url),
            error=str(exc),
            duration_ms=duration,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error. Please try again."},
        )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = [
        {"field": " -> ".join(str(l) for l in e["loc"]), "message": e["msg"]}
        for e in exc.errors()
    ]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Validation error", "errors": errors},
    )
