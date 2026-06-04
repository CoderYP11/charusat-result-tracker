import json
import base64
import requests
import os

OWNER = "CoderYP11"
REPO = "charusat-result-tracker"
BRANCH = "main"

GH_TOKEN = os.environ["GH_TOKEN"]

API_URL = (
    f"https://api.github.com/repos/"
    f"{OWNER}/{REPO}/contents/"
    f"known_results.json"
)


def load_known_results():

    headers = {
        "Authorization": f"Bearer {GH_TOKEN}",
        "Accept": "application/vnd.github+json"
    }

    response = requests.get(
        API_URL,
        headers=headers,
        timeout=30
    )

    if response.status_code != 200:
        return {}

    data = response.json()

    content = base64.b64decode(
        data["content"]
    ).decode()

    return json.loads(content)


def save_known_results(results):

    headers = {
        "Authorization": f"Bearer {GH_TOKEN}",
        "Accept": "application/vnd.github+json"
    }

    current = requests.get(
        API_URL,
        headers=headers,
        timeout=30
    )

    sha = None

    if current.status_code == 200:
        sha = current.json()["sha"]

    encoded = base64.b64encode(
        json.dumps(
            results,
            indent=2
        ).encode()
    ).decode()

    payload = {
        "message": "Update known_results.json",
        "content": encoded,
        "branch": BRANCH
    }

    if sha:
        payload["sha"] = sha

    response = requests.put(
        API_URL,
        headers=headers,
        json=payload,
        timeout=60
    )

    response.raise_for_status()
