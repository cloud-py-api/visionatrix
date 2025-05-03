import asyncio
import contextlib
import json
import logging
import os
import random
import string
import subprocess
import typing
import xml.etree.ElementTree as ET  # noqa
import zipfile
from base64 import b64encode
from contextvars import ContextVar
from gettext import translation
from io import BytesIO
from pathlib import Path
from time import sleep

import httpx
from fastapi import BackgroundTasks, Body, Depends, FastAPI, Request, responses
from nc_py_api import NextcloudApp
from nc_py_api.ex_app import (
    AppAPIAuthMiddleware,
    nc_app,
    run_app,
    setup_nextcloud_logging,
)
from nc_py_api.ex_app.integration_fastapi import fetch_models_task
from nc_py_api.ex_app.providers.task_processing import TaskProcessingProvider
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import FileResponse, Response
from task_processing_flows import FLOWS_IDS

# ---------Start of configuration values for manual deploy---------
# Uncommenting the following lines may be useful when installing manually.
#
# xml_path = Path(__file__).resolve().parent / "../../appinfo/info.xml"
# os.environ["APP_VERSION"] = ET.parse(xml_path).getroot().find(".//image-tag").text
#
# os.environ["NEXTCLOUD_URL"] = "http://nextcloud.local/index.php"
# os.environ["APP_HOST"] = "0.0.0.0"
# os.environ["APP_PORT"] = "23700"
# os.environ["APP_ID"] = "visionatrix"
# os.environ["APP_SECRET"] = "12345"  # noqa
# os.environ["NC_DEV_SKIP_RUN"] = "1"
# os.environ["HP_SHARED_KEY"] = "1"  # uncomment ONLY for "manual-install" with HaRP
# ---------Enf of configuration values for manual deploy---------

SUPERUSER_NAME = "visionatrix_admin"
SUPERUSER_PASSWORD = "".join(random.choice(string.ascii_letters + string.digits) for i in range(10))  # noqa

SERVICE_URL = os.environ.get("VISIONATRIX_URL", "http://127.0.0.1:8288")

logging.basicConfig(
    level=logging.WARNING,
    format="[%(funcName)s]: %(message)s",
    datefmt="%H:%M:%S",
)
LOGGER = logging.getLogger("visionatrix")
LOGGER.setLevel(logging.DEBUG)

LOCALE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "locale")
current_translator = ContextVar("current_translator")
current_translator.set(translation(os.getenv("APP_ID"), LOCALE_DIR, languages=["en"], fallback=True))

ENABLED_FLAG = NextcloudApp().enabled_state
HARP_ENABLED = bool(os.environ.get("HP_SHARED_KEY"))
INSTALLED_FLOWS = []

PROJECT_ROOT_FOLDER = Path(__file__).parent.parent.parent
STATIC_FRONTEND_FOLDER = PROJECT_ROOT_FOLDER.joinpath("../Visionatrix/visionatrix/client")
STATIC_FRONTEND_FOLDER_HARP = PROJECT_ROOT_FOLDER.joinpath("../Visionatrix/visionatrix/client_harp")
STATIC_FRONTEND_PRESENT = STATIC_FRONTEND_FOLDER.is_dir()
print("[DEBUG]: PROJECT_ROOT_FOLDER=", PROJECT_ROOT_FOLDER, flush=True)
print("[DEBUG]: STATIC_FRONTEND_PRESENT=", STATIC_FRONTEND_PRESENT, flush=True)


def _(text):
    return current_translator.get().gettext(text)


class LocalizationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_lang = request.headers.get("Accept-Language", "en")
        print(f"DEBUG: lang={request_lang}", flush=True)
        translator = translation(os.getenv("APP_ID"), LOCALE_DIR, languages=[request_lang], fallback=True)
        current_translator.set(translator)
        return await call_next(request)


@contextlib.asynccontextmanager
async def lifespan(_app: FastAPI):
    global SUPERUSER_PASSWORD

    SUPERUSER_PASSWORD = os.environ["ADMIN_OVERRIDE"].split(":")[1]
    print(_("Visionatrix"), flush=True)
    setup_nextcloud_logging("visionatrix", logging_level=logging.WARNING)
    _t1 = asyncio.create_task(start_nextcloud_provider_registration())  # noqa
    _t2 = asyncio.create_task(start_nextcloud_tasks_polling())  # noqa
    yield


