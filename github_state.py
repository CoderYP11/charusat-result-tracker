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

    if response.status_code == 404:
        return None

    if response.status_code != 200:
    
        raise Exception(
            f"Cannot load known_results.json. "
            f"Status: {response.status_code}. "
            f"Response: {response.text}"
        )

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

STRUCTURE_URL = (
    f"https://api.github.com/repos/"
    f"{OWNER}/{REPO}/contents/"
    f"structure.json"
)


def load_structure():

    headers = {
        "Authorization": f"Bearer {GH_TOKEN}",
        "Accept": "application/vnd.github+json"
    }

    response = requests.get(
        STRUCTURE_URL,
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


def save_structure(data):

    headers = {
        "Authorization": f"Bearer {GH_TOKEN}",
        "Accept": "application/vnd.github+json"
    }

    current = requests.get(
        STRUCTURE_URL,
        headers=headers,
        timeout=30
    )

    sha = None

    if current.status_code == 200:
        sha = current.json()["sha"]

    encoded = base64.b64encode(
        json.dumps(
            data,
            indent=2
        ).encode()
    ).decode()

    payload = {
        "message": "Update structure.json",
        "content": encoded,
        "branch": BRANCH
    }

    if sha:
        payload["sha"] = sha

    response = requests.put(
        STRUCTURE_URL,
        headers=headers,
        json=payload,
        timeout=60
    )

    response.raise_for_status()

def download_file(filename):

    headers = {
        "Authorization": f"Bearer {GH_TOKEN}",
        "Accept": "application/vnd.github+json"
    }

    url = (
        f"https://api.github.com/repos/"
        f"{OWNER}/{REPO}/contents/{filename}"
    )

    response = requests.get(
        url,
        headers=headers,
        timeout=30
    )

    if response.status_code != 200:

        raise Exception(
            f"Cannot load {filename}. "
            f"Status: {response.status_code}. "
            f"Response: {response.text}"
        )

    data = response.json()

    return base64.b64decode(
        data["content"]
    ).decode()


def upload_file(filename, content):

    headers = {
        "Authorization": f"Bearer {GH_TOKEN}",
        "Accept": "application/vnd.github+json"
    }

    url = (
        f"https://api.github.com/repos/"
        f"{OWNER}/{REPO}/contents/{filename}"
    )

    current = requests.get(
        url,
        headers=headers,
        timeout=30
    )

    sha = None

    if current.status_code == 200:

        sha = current.json()["sha"]

    encoded = base64.b64encode(
        content.encode()
    ).decode()

    payload = {
        "message": f"Update {filename}",
        "content": encoded,
        "branch": BRANCH
    }

    if sha:

        payload["sha"] = sha

    response = requests.put(
        url,
        headers=headers,
        json=payload,
        timeout=60
    )

    if response.status_code not in [200, 201]:

        raise Exception(
            f"Cannot upload {filename}. "
            f"Status: {response.status_code}. "
            f"Response: {response.text}"
        )
