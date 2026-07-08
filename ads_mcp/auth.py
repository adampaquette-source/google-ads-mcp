"""Service account credential loading for local (file) and hosted (inline env) environments."""

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from google.oauth2 import service_account

load_dotenv()

_SCOPES = ["https://www.googleapis.com/auth/adwords"]


def get_credentials() -> service_account.Credentials:
    # Hosted mode: the key JSON is pasted into a platform secret variable —
    # no key file ever enters the image or the build context.
    inline = os.getenv("GOOGLE_ADS_SERVICE_ACCOUNT_JSON")
    if inline:
        return service_account.Credentials.from_service_account_info(
            json.loads(inline), scopes=_SCOPES
        )

    env = os.getenv("ADS_MCP_ENV", "local")

    if env == "local":
        return _credentials_from_file()
    elif env == "cloud":
        return _credentials_from_secret_manager()
    else:
        raise ValueError(f"Unknown ADS_MCP_ENV value: {env!r}. Expected 'local' or 'cloud'.")


def _credentials_from_file() -> service_account.Credentials:
    key_path_str = os.getenv("GOOGLE_ADS_SERVICE_ACCOUNT_JSON_PATH")
    if not key_path_str:
        raise EnvironmentError(
            "GOOGLE_ADS_SERVICE_ACCOUNT_JSON_PATH is not set in .env. "
            "Point it at the service account JSON key file."
        )

    key_path = Path(key_path_str)
    if not key_path.exists():
        raise FileNotFoundError(
            f"Service account key file not found at {key_path.resolve()}. "
            "Check GOOGLE_ADS_SERVICE_ACCOUNT_JSON_PATH in .env."
        )

    return service_account.Credentials.from_service_account_file(
        str(key_path), scopes=_SCOPES
    )


def _credentials_from_secret_manager() -> service_account.Credentials:
    raise NotImplementedError(
        "Secret Manager credential loading is not implemented yet (Phase 2). "
        "Set ADS_MCP_ENV=local for local development."
    )