APP = FastAPI(lifespan=lifespan)
APP.add_middleware(AppAPIAuthMiddleware)  # noqa
# APP.add_middleware(LocalizationMiddleware)


def enabled_handler(enabled: bool, nc: NextcloudApp) -> str:
    global ENABLED_FLAG

    ENABLED_FLAG = enabled
    if enabled:
        LOGGER.info("Hello from %s", nc.app_cfg.app_name)
        if HARP_ENABLED:
            nc.ui.resources.set_script("top_menu", "visionatrix", "ex_app/js_harp/visionatrix-main")
        else:
            nc.ui.resources.set_script("top_menu", "visionatrix", "ex_app/js/visionatrix-main")
        nc.ui.top_menu.register("visionatrix", "Visionatrix", "ex_app/img/app.svg")
    else:
        LOGGER.info("Bye bye from %s", nc.app_cfg.app_name)
        if HARP_ENABLED:
            nc.ui.resources.delete_script("top_menu", "visionatrix", "ex_app/js_harp/visionatrix-main")
        else:
            nc.ui.resources.delete_script("top_menu", "visionatrix", "ex_app/js/visionatrix-main")
        nc.ui.top_menu.unregister("visionatrix")
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


async def proxy_request_to_service(request: Request, path: str, path_prefix: str = ""):
    # Creating a task can take a long time if using local LLM(ollama), so set the timeout to 10 minutes.
    async with httpx.AsyncClient(timeout=600.0) as client:
        url = f"{SERVICE_URL}{path_prefix}{path}" if path.startswith("/") else f"{SERVICE_URL}{path_prefix}/{path}"
        headers = {key: value for key, value in request.headers.items() if key.lower() not in ("host", "cookie")}
        if request.method == "GET":
            response = await client.get(
                url,
                params=request.query_params,
                cookies=request.cookies,
                headers=headers,
            )
        else:
            response = await client.request(
                method=request.method,
                url=url,
                params=request.query_params,
                headers=headers,
                cookies=request.cookies,
                content=await request.body(),
            )
        LOGGER.debug("%s %s/%s -> %s", request.method, path_prefix, path, response.status_code)
        response_header = dict(response.headers)
        response_header.pop("transfer-encoding", None)
        return Response(content=response.content, status_code=response.status_code, headers=response_header)


@APP.post("/webhooks/{nc_task_id}/task-progress")
def get_task_progress(
    nc_task_id: int,
    task_id: int = Body(...),
    progress: float = Body(...),
    execution_time: float = Body(...),
    error: str = Body(...),
):
    nc = NextcloudApp()
    if error:
        nc.providers.task_processing.report_result(nc_task_id, None, error)
        return
    if progress == 100.0:
        with httpx.Client(
            base_url=f"{SERVICE_URL}/vapi",
            auth=httpx.BasicAuth(SUPERUSER_NAME, SUPERUSER_PASSWORD),
        ) as client:
            vix_task = client.get(
                url=f"/tasks/progress/{task_id}",
            )
            vix_task_parsed = json.loads(vix_task.content)
            vix_task_result = client.get(
                url="/tasks/results",
                params={
                    "task_id": task_id,
                    "node_id": vix_task_parsed["outputs"][0]["comfy_node_id"],
                    "batch_index": -1,
                },
            )
            zip_file = zipfile.ZipFile(BytesIO(vix_task_result.content))
            results_ids = []
            for file_name in zip_file.namelist():
                results_ids.append(
                    nc.providers.task_processing.upload_result_file(nc_task_id, zip_file.read(file_name))
                )
            debug_info = nc.providers.task_processing.report_result(nc_task_id, output={"images": results_ids})
            client.delete(url="/tasks/task", params={"task_id": task_id})
    else:
        debug_info = nc.providers.task_processing.set_progress(nc_task_id, progress)
        if not debug_info:
            with httpx.Client(
                base_url=f"{SERVICE_URL}/vapi",
                auth=httpx.BasicAuth(SUPERUSER_NAME, SUPERUSER_PASSWORD),
            ) as client:
                client.delete(
                    url="/tasks/task",
                    params={"task_id": task_id},
                )
    LOGGER.debug(
        "Updating task progress in NC with:\n"
        "NcTaskID=%s, task_id=%s, progress=%s, execution_time=%s, error='%s'\n"
        "Reply from nc: %s",
        nc_task_id,
        task_id,
        progress,
        execution_time,
        error,
        debug_info,
    )


