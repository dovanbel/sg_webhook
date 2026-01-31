from fastapi import FastAPI, Request, HTTPException
import hmac
import hashlib
from redis import Redis
# from rq import Queue
import os
import sys
import json
import sgtk
import shotgun_api3

from pxr import Usd, Sdf
from pprint import pprint
from pydantic import HttpUrl, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class SgEnvVars(BaseSettings):
    SHOTGUN_SITE: str
    SHOTGUN_WEBHOOK_SCRIPT_USER: str
    # Use SecretStr to prevent keys from being printed in plain text in logs
    SHOTGUN_WEBHOOK_SCRIPT_KEY: SecretStr
    SHOTGUN_WEBHOOK_SECRET: SecretStr
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

sg_env_vars = SgEnvVars()



def main():
    print("Hello from sg-webhook!")
    print(sys.executable)

    # shotgun api connection
    shotgun = shotgun_api3.Shotgun(
        sg_env_vars.SHOTGUN_SITE,
        sg_env_vars.SHOTGUN_WEBHOOK_SCRIPT_USER,
        sg_env_vars.SHOTGUN_WEBHOOK_SCRIPT_KEY.get_secret_value())
    print(shotgun)




if __name__ == "__main__":
    main()
