"""Create the FastAPI application and register its shared HTTP behavior."""

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import auctions, experiments, simulations
from app.auctions.models import AuctionInputError
from app.config import settings
from app.db import initialize_database


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Prepare persistent storage before accepting requests."""
    initialize_database()
    yield


app = FastAPI(
    title="AuctionLab API",
    version="0.1.0",
    lifespan=lifespan,
    description="First-price and second-price advertisement auction simulator.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type", "Idempotency-Key"],
)


def error_response(
    status_code: int,
    code: str,
    message: str,
    details: Any = None,
) -> JSONResponse:
    """Return API errors in the same envelope for every route."""
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": details,
            }
        },
    )


@app.exception_handler(AuctionInputError)
async def handle_auction_input_error(_: Request, exc: AuctionInputError) -> JSONResponse:
    return error_response(422, "invalid_input", str(exc))


@app.exception_handler(RequestValidationError)
async def handle_request_validation_error(
    _: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Translate Pydantic errors into readable, field-specific messages."""
    details = [
        {
            "field": ".".join(str(part) for part in error["loc"][1:]),
            "message": error["msg"],
        }
        for error in exc.errors()
    ]
    message = "; ".join(
        f"{item['field'] or 'body'}: {item['message']}" for item in details
    )
    return error_response(422, "validation_error", message, details)


@app.exception_handler(HTTPException)
async def handle_http_error(_: Request, exc: HTTPException) -> JSONResponse:
    message = exc.detail if isinstance(exc.detail, str) else "Request failed."
    code = "not_found" if exc.status_code == 404 else "http_error"
    return error_response(exc.status_code, code, message)


@app.get("/api/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(auctions.router)
app.include_router(simulations.router)
app.include_router(experiments.router)
