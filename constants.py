SUBSCRIBERS_FILE = "subscribers.json"
STATE_FILE = "telegram_state.json"
KNOWN_RESULTS_FILE = "known_results.json"
STRUCTURE_FILE = "structure.json"

# Telegram's hard cap is 4096 chars per message. Leave headroom for the
# emoji/prefix text every message wraps around its content.
TELEGRAM_MAX_MESSAGE_CHARS = 4096
TELEGRAM_SAFE_MESSAGE_CHARS = 3900
