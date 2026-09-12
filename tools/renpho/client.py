"""Renpho Cloud API Client for fetching measurements."""

import os
import requests
from pathlib import Path
from .constants import (
    API_BASE_URL,
    APP_VERSION,
    BODY_WEIGHT_SCALES,
    ENDPOINTS,
    MEASUREMENT_TABLE_NAMES,
    PLATFORM,
)
from .crypto import (
    decrypt_response,
    encrypt_empty_bytes,
    encrypt_empty_object,
    encrypt_request,
)


class RenphoAPIError(Exception):
    """Raised when Renpho API returns an error."""
    pass


def load_env_credentials():
    """Load credentials from ~/.config/renpho/credentials.env."""
    env_path = Path.home() / ".config" / "renpho" / "credentials.env"
    creds = {}
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                creds[k.strip()] = v.strip()
    return creds.get("RENPHO_EMAIL"), creds.get("RENPHO_PASSWORD")


class RenphoClient:
    """Client for Renpho cloud API authentication and data sync."""

    def __init__(self, email: str = None, password: str = None):
        if not email or not password:
            loaded_email, loaded_password = load_env_credentials()
            email = email or loaded_email
            password = password or loaded_password
        if not email or not password:
            raise ValueError("Renpho credentials missing.")
        self.email = email
        self.password = password
        self.token = None
        self.user_id = None
        self.user_info = None
        self._session = requests.Session()

    def _post(self, endpoint: str, body: dict, auth: bool = True) -> dict:
        url = f"{API_BASE_URL}/{endpoint}"
        headers = {}
        if auth and self.token:
            headers.update({
                "token": self.token,
                "userId": str(self.user_id),
                "appVersion": APP_VERSION,
                "platform": PLATFORM,
            })
        resp = self._session.post(url, json=body, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") not in (100, 101) and data.get("msg", "").lower() != "success":
            raise RenphoAPIError(f"API {endpoint} failed: {data}")
        return data

    def login(self) -> dict:
        """Authenticate with Renpho and retrieve session token."""
        payload = {
            "questionnaire": {},
            "login": {
                "password": self.password,
                "areaCode": "US",
                "appRevision": APP_VERSION,
                "cellphoneType": "PythonScript",
                "systemType": "11",
                "email": self.email,
                "platform": PLATFORM,
            },
            "bindingList": {"deviceTypes": BODY_WEIGHT_SCALES},
        }
        res = self._post(ENDPOINTS["login"], encrypt_request(payload), auth=False)
        user_data = decrypt_response(res["data"])
        login_info = user_data.get("login", {})
        self.token = login_info.get("token")
        self.user_id = login_info.get("id")
        self.user_info = login_info
        if not self.token:
            raise RenphoAPIError("No token in login response")
        return user_data

    def get_device_info(self) -> dict:
        """Retrieve device info and scale shards."""
        for body_fn in (encrypt_empty_bytes, encrypt_empty_object):
            try:
                res = self._post(ENDPOINTS["device_info"], body_fn())
                return decrypt_response(res["data"])
            except requests.RequestException:
                continue
        raise RenphoAPIError("Failed to fetch device info")

    def get_body_composition(self, table_name: str, user_id=None, page_size: int = 50) -> list[dict]:
        """Fetch impedance measurements for specified table and user."""
        uid = user_id or self.user_id
        items = []
        page = 1
        while True:
            req = {"pageNum": page, "pageSize": page_size, "userIds": [str(uid)], "tableName": table_name}
            res = self._post(ENDPOINTS["body_composition"], encrypt_request(req))
            if not res.get("data"):
                break
            page_data = decrypt_response(res["data"])
            records = page_data.get(table_name) if isinstance(page_data, dict) else page_data
            if not records:
                break
            items.extend(records)
            if len(records) < page_size:
                break
            page += 1
        return items

    def get_all_measurements(self) -> list[dict]:
        """Fetch all available scale records for the account."""
        if not self.token:
            self.login()
        dev = self.get_device_info()
        tables = [s["tableName"] for s in dev.get("scale", []) if "tableName" in s]
        if not tables:
            tables = [f"measurements_info_{int(self.user_id) % 24}"]
        all_records = []
        for tbl in tables:
            records = self.get_body_composition(tbl, self.user_id)
            all_records.extend(records)
        all_records.sort(key=lambda r: r.get("timeStamp", 0), reverse=True)
        return all_records
