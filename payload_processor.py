"""
Background task processor for ShotGrid webhook payloads.
This module handles payload parsing without blocking the FastAPI server.
"""

import asyncio
from typing import Dict, Any
import logging

from pprint import pprint
import sgtk
import shotgun_api3

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
    sg_env_vars.SHOTGUN_WEBHOOK_SCRIPT_KEY.get_secret_value(),
)



async def parse_shotgrid_payload(payload: Dict[str, Any]) -> None:
    """
    Parse and process ShotGrid webhook payload.
    This runs in the background and won't block the webhook endpoint.

    Args:
        payload: The webhook payload from ShotGrid
    """
    try:
        logger.info("Starting payload processing...")

        pprint(payload)

        payload_data = payload.get("data", {})

        # Extract common webhook fields
        event_type = payload_data.get("event_type")
        entity_type = payload_data.get("entity", {}).get("type")
        entity_id = payload_data.get("entity", {}).get("id")
        project_id = payload_data.get("project", {}).get("id")

        logger.info(
            f"Event: {event_type} | Entity: {entity_type} (id: {entity_id}) | Project id: {project_id}"
        )

        # Extract meta information
        # meta = payload.get("meta", {})
        # attribute_name = meta.get("attribute_name")
        # old_value = meta.get("old_value")
        # new_value = meta.get("new_value")

        # Simulate processing that takes time
        # Replace this with your actual business logic
        # await asyncio.sleep(1)  # Simulating work

        if entity_type == "Task" and project_id and entity_id:
            await process_task(project_id, entity_id)

        # Example: Process based on event type
        # if event_type == "Shotgun_Task_Change":
        #     await process_task_change(payload, attribute_name, old_value, new_value)
        # elif event_type == "Shotgun_Task_New":
        #     await process_new_task(payload)
        # else:
        #     logger.info(f"Unhandled event type: {event_type}")

        logger.info("✅ Payload processing complete")

    except Exception as e:
        logger.error(f"❌ Error processing payload: {e}", exc_info=True)


async def process_task_change(
    payload: Dict[str, Any], attribute_name: str, old_value: Any, new_value: Any
) -> None:
    """Handle Task change events."""
    logger.info(f"Processing task change: {attribute_name}")
    logger.info(f"  Old: {old_value} → New: {new_value}")

    # Add your task change logic here
    # For example:
    # - Update USD files
    # - Trigger toolkit actions
    # - Send notifications
    await asyncio.sleep(5)  # Simulate heavy processing


async def process_new_task(payload: Dict[str, Any]) -> None:
    """Handle new Task creation events."""
    logger.info("Processing new task creation")

    # Add your new task logic here
    await asyncio.sleep(3)  # Simulate heavy processing


async def process_task(project_id: int, entity_id: int):

    filters = [
        ["entity", "is", {"id": entity_id, "type": "Task"}],
        ["project", "is", {"id": project_id, "type": "Project"}],
    ]
    fields = ["path", "version_number"]


    tttask = shotgun.find(
        "Task",
        filters=filters,
        fields=fields,
    )

    logger.info(f"Youpirrr {tttask}")