@APP.api_route(
    "/vapi/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH", "TRACE"],
)
async def proxy_backend_requests(request: Request, path: str):
    LOGGER.debug("%s %s\nCookies: %s", request.method, path, request.cookies)
    return await proxy_request_to_service(request, path, "/vapi")


@APP.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH", "TRACE"])
async def proxy_frontend_requests(request: Request, path: str):
    LOGGER.debug("%s %s\nCookies: %s", request.method, path, request.cookies)
    file_server_path = ""
    if path.startswith("ex_app"):
        file_server_path = PROJECT_ROOT_FOLDER.joinpath(path)
    elif STATIC_FRONTEND_PRESENT:
        if HARP_ENABLED:
            if not path:
                file_server_path = STATIC_FRONTEND_FOLDER_HARP.joinpath("index.html")
            elif STATIC_FRONTEND_FOLDER_HARP.joinpath(path).is_file():
                file_server_path = STATIC_FRONTEND_FOLDER_HARP.joinpath(path)
        else:
            if not path:
                file_server_path = STATIC_FRONTEND_FOLDER.joinpath("index.html")
            elif STATIC_FRONTEND_FOLDER.joinpath(path).is_file():
                file_server_path = STATIC_FRONTEND_FOLDER.joinpath(path)

    if file_server_path:
        LOGGER.debug("proxy_FRONTEND_requests: <OK> Returning: %s", file_server_path)
        response = FileResponse(str(file_server_path))
    else:
        if STATIC_FRONTEND_PRESENT:
            LOGGER.debug("proxy_FRONTEND_requests: <LOCAL FILE MISSING> Routing(%s) to the service", path)
        response = await proxy_request_to_service(request, path)
    response.headers["content-security-policy"] = "default-src * 'unsafe-inline' 'unsafe-eval' data: blob:;"
    return response


def background_tasks_polling():
    global ENABLED_FLAG

    basic_auth = httpx.BasicAuth(SUPERUSER_NAME, SUPERUSER_PASSWORD)
    nc = NextcloudApp()
    headers = {
        "aa-version": "4.0.0",
        "ex-app-version": os.environ["APP_VERSION"],
        "ex-app-id": os.environ["APP_ID"],
        "authorization-app-api": b64encode(f":{os.environ['APP_SECRET']}".encode()).decode(),
    }
    if HARP_ENABLED:
        headers["x-transport-uds"] = "/tmp/exapp.sock"  # noqa
    ip_address = "127.0.0.1" if os.environ["APP_HOST"] == "0.0.0.0" else os.environ["APP_HOST"]  # noqa
    webhook_url = f"http://{ip_address}:{os.environ['APP_PORT']}/webhooks"  # noqa
    webhook_headers = json.dumps(headers)
    while True:
        while ENABLED_FLAG:
            try:
                if not poll_tasks(nc, basic_auth, webhook_url, webhook_headers):
                    sleep(1)
            except Exception:  # noqa
                LOGGER.exception("Exception occurred", stack_info=True)
                sleep(10)
        sleep(30)
        ENABLED_FLAG = nc.enabled_state


def poll_tasks(nc: NextcloudApp, basic_auth: httpx.BasicAuth, webhook_url: str, webhook_headers: str) -> bool:
    reply_from_nc = nc.providers.task_processing.next_task([f"v_{i}" for i in INSTALLED_FLOWS], ["core:text2image"])
    if not reply_from_nc:
        return False
    task_info = reply_from_nc["task"]
    data = {
        "prompt": task_info["input"]["input"],
        "batch_size": min(task_info["input"]["numberOfImages"], 4),
        "webhook_url": webhook_url + f"/{task_info['id']}",
        "webhook_headers": webhook_headers,
    }
    flow_name = reply_from_nc["provider"]["name"].removeprefix("v_")
    if flow_name in ("flux1_dev", "flux1_schnell"):
        data["diffusion_precision"] = "fp8_e4m3fn"
    with httpx.Client(base_url=f"{SERVICE_URL}/vapi") as client:
        vix_task = client.put(
            url=f"/tasks/create/{flow_name}",
            auth=basic_auth,
            data=data,
        )
        LOGGER.debug("task passed to visionatrix, return code: %s", vix_task.status_code)
    return True


