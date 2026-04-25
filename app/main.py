from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.routers import todos, calendar, emails, scenarios

app = FastAPI(
    title="AISA Internal System",
    version="1.0.0",
    description="FastAPI service exposing Todo, Calendar/Event, and Email/Scenario surfaces for the AISA Spring 26 benchmark.",
)


# --- Guardian / error handlers ---

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation error",
            "detail": exc.errors(),
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc),
        },
    )


# --- Routers ---

app.include_router(todos.router)
app.include_router(calendar.router)
app.include_router(scenarios.router)
app.include_router(emails.router)


# --- Health check ---

@app.get("/", tags=["health"])
def health_check() -> dict:
    return {"status": "ok", "service": "AISA Internal System"}
