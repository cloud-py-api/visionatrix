import os
from contextlib import asynccontextmanager

import httpx
from starlette.responses import Response
from fastapi import FastAPI, responses, Request
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel

from nc_py_api import NextcloudApp
from nc_py_api.ex_app import (
    run_app,
    set_handlers,
    AppAPIAuthMiddleware,
)
from contextvars import ContextVar

from gettext import translation

LOCALE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "locale")
current_translator = ContextVar("current_translator")
current_translator.set(translation(os.getenv("APP_ID"), LOCALE_DIR, languages=["en"], fallback=True))


def _(text):
    return current_translator.get().gettext(text)


class LocalizationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_lang = request.headers.get('Accept-Language', 'en')
        print(f"DEBUG: lang={request_lang}")
        translator = translation(
            os.getenv("APP_ID"), LOCALE_DIR, languages=[request_lang], fallback=True
        )
        current_translator.set(translator)
        response = await call_next(request)
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    set_handlers(app, enabled_handler)
    print(_("Vix"))
    yield


APP = FastAPI(lifespan=lifespan)
APP.add_middleware(AppAPIAuthMiddleware)
APP.add_middleware(LocalizationMiddleware)


def enabled_handler(enabled: bool, nc: NextcloudApp) -> str:
    print(f"enabled={enabled}")
    if enabled:
        nc.ui.resources.set_script("top_menu", "vix_service", "js/vix-main")
        nc.ui.top_menu.register("vix_service", "Visionatrix", "img/app.svg")
        nc.occ_commands.register("vix:ping", "/occ_ping")
        nc.occ_commands.register("vix:service:start", "/occ_service_start")
        nc.occ_commands.register("vix:service:stop", "/occ_service_stop")
        nc.occ_commands.register("vix:service:restart", "/occ_service_restart")
        nc.occ_commands.register("vix:service:status", "/occ_service_restart")
    else:
        nc.ui.resources.delete_script("top_menu", "vix_service", "js/vix-main")
        nc.ui.top_menu.unregister("vix_service")
        nc.occ_commands.unregister("vix:ping")
        nc.occ_commands.unregister("vix:service:start")
        nc.occ_commands.unregister("vix:service:stop")
        nc.occ_commands.unregister("vix:service:restart")
        nc.occ_commands.unregister("vix:service:status")
    return ""


class OccPayload(BaseModel):
    arguments: dict | None = None
    options: dict | None = None


class OccData(BaseModel):
    occ: OccPayload


@APP.post("/occ_ping")
async def occ_ping():
    return responses.Response(content="<info>PONG</info>\n")


@APP.post("/occ_service_start")
async def occ_service_start(data: OccData):
    # TODO: implement systemctl call to start service
    return responses.Response(content="<info>Service started</info>\n")


@APP.post("/occ_service_stop")
async def occ_service_stop(data: OccData):
    # TODO: implement systemctl call to stop service
    return responses.Response(content="<info>Service stopped</info>\n")


@APP.post("/occ_service_restart")
async def occ_service_restart(data: OccData):
    # TODO: implement systemctl call to restart service
    return responses.Response(content="<info>Service restarted</info>\n")


@APP.post("/occ_service_status")
async def occ_service_status(data: OccData):
    # TODO: implement systemctl call to get service status
    return responses.Response(content="<info>Service status</info>\n")


@APP.api_route("/iframe/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH", "TRACE"])
async def proxy_requests(request: Request, path: str):
    async with httpx.AsyncClient() as client:
        url = f"http://127.0.0.1:8288/{path}"
        headers = {key: value for key, value in request.headers.items() if key.lower() != 'host'}
        response = await client.request(
            method=request.method,
            url=url,
            params=request.query_params,
            headers=headers,
            cookies=request.cookies,
            content=await request.body()
        )
        print(f"method={request.method}, path={path}, status={response.status_code}")
        response.headers["content-security-policy"] = "frame-ancestors 'self'"
        return Response(content=response.content, status_code=response.status_code, headers=dict(response.headers))


if __name__ == "__main__":
    run_app("main:APP", log_level="trace")