async def start_nextcloud_tasks_polling():
    await asyncio.to_thread(background_tasks_polling)


def background_provider_registration():
    global ENABLED_FLAG

    basic_auth = httpx.BasicAuth(SUPERUSER_NAME, SUPERUSER_PASSWORD)
    nc = NextcloudApp()

    while True:
        while ENABLED_FLAG:
            try:
                sync_providers(nc, basic_auth)
                sleep(30)
            except Exception:  # noqa
                LOGGER.exception("Exception occurred", stack_info=True)
                sleep(60)
        sleep(60)
        ENABLED_FLAG = nc.enabled_state


def sync_providers(nc: NextcloudApp, basic_auth: httpx.BasicAuth) -> None:
    global INSTALLED_FLOWS

    with httpx.Client(base_url=f"{SERVICE_URL}/vapi") as client:
        r = client.get(
            url="/flows/installed",
            auth=basic_auth,
        )
    vix_flows = json.loads(r.content)
    name_to_display_name = {item["name"]: item["display_name"] for item in vix_flows}
    new_flows = set([i["name"] for i in vix_flows if i["name"] in FLOWS_IDS])  # noqa
    providers_to_install = list(new_flows - set(INSTALLED_FLOWS))
    providers_to_delete = list(set(INSTALLED_FLOWS) - new_flows)
    for i in providers_to_install:
        provider_info = TaskProcessingProvider(
            id=f"v_{i}", name=f"Visionatrix: {name_to_display_name[i]}", task_type="core:text2image"  # noqa
        )
        nc.providers.task_processing.register(provider_info)
    for i in providers_to_delete:
        nc.providers.task_processing.unregister(name=f"v_{i}")
    INSTALLED_FLOWS = list(new_flows)


async def start_nextcloud_provider_registration():
    await asyncio.to_thread(background_provider_registration)


def start_visionatrix() -> None:
    if os.environ.get("NC_DEV_SKIP_RUN") != "1":
        visionatrix_python = "/Visionatrix/venv/bin/python"
        if os.environ.get("DISABLE_WORKER") != "1":
            # Run server in background and redirect output to server.log
            server_log = open("server.log", "wb")
            ui_path = "--ui=visionatrix/client_harp" if HARP_ENABLED else "--ui"
            subprocess.Popen(
                [visionatrix_python, "-m", "visionatrix", "run", "--mode=SERVER", ui_path],
                stdout=server_log,
                stderr=subprocess.STDOUT,
            )
            print("[DEBUG]: Launched Visionatrix server in background", flush=True)
            # Wait a bit to let the server start up
            sleep(15)
            # Run worker in background and redirect output to worker.log
            worker_log = open("worker.log", "wb")
            subprocess.Popen(
                [visionatrix_python, "-m", "visionatrix", "run", "--mode=WORKER", "--disable-smart-memory"],
                stdout=worker_log,
                stderr=subprocess.STDOUT,
            )
            print("[DEBUG]: Launched Visionatrix worker in background", flush=True)
        else:
            # Only run server when worker is disabled
            server_log = open("server.log", "wb")
            subprocess.Popen(
                [visionatrix_python, "-m", "visionatrix", "run", "--mode=SERVER"],
                stdout=server_log,
                stderr=subprocess.STDOUT,
            )
            print("[DEBUG]: Launched Visionatrix server (worker disabled)", flush=True)

    while True:  # Let's wait until Visionatrix opens the port.
        with contextlib.suppress(httpx.ReadError, httpx.ConnectError, httpx.RemoteProtocolError):
            r = httpx.get(SERVICE_URL + "/vapi/other/whoami")
            if r.status_code in (200, 204, 401, 403):
                break
            sleep(5)


if __name__ == "__main__":
    os.environ["ADMIN_OVERRIDE"] = f"{SUPERUSER_NAME}:{SUPERUSER_PASSWORD}"
    start_visionatrix()
    os.chdir(Path(__file__).parent)
    run_app("main:APP", log_level="trace")
