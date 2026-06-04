import subprocess

from telegram_utils import send

subprocess.run(
    ["python", "build_structure.py"],
    check=True
)

send("structure.json generated ✅")
