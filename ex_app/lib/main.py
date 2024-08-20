import asyncio
import contextlib
import json
import os
import random
import string
import subprocess
import typing
import zipfile
from base64 import b64encode
from contextvars import ContextVar
from gettext import translation
from io import BytesIO
from pathlib import Path
from time import sleep

import httpx
from fastapi import BackgroundTasks, Body, Depends, FastAPI, Request, responses, status
from nc_py_api import NextcloudApp
from nc_py_api.ex_app import AppAPIAuthMiddleware, nc_app, persistent_storage, run_app
from nc_py_api.ex_app.integration_fastapi import fetch_models_task
from nc_py_api.ex_app.providers.task_processing import TaskProcessingProvider
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import FileResponse, Response
from supported_flows import FLOWS_IDS

LOCALE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "locale")
current_translator = ContextVar("current_translator")
current_translator.set(translation(os.getenv("APP_ID"), LOCALE_DIR, languages=["en"], fallback=True))

ENABLED_FLAG = NextcloudApp().enabled_state
SUPERUSER_PASSWORD_PATH = Path(persistent_storage()).joinpath("superuser.txt")
SUPERUSER_NAME = "visionatrix_admin"
SUPERUSER_PASSWORD: str = ""
# print(str(SUPERUSER_PASSWORD_PATH), flush=True)  # for development only
INSTALLED_FLOWS = []


def _(text):
    return current_translator.get().gettext(text)


class LocalizationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_lang = request.headers.get("Accept-Language", "en")
        print(f"DEBUG: lang={request_lang}")
        translator = translation(os.getenv("APP_ID"), LOCALE_DIR, languages=[request_lang], fallback=True)
        current_translator.set(translator)
        return await call_next(request)


@contextlib.asynccontextmanager
async def lifespan(_app: FastAPI):
    global SUPERUSER_PASSWORD

    print(_("Visionatrix"))
    SUPERUSER_PASSWORD = Path(SUPERUSER_PASSWORD_PATH).read_text()
    _t1 = asyncio.create_task(start_nextcloud_provider_registration())  # noqa
    _t2 = asyncio.create_task(start_nextcloud_tasks_polling())  # noqa
    yield


APP = FastAPI(lifespan=lifespan)
APP.add_middleware(AppAPIAuthMiddleware)  # noqa
# APP.add_middleware(LocalizationMiddleware)


def enabled_handler(enabled: bool, nc: NextcloudApp) -> str:
    global ENABLED_FLAG

    print(f"enabled={enabled}")
    ENABLED_FLAG = enabled
    if enabled:
        nc.ui.resources.set_script("top_menu", "visionatrix", "ex_app/js/visionatrix-main")
        nc.ui.top_menu.register("visionatrix", "Visionatrix", "ex_app/img/app.svg")
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
        # to-do: here if task is not found on the NC side we should cancel it in the Visionatrix
        return
    if progress == 100.0:
        with httpx.Client(
            base_url="http://127.0.0.1:8288/api",
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
    print("[DEBUG]: get_task_progress:")
    print(debug_info)
    print(nc_task_id, " ", task_id, " ", progress, " ", execution_time, " ", error)


@APP.api_route(
    "/api/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH", "TRACE"],
)
async def proxy_backend_requests(request: Request, path: str):
    # print(f"proxy_BACKEND_requests: {path} - {request.method}\nCookies: {request.cookies}", flush=True)
    async with httpx.AsyncClient() as client:
        url = f"http://127.0.0.1:8288/api/{path}"
        headers = {key: value for key, value in request.headers.items() if key.lower() not in ("host", "cookie")}
        # print(f"proxy_BACKEND_requests: method={request.method}, path={path}, status={response.status_code}")
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
        # print(
        #     f"proxy_BACKEND_requests: method={request.method}, path={path}, status={response.status_code}", flush=True
        # )
        response_header = dict(response.headers)
        response_header.pop("transfer-encoding", None)
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=response_header,
        )


@APP.api_route(
    "/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH", "TRACE"],
)
async def proxy_requests(_request: Request, path: str):
    # print(
    #     f"proxy_requests: {path} - {_request.method}\nCookies: {_request.cookies}",
    #     flush=True,
    # )
    if path.startswith("ex_app"):
        file_server_path = Path("../../" + path)
    elif not path:
        file_server_path = Path("../../Visionatrix/visionatrix/client/index.html")
    else:
        file_server_path = Path("../../Visionatrix/visionatrix/client/" + path)
    if not file_server_path.exists():
        return Response(status_code=status.HTTP_404_NOT_FOUND)
    response = FileResponse(str(file_server_path))
    response.headers["content-security-policy"] = "default-src * 'unsafe-inline' 'unsafe-eval' data: blob:;"
    # print("proxy_FRONTEND_requests: <OK> Returning: ", str(file_server_path), flush=True)
    return response


