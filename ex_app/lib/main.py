import os
import typing
from pathlib import Path
from contextlib import asynccontextmanager

import httpx
from starlette.responses import Response, FileResponse
from fastapi import FastAPI, responses, Request, Depends, BackgroundTasks
from starlette.middleware.base import BaseHTTPMiddleware

from nc_py_api import NextcloudApp
from nc_py_api.ex_app import (
    run_app,
    set_handlers,
    AppAPIAuthMiddleware,
    nc_app,
)
from nc_py_api.ex_app.integration_fastapi import fetch_models_task
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
async def lifespan(_app: FastAPI):
    print(_("Vix"))
    yield


APP = FastAPI(lifespan=lifespan)
# APP.add_middleware(AppAPIAuthMiddleware)
# APP.add_middleware(LocalizationMiddleware)


def enabled_handler(enabled: bool, nc: NextcloudApp) -> str:
    print(f"enabled={enabled}")
    if enabled:
        nc.ui.resources.set_script("top_menu", "vix_service", "ex_app/js/vix-main")
        nc.ui.top_menu.register("vix_service", "Visionatrix", "ex_app/img/app.svg")
    else:
        nc.ui.resources.delete_script("top_menu", "vix_service", "ex_app/js/vix-main")
        nc.ui.top_menu.unregister("vix_service")
    return ""


@APP.get("/heartbeat")
async def heartbeat_callback():
    return responses.JSONResponse(content={"status": "ok"})


@APP.post("/init")
async def init_callback(b_tasks: BackgroundTasks, nc: typing.Annotated[NextcloudApp, Depends(nc_app)]):
    b_tasks.add_task(fetch_models_task, nc, {}, 0)
    return responses.JSONResponse(content={})


@APP.put("/enabled")
def enabled_callback(enabled: bool, nc: typing.Annotated[NextcloudApp, Depends(nc_app)]):
    return responses.JSONResponse(content={"error": enabled_handler(enabled, nc)})


@APP.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH", "TRACE"])
async def proxy_requests(request: Request, path: str):
    print(f"proxy_requests: {path} - {request.method}\nCookies: {request.cookies}", flush=True)
    if path.startswith("ex_app"):
        file_server_path = Path("/" + path)
    elif not path:
        file_server_path = Path("/Visionatrix/visionatrix/client/index.html")
    else:
        file_server_path = Path("/Visionatrix/visionatrix/client/" + path)
    if file_server_path.exists():
        media_type = None
        if str(file_server_path).endswith(".js"):
            media_type = "application/javascript"
        response = FileResponse(str(file_server_path), media_type=media_type)
        response.headers["content-security-policy"] = "default-src * 'unsafe-inline' 'unsafe-eval' data: blob:;"
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["X-Permitted-Cross-Domain-Policies"] = "all"
        print("proxy_FRONTEND_requests: <OK> Returning: ", str(file_server_path), flush=True)
        return response

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
    os.chdir(Path(__file__).parent)
    run_app("main:APP", log_level="trace")
