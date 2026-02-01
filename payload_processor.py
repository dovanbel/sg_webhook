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

        # pprint(payload)

        payload_data = payload.get("data", {})

        # Extract common webhook fields
        event_type = payload_data.get("event_type")
        entity_type = payload_data.get("entity", {}).get("type")
        entity_id = payload_data.get("entity", {}).get("id")
        project_id = payload_data.get("project", {}).get("id")

        logger.info(
            f"Event: {event_type} | Entity: {entity_type} (id: {entity_id}) | Project id: {project_id}"
        )


        if entity_type == "Task" and project_id and entity_id:
            await process_task(project_id, entity_id)


        # logger.info("✅ Payload processing complete")

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
    # Bootstrap the tk-shell engine
    engine = mgr.bootstrap_engine("tk-shell", entity={"type": entity.get("type"), "id": entity.get("id")}) 

    usdfw = engine.frameworks.get("tk-framework-dubrolusd")
    if not usdfw:
        logger.info(f"Could not find a 'tk-framework-dubrolusd' in the frameworks of engine: {engine} ")
        engine.destroy()
        return

    context = engine.sgtk.context_from_entity(entity.get("type"), entity.get("id"))
    logger.info(f"Context: {context.to_dict()}")


    rlmod = usdfw.import_module("rootlayer_manager")
    rlman = rlmod.RootLayerManager(usdfw, context)

    usd_master_path = rlman.get_latest_usdmaster_from_context()

    if not usd_master_path:
        logger.info(f"No usd master file found for entity: {context.entity}, will create and publish one")
        rlman.create_entity_usdmaster()
    elif not rlman.validate_entity_usdmaster(usd_master_path):
        logger.info(f"Usd master file: {usd_master_path} found for entity: {context.entity}. "
                    "However, it is not correct, will create and publish a new version")
        rlman.create_entity_usdmaster()
    else:
        logger.info(f"Found usd master file: {usd_master_path} for entity {context.entity}. It is correct, nothing to do")

    # Important : destroy the engine
    engine.destroy()



