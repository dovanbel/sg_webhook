from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
import hmac
import hashlib
import os
import sys
import json
import sgtk
import shotgun_api3

from pxr import Usd, Sdf
from pprint import pprint
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from payload_processor import parse_shotgrid_payload


class SgEnvVars(BaseSettings):
    SHOTGUN_SITE: str
    SHOTGUN_WEBHOOK_SCRIPT_USER: str
    SHOTGUN_WEBHOOK_SCRIPT_KEY: SecretStr
    SHOTGUN_WEBHOOK_SECRET: SecretStr
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

sg_env_vars = SgEnvVars()

# shotgun api connection
shotgun = shotgun_api3.Shotgun(
    sg_env_vars.SHOTGUN_SITE,
    sg_env_vars.SHOTGUN_WEBHOOK_SCRIPT_USER,
    sg_env_vars.SHOTGUN_WEBHOOK_SCRIPT_KEY.get_secret_value())
print(shotgun)


def verify_signature(body: bytes, received_signature: str) -> bool:
    """
    Verify ShotGrid webhook HMAC signature (SHA1).
    """
    expected_signature = "sha1=" + hmac.new(
        sg_env_vars.SHOTGUN_WEBHOOK_SECRET.get_secret_value().encode("utf-8"),
        body,
        hashlib.sha1,
    ).hexdigest()

    return hmac.compare_digest(expected_signature, received_signature)


app = FastAPI()

@app.get("/")
def hello():
    return {"message": "ShotGrid webhook receiver is running"}



@app.post("/sg_task_webhook")
async def sg_task_webhook(request: Request, background_tasks: BackgroundTasks):
    # Read raw body FIRST (important!)
    body = await request.body()

    # Get signature header
    signature = request.headers.get("x-sg-signature")
    if not signature:
        raise HTTPException(status_code=401, detail="Missing ShotGrid signature")

    # Verify signature
    if not verify_signature(body, signature):
        raise HTTPException(status_code=401, detail="Invalid ShotGrid signature")

    # At this point: request is authentic ✅
    payload = await request.json()




    # Add the processing task to background (non-blocking!)
    background_tasks.add_task(parse_shotgrid_payload, payload)

    return {"status": "accepted"}






#uv run uvicorn main:app --host 0.0.0.0 --port 9222 --reload