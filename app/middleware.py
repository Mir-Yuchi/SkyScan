import uuid

from fastapi import Request
from sqlalchemy import select
from starlette.middleware.base import BaseHTTPMiddleware

from app.db.session import AsyncSessionLocal
from app.models.user import User


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware: ensures each visitor has an anon_uuid cookie and User record, attaches User to request.state.user.
    """

    async def dispatch(self, request: Request, call_next):
        """Ensure each visitor has an anon_uuid cookie and User record."""
        async with AsyncSessionLocal() as session:
            cookie = request.cookies.get("anon_uuid")
            if cookie:
                result = await session.execute(select(User).filter_by(cookie_id=cookie))
                user = result.scalar_one_or_none()
                if not user:
                    user = User(cookie_id=cookie)
                    session.add(user)
                    await session.commit()
            else:
                cookie = str(uuid.uuid4())
                user = User(cookie_id=cookie)
                session.add(user)
                await session.commit()

            request.state.user = user

        response = await call_next(request)

        if "anon_uuid" not in request.cookies:
            response.set_cookie("anon_uuid", cookie, httponly=True)

        return response
