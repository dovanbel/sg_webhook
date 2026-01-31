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



async def process_task(project_id: int, task_id: int):
    filters = [
        ["id", "is", task_id],
        ["project", "is", {"id": project_id, "type": "Project"}],
    ]
    fields = ["entity"]

    tasks = shotgun.find(
        "Task",
        filters=filters,
        fields=fields,
    )

    if not tasks:
        logger.info(f"No task found with id {task_id} in project with id {project_id}")
        return

    if len(tasks) > 1:
        logger.info("Multiple results, should never happen")
        return

    entity = tasks[0].get("entity", {})

    if not entity:
        logger.info(f"No entity linked to task with id {task_id}")
        return

    logger.info(f"Entity linked to current task is: {entity}")

    #### Now we can bootstrap


    #Authenticate using a pre-defined script user.
    sa = sgtk.authentication.ShotgunAuthenticator()

    user = sa.create_script_user(
        api_script=sg_env_vars.SHOTGUN_WEBHOOK_SCRIPT_USER,
        api_key=sg_env_vars.SHOTGUN_WEBHOOK_SCRIPT_KEY.get_secret_value(),
        host=sg_env_vars.SHOTGUN_SITE
    )
    sgtk.set_authenticated_user(user)

    mgr = sgtk.bootstrap.ToolkitManager(user)
    mgr.base_configuration = "sgtk:descriptor:app_store?name=tk-config-basic"
    mgr.plugin_id = "basic.*"
    mgr.pipeline_configuration = "Primary"
    mgr.pre_engine_start_callback = lambda ctx: ctx.sgtk.synchronize_filesystem_structure()
    engine = mgr.bootstrap_engine("tk-shell", entity={"type": entity.get("type"), "id": entity.get("id")}) 

    logger.info(f"Engine used: {engine}")


    context = engine.sgtk.context_from_entity(entity.get("type"), entity.get("id"))
    logger.info(f"Context: {context.to_dict()}")

    # Important : destroy the engine
    engine.destroy()

    # framework = engine.sgtk.load_framework("tk-framework-dubrolusd")
    # fw = sgtk.platform.get_framework("tk-framework-dubrolusd")
    # logger.info(f"Framework: {fw}")




    # fw = xxxxxxxxxxx.frameworks["tk-framework-dubrolusd"]

    # rlmod = fw.import_module("rootlayer_manager")

    # # Use the init time of the app to check if a usd master file exists for the current entity
    # # TODO : I should create the usd master as soon as the entity is created in Shotgrid...
    # rlman = rlmod.RootLayerManager(fw, context)

    # usd_master_path = rlman.get_latest_usdmaster_from_context()

    # if not usd_master_path:
    #     rlman.create_entity_usdmaster()
    # else:
    #     if not rlman.validate_entity_usdmaster(usd_master_path):
    #         rlman.create_entity_usdmaster()