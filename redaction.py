"""Secret redaction for error text that is logged, stored or shown to users.

`requests` exceptions embed the full request URL, and the Telegram Bot API puts
the bot token in that URL (``https://api.telegram.org/bot<TOKEN>/sendMessage``).
Anything that persists or displays ``str(exc)`` must pass through
:func:`redact_secrets` first.

This module deliberately has no dependencies and reads no required environment
variables, so any process (worker, bot, dashboard) can import it.
"""

import os
import re

# Telegram bot tokens look like "<digits>:<35 url-safe chars>".
_BOT_TOKEN_IN_URL = re.compile(r"(bot)\d{3,}:[A-Za-z0-9_-]{10,}")
_BARE_TOKEN = re.compile(r"\b\d{6,}:[A-Za-z0-9_-]{30,}\b")

REDACTED = "<redacted>"


def redact_secrets(value):
    """Return ``str(value)`` with the bot token (and token-shaped strings) removed."""

    text = str(value)

    token = os.environ.get("BOT_TOKEN", "").strip()
    if token:
        text = text.replace(token, REDACTED)

    text = _BOT_TOKEN_IN_URL.sub(rf"\1{REDACTED}", text)
    return _BARE_TOKEN.sub(REDACTED, text)
