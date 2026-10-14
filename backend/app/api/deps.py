from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import get_settings

limiter = Limiter(key_func=get_remote_address, default_limits=[get_settings().rate_limit_default])


def runner(request: Request):
    return request.app.state.runner


def storage(request: Request):
    return request.app.state.storage
