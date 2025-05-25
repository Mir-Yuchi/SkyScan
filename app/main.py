from fastapi import FastAPI
from starlette.middleware import Middleware

from app.middleware import AuthMiddleware
from app.routers import api, web

middleware = [Middleware(AuthMiddleware)]

app = FastAPI(title="SkyScan", middleware=middleware)

app.include_router(web.router)

app.include_router(api.router, prefix="/api")
