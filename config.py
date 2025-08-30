# Required channel IDs (integers)
SOURCE_CHANNEL_ID = 123 # Replace
DEST_CHANNEL_ID   = 456 # Replace

# Optional range selection (by *message links* copied from Discord → “Copy Message Link”)
START_MESSAGE_LINK = "" # empty → start of channel
END_MESSAGE_LINK   = "" # empty → end of channel

# Additional settings
SHOW_AUTHOR_NAME = True # True → "**Author:** " prefix; False → no author prefix
SHOW_TIMESTAMPS = True # True → display message timestamps in Discord-style format
IGNORE_BOT_MESSAGES = False # False = include bot/webhook messages too
INCLUDE_SYSTEM_MESSAGES = True  # True = include non-default types (pins, joins, thread starters, etc.)

# Limits / pacing
MAX_UPLOAD_BYTES = 24 * 1024 * 1024 # ~24 MB per file (raise only if your dest server tier allows)
SLEEP_BETWEEN_SENDS_SEC = 0.35  # gentle pacing; discord.py also rate-limits
CHUNK_LIMIT = 2000  # Discord hard cap
ATTACHMENTS_PER_MESSAGE = 10  # Discord hard cap
