# app/main.py
from fastapi import FastAPI

from app.routers import api, web

app = FastAPI(title="SkyScan")

app.include_router(web.router)

app.include_router(api.router, prefix="/api")
