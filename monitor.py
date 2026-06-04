import subprocess

from telegram_utils import send

subprocess.run(
    ["python", "initialize_results.py"],
    check=True
)

send(
    "known_results.json initialized ✅"
)
