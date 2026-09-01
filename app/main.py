from fastapi import FastAPI

from app.config import settings
from app.routers import assets, auth, health, portfolios, transactions

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
)


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
