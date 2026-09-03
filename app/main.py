from fastapi import FastAPI

from app.config import settings
from app.logging_config import configure_logging
from app.middleware import request_logging_middleware
from app.routers import assets, auth, health, portfolios, transactions

configure_logging(settings.log_level)

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
)
app.middleware("http")(request_logging_middleware)


# --------------------------------------------------
# API routers
# --------------------------------------------------


app.include_router(auth.router)
app.include_router(portfolios.router)
app.include_router(assets.router)
app.include_router(transactions.router)
app.include_router(health.router)


# --------------------------------------------------
# Root endpoint
# --------------------------------------------------


@app.get("/")
def home():
    return {"message": "Portfolio API is running"}