def background_tasks_polling():
    global ENABLED_FLAG

    basic_auth = httpx.BasicAuth(SUPERUSER_NAME, SUPERUSER_PASSWORD)
    nc = NextcloudApp()
    ip_address = "127.0.0.1" if os.environ["APP_HOST"] == "0.0.0.0" else os.environ["APP_HOST"]  # noqa
    webhook_url = f"http://{ip_address}:{os.environ['APP_PORT']}/webhooks"  # noqa
    webhook_headers = json.dumps(
        {
            "AA-VERSION": "3.1.0",
            "EX-APP-VERSION": os.environ["APP_VERSION"],
            "EX-APP-ID": os.environ["APP_ID"],
            "AUTHORIZATION-APP-API": b64encode(f":{os.environ['APP_SECRET']}".encode()).decode(),
        }
    )
    while True:
        while ENABLED_FLAG:
            try:
                if not poll_tasks(nc, basic_auth, webhook_url, webhook_headers):
                    sleep(1)
            except Exception as e:
                print(f"poll_tasks: Exception occurred! Info: {e}")
                sleep(10)
        sleep(30)
        ENABLED_FLAG = nc.enabled_state


def poll_tasks(nc: NextcloudApp, basic_auth: httpx.BasicAuth, webhook_url: str, webhook_headers: str) -> bool:
    reply_from_nc = nc.providers.task_processing.next_task([f"v_{i}" for i in INSTALLED_FLOWS], ["core:text2image"])
    if not reply_from_nc:
        return False
    task_info = reply_from_nc["task"]
    with httpx.Client(base_url="http://127.0.0.1:8288/api") as client:
        vix_task = client.put(
            url="/tasks/create",
            auth=basic_auth,
            data={
                "name": reply_from_nc["provider"]["name"].removeprefix("v_"),
                "input_params": json.dumps(
                    {
                        "prompt": task_info["input"]["input"],
                        "batch_size": min(task_info["input"]["numberOfImages"], 4),
                    }
                ),
                "webhook_url": webhook_url + f"/{task_info['id']}",
                "webhook_headers": webhook_headers,
            },
        )
        print("task passed to visionatrix, return code: ", vix_task.status_code, flush=True)
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
            except Exception as e:
                print(f"sync_providers: Exception occurred! Info: {e}")
                sleep(60)
        sleep(60)
        ENABLED_FLAG = nc.enabled_state


def sync_providers(nc: NextcloudApp, basic_auth: httpx.BasicAuth) -> None:
    global INSTALLED_FLOWS

    with httpx.Client(base_url="http://127.0.0.1:8288/api") as client:
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


def generate_random_string(length=10):
    letters = string.ascii_letters + string.digits  # You can include other characters if needed
    return "".join(random.choice(letters) for i in range(length))  # noqa


def venv_run(command: str) -> None:
    command = f". /Visionatrix/venv/bin/activate && {command}"
    try:
        print(f"executing(pwf={os.getcwd()}): {command}")
        subprocess.check_call(command, shell=True)
    except subprocess.CalledProcessError as e:
        print("An error occurred while executing command in venv:", str(e))
        raise


def initialize_visionatrix() -> None:
    while True:  # Let's wait until Visionatrix opens the port.
        with contextlib.suppress(httpx.ReadError, httpx.ConnectError, httpx.RemoteProtocolError):
            r = httpx.get("http://127.0.0.1:8288")
            if r.status_code in (200, 204, 401, 403):
                break
            sleep(5)
    if not SUPERUSER_PASSWORD_PATH.exists():
        password = generate_random_string()
        # password = "12345"  # uncomment this line and comment next for the developing with local Visionatrix version.
        venv_run(f"python3 -m visionatrix create-user --name {SUPERUSER_NAME} --password {password}")
        Path(SUPERUSER_PASSWORD_PATH).write_text(password)


if __name__ == "__main__":
    initialize_visionatrix()
    os.chdir(Path(__file__).parent)
    run_app("main:APP", log_level="trace")
