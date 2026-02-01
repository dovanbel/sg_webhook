import hashlib
import hmac

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from payload_processor import parse_shotgrid_payload


class SgEnvVars(BaseSettings):
    SHOTGUN_SITE: str
    SHOTGUN_WEBHOOK_SCRIPT_USER: str
    SHOTGUN_WEBHOOK_SCRIPT_KEY: SecretStr
    SHOTGUN_WEBHOOK_SECRET: SecretStr
    ENVIRONMENT: str
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


sg_env_vars = SgEnvVars()


def verify_signature(body: bytes, received_signature: str) -> bool:
    """
    Verify ShotGrid webhook HMAC signature (SHA1).
    """
    expected_signature = (
        "sha1="
        + hmac.new(
            sg_env_vars.SHOTGUN_WEBHOOK_SECRET.get_secret_value().encode("utf-8"),
            body,
            hashlib.sha1,
        ).hexdigest()
    )

    return hmac.compare_digest(expected_signature, received_signature)


# Disable docs in production (when ENVIRONMENT is set to 'production')
# Enable docs in development/local (when ENVIRONMENT is not set or set to 'development')
environment = sg_env_vars.ENVIRONMENT.lower()
docs_enabled = environment != "production"

app = FastAPI(
    title="ShotGrid Webhook Server",
    docs_url="/docs" if docs_enabled else None,
    redoc_url="/redoc" if docs_enabled else None,
    openapi_url="/openapi.json" if docs_enabled else None,
)


# Health check endpoint
@app.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring.
    Returns basic status without revealing sensitive information.
    """
    return {"status": "healthy"}


# /sg_task_webhook is the endpoint used by the sg webhook that is configured to
# send event for the 'Task' entity
@app.post("/sg_task_webhook")
async def sg_task_webhook(request: Request, background_tasks: BackgroundTasks):
    body = await request.body()

    # Get the signature header
    signature = request.headers.get("x-sg-signature")
    if not signature:
        raise HTTPException(status_code=401, detail="Missing ShotGrid signature")

    # Verify signature
    if not verify_signature(body, signature):
        raise HTTPException(status_code=401, detail="Invalid ShotGrid signature")

    # At this point: request is authentic
    payload = await request.json()

    # Add the processing task to background (non-blocking!)
    background_tasks.add_task(parse_shotgrid_payload, payload)

    return {"status": "accepted"}


# Local testing:  uv run uvicorn main:app --host 0.0.0.0 --port 9222 --reload
