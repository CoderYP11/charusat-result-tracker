import os
import json
import base64
import time
import requests

OWNER = "CoderYP11"
REPO = "charusat-result-tracker"
BRANCH = "main"

GH_TOKEN = os.environ["GH_TOKEN"]

HEADERS = {
    "Authorization": f"Bearer {GH_TOKEN}",
    "Accept": "application/vnd.github+json"
}

RETRYABLE_STATUSES = (409, 422, 429, 500, 502, 503)
MAX_ATTEMPTS = 3


def _url(filename):
    return f"https://api.github.com/repos/{OWNER}/{REPO}/contents/{filename}"


def _backoff(attempt):
    time.sleep(2 ** attempt)


def download_file(filename):
    url = _url(filename)

    for attempt in range(MAX_ATTEMPTS):

        try:
            response = requests.get(url, headers=HEADERS, timeout=30)
        except (requests.ConnectionError, requests.Timeout, requests.exceptions.SSLError) as e:
            if attempt < MAX_ATTEMPTS - 1:
                _backoff(attempt)
                continue
            raise Exception(f"Network error loading {filename}: {e}")

        if response.status_code == 200:
            data = response.json()
            return base64.b64decode(data["content"]).decode()

        if response.status_code in RETRYABLE_STATUSES and attempt < MAX_ATTEMPTS - 1:
            _backoff(attempt)
            continue

        raise Exception(
            f"Cannot load {filename}. "
            f"Status: {response.status_code}. "
            f"Response: {response.text}"
        )


def upload_file(filename, content):
    url = _url(filename)

    for attempt in range(MAX_ATTEMPTS):

        # --- Step 1: check whether the file already exists (need its sha to update it) ---
        try:
            current = requests.get(url, headers=HEADERS, timeout=30)
        except (requests.ConnectionError, requests.Timeout, requests.exceptions.SSLError) as e:
            if attempt < MAX_ATTEMPTS - 1:
                _backoff(attempt)
                continue
            raise Exception(f"Network error checking existing {filename} before upload: {e}")

        if current.status_code == 200:
            sha = current.json()["sha"]

        elif current.status_code == 404:
            sha = None

        elif current.status_code in RETRYABLE_STATUSES:
            if attempt < MAX_ATTEMPTS - 1:
                _backoff(attempt)
                continue
            raise Exception(
                f"Cannot check existing {filename} before upload. "
                f"Status: {current.status_code}. "
                f"Response: {current.text}"
            )

        else:
            raise Exception(
                f"Cannot check existing {filename} before upload. "
                f"Status: {current.status_code}. "
                f"Response: {current.text}"
            )

        # --- Step 2: upload (create or update) ---
        payload = {
            "message": f"Update {filename}",
            "content": base64.b64encode(content.encode()).decode(),
            "branch": BRANCH
        }

        if sha is not None:
            payload["sha"] = sha

        try:
            response = requests.put(url, headers=HEADERS, json=payload, timeout=60)
        except (requests.ConnectionError, requests.Timeout, requests.exceptions.SSLError) as e:
            if attempt < MAX_ATTEMPTS - 1:
                _backoff(attempt)
                continue
            raise Exception(f"Network error uploading {filename}: {e}")

        if response.status_code in (200, 201):
            return

        # A 409 here usually means someone else (another workflow run) wrote the
        # file between our GET and PUT. Retrying re-fetches a fresh sha above.
        if response.status_code in RETRYABLE_STATUSES and attempt < MAX_ATTEMPTS - 1:
            _backoff(attempt)
            continue

        raise Exception(
            f"Cannot upload {filename}. "
            f"Status: {response.status_code}. "
            f"Response: {response.text}"
        )


def load_known_results():
    try:
        return json.loads(download_file("known_results.json"))
    except Exception as e:
        if "Status: 404" in str(e):
            return None
        raise


def save_known_results(results):
    upload_file("known_results.json", json.dumps(results, indent=2))


def load_structure():
    try:
        return json.loads(download_file("structure.json"))
    except Exception as e:
        if "Status: 404" in str(e):
            return {}
        raise


def save_structure(data):
    upload_file("structure.json", json.dumps(data, indent=2))
