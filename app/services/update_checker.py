"Update checker for NCRenamer"
import requests
from app.version import APP_VERSION

VERSION_URL = "https://raw.githubusercontent.com/uzuran/NCRenamer/main/version.json"


def check_for_updates():

    try:
        response = requests.get(VERSION_URL, timeout=3)
        data = response.json()

        latest = data["version"]

        if latest != APP_VERSION:
            return True, data["download"]

    except Exception:
        pass

    return False, None