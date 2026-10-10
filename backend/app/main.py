from contextlib import asynccontextmanager

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
    initialize_database()
    yield

app = FastAPI(title="AuctionLab API", version="0.1.0", lifespan=lifespan,
              description="First-price and second-price advertisement auction simulator.")

app.add_middleware(CORSMiddleware, allow_origins=settings.origins, allow_methods=["GET", "POST", "DELETE"],
                   allow_headers=["Content-Type", "Idempotency-Key"])


def _error(status: int, code: str, message: str, details=None) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message, "details": details}})


@app.exception_handler(AuctionInputError)
async def _input_error(_: Request, exc: AuctionInputError):
    return _error(422, "invalid_input", str(exc))


@app.exception_handler(RequestValidationError)
async def _validation_error(_: Request, exc: RequestValidationError):
    details = [{"field": ".".join(str(p) for p in e["loc"][1:]), "message": e["msg"]} for e in exc.errors()]
    msg = "; ".join(f"{d['field'] or 'body'}: {d['message']}" for d in details)
    return _error(422, "validation_error", msg, details)


@app.exception_handler(HTTPException)
async def _http_error(_: Request, exc: HTTPException):
    message = exc.detail if isinstance(exc.detail, str) else "Request failed."
    return _error(exc.status_code, "not_found" if exc.status_code == 404 else "http_error", message)


@app.get("/api/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok"}


app.include_router(auctions.router)
app.include_router(simulations.router)
app.include_router(experiments.router)
