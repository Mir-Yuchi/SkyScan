# app/routers/web.py
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/", response_class=HTMLResponse, tags=["web"])
async def read_root(request: Request):
    """
    Landing page for SkyScan.
    """
    return HTMLResponse(
        """
        <html>
          <head><title>SkyScan</title></head>
          <body>
            <h1>Welcome to SkyScan!</h1>
            <p>Type a city name in the URL (/api/weather?city=…) or use the future form here.</p>
          </body>
        </html>
        """
    )
