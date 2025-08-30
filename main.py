import asyncio
import io
import re
from datetime import datetime
from typing import List, Tuple, Optional

import discord
from keys import BOT_TOKEN
import config

# Intents sufficient for reading history/content and sending
intents = discord.Intents.none()
intents.guilds = True
intents.messages = True
intents.message_content = True

client = discord.Client(intents=intents)


def chunk_text(text: str, limit: int) -> List[str]:
    if not text:
        return []
    return [text[i:i + limit] for i in range(0, len(text), limit)]


async def send_with_files(
    channel: discord.abc.Messageable,
    content: Optional[str],
    files: List[discord.File],
) -> None:
    """Send content + up to N files per message; batch if >N."""
    n = config.ATTACHMENTS_PER_MESSAGE
    if not files:
        await channel.send(content=content or None)
        return

    batches = [files[i:i + n] for i in range(0, len(files), n)]
    for idx, batch in enumerate(batches):
        msg_text = content if idx == 0 else ("(continued attachments)" if content else "")
        await channel.send(content=msg_text or None, files=batch)


async def reupload_attachments(message: discord.Message) -> Tuple[List[discord.File], List[str]]:
    """Download attachments and return (uploadable_files, link_notes_for_skipped)."""
    uploadables: List[discord.File] = []
    link_notes: List[str] = []

    for a in message.attachments:
        try:
            if a.size is not None and a.size > config.MAX_UPLOAD_BYTES:
                link_notes.append(f"{a.filename} *(too large to re-upload; link only)*\n{a.url}")
                continue

            data: bytes = await a.read(use_cached=False)
            if not data:
                link_notes.append(f"{a.filename} *(download failed; link only)*\n{a.url}")
                continue
            if len(data) > config.MAX_UPLOAD_BYTES:
                link_notes.append(f"{a.filename} *(too large to re-upload after download; link only)*\n{a.url}")
                continue

            uploadables.append(discord.File(fp=io.BytesIO(data), filename=a.filename))
        except Exception:
            link_notes.append(f"{a.filename} *(download failed; link only)*\n{a.url}")

    return uploadables, link_notes


def message_type_name(m: discord.Message) -> str:
    try:
        return m.type.name
    except Exception:
        return str(m.type)


def is_webhook_message(m: discord.Message) -> bool:
    return getattr(m, "webhook_id", None) is not None


def should_skip_message(m: discord.Message) -> Tuple[bool, str]:
    if config.IGNORE_BOT_MESSAGES:
        if m.author.bot:
            return True, "bot_author"
        if is_webhook_message(m):
            return True, "webhook"
    if not config.INCLUDE_SYSTEM_MESSAGES and m.type is not discord.MessageType.default:
        return True, f"non_default_type:{message_type_name(m)}"
    return False, ""


_LINK_RE = re.compile(
    r"https?://(?:ptb\.|canary\.)?discord(?:app)?\.com/channels/(?P<guild>\d+)/(?P<channel>\d+)/(?P<message>\d+)"
)


def parse_message_link(link: str) -> Optional[Tuple[int, int, int]]:
    if not link:
        return None
    m = _LINK_RE.match(link.strip())
    if not m:
        raise ValueError(f"Invalid message link: {link}")
    guild_id = int(m.group("guild"))
    channel_id = int(m.group("channel"))
    message_id = int(m.group("message"))
    return guild_id, channel_id, message_id


async def resolve_range(source: discord.abc.GuildChannel) -> List[discord.Message]:
    """
    Return the messages to copy, respecting START_MESSAGE_LINK / END_MESSAGE_LINK.
    Inclusive of boundaries if provided.
    """
    start_triplet = parse_message_link(config.START_MESSAGE_LINK) if config.START_MESSAGE_LINK else None
    end_triplet   = parse_message_link(config.END_MESSAGE_LINK) if config.END_MESSAGE_LINK else None

    start_msg = end_msg = None

    # Validate links belong to the source channel
    if start_triplet:
        _sg, sc, sm = start_triplet
        if sc != config.SOURCE_CHANNEL_ID:
            raise RuntimeError("START_MESSAGE_LINK channel ID does not match SOURCE_CHANNEL_ID.")
        start_msg = await source.fetch_message(sm)
    if end_triplet:
        _eg, ec, em = end_triplet
        if ec != config.SOURCE_CHANNEL_ID:
            raise RuntimeError("END_MESSAGE_LINK channel ID does not match SOURCE_CHANNEL_ID.")
        end_msg = await source.fetch_message(em)

    # Whole channel
    if not start_msg and not end_msg:
        messages: List[discord.Message] = []
        async for m in source.history(limit=None, oldest_first=True):
            messages.append(m)
        return messages

    # Start → end of channel
    if start_msg and not end_msg:
        messages: List[discord.Message] = [start_msg]
        async for m in source.history(limit=None, oldest_first=True, after=start_msg):
            messages.append(m)
        return messages

    # Start of channel → End
    if end_msg and not start_msg:
        messages: List[discord.Message] = []
        async for m in source.history(limit=None, oldest_first=True, before=end_msg):
            messages.append(m)
        messages.append(end_msg)
        return messages

    # Both provided
    if start_msg.created_at > end_msg.created_at:
        raise RuntimeError("START_MESSAGE_LINK refers to a newer message than END_MESSAGE_LINK. Swap them.")

    messages: List[discord.Message] = [start_msg]
    async for m in source.history(limit=None, oldest_first=True, after=start_msg, before=end_msg):
        messages.append(m)
    if start_msg.id != end_msg.id:
        messages.append(end_msg)
    return messages


@client.event
async def on_ready():
    print(f"Logged in as {client.user} (id={client.user.id})")

    # Resolve channels
    src = client.get_channel(config.SOURCE_CHANNEL_ID) or await client.fetch_channel(config.SOURCE_CHANNEL_ID)
    dst = client.get_channel(config.DEST_CHANNEL_ID) or await client.fetch_channel(config.DEST_CHANNEL_ID)

    if not isinstance(src, (discord.TextChannel, discord.Thread, discord.ForumChannel)):
        raise RuntimeError("SOURCE_CHANNEL_ID is not a readable text channel/thread/forum.")
    if not isinstance(dst, (discord.TextChannel, discord.Thread, discord.ForumChannel)):
        raise RuntimeError("DEST_CHANNEL_ID is not a sendable text channel/thread/forum.")

    # Build list according to range
    print("Building message list based on config range…")
    history: List[discord.Message] = await resolve_range(src)
    print(f"Selected {len(history)} messages to transfer.")

    total_sent = 0
    total_files_uploaded = 0
    total_files_linked = 0
    skipped = {"bot_author": 0, "webhook": 0, "non_default_type": 0, "empty_send_blocked": 0}

    prev_author_id: Optional[int] = None  # only show header when author changes

    for idx, msg in enumerate(history, start=1):
        skip, reason = should_skip_message(msg)
        if skip:
            if reason.startswith("non_default_type"):
                skipped["non_default_type"] += 1
            else:
                skipped[reason] = skipped.get(reason, 0) + 1
            continue

        try:
            author_name = getattr(msg.author, "display_name", None) or msg.author.name
            content_text = (msg.content or "").strip()

            # Determine whether to show the header now (Discord-style author blocks)
            show_header_now = bool(config.SHOW_AUTHOR_NAME and (msg.author.id != prev_author_id))

            # Timestamp string (Discord-like format)
            timestamp_str = ""
            if config.SHOW_TIMESTAMPS:
                # Example: 12/07/2025 3:06 PM (UTC timestamps by default; discord.py uses aware datetimes)
                # If you need local time, convert with tzinfo before formatting.
                timestamp_str = msg.created_at.strftime("%m/%d/%Y %-I:%M %p") if hasattr(datetime, "strftime") else ""

            header_line = ""
            if show_header_now and config.SHOW_AUTHOR_NAME:
                header_line = f"**{author_name}**"
                if timestamp_str:
                    header_line += f" • *{timestamp_str}*"
            elif not config.SHOW_AUTHOR_NAME and config.SHOW_TIMESTAMPS:
                # No author grouping → show timestamp per message
                header_line = f"*{timestamp_str}*" if timestamp_str else ""

            # Build base text (no jump link). If same author continues and SHOW_AUTHOR_NAME=True,
            # we suppress timestamp on subsequent messages to mimic Discord blocks.
            if content_text:
                base_text = f"{header_line}\n{content_text}" if header_line else content_text
            else:
                base_text = header_line  # may be empty if same author and no text

            text_chunks = chunk_text(base_text, config.CHUNK_LIMIT)

            # Attachments
            files_to_upload, link_notes = await reupload_attachments(msg)
            total_files_uploaded += len(files_to_upload)
            total_files_linked += len(link_notes)

            # Skip if absolutely nothing to send
            if not text_chunks and not files_to_upload and not link_notes:
                skipped["empty_send_blocked"] += 1
                prev_author_id = msg.author.id  # still advance author tracker
                continue

            # First chunk + files
            if files_to_upload:
                first_chunk = text_chunks[0] if text_chunks else ""
                await send_with_files(dst, first_chunk or None, files_to_upload)
                for extra_chunk in text_chunks[1:]:
                    await dst.send(content=extra_chunk)
                    await asyncio.sleep(config.SLEEP_BETWEEN_SENDS_SEC)
            else:
                # No files → send all text chunks (could be zero if only link_notes)
                for chunk in text_chunks:
                    await dst.send(content=chunk)
                    await asyncio.sleep(config.SLEEP_BETWEEN_SENDS_SEC)

            # Link-only fallbacks for skipped/failed/oversized files
            for note in link_notes:
                await dst.send(content=note)
                await asyncio.sleep(config.SLEEP_BETWEEN_SENDS_SEC)

            total_sent += 1
            prev_author_id = msg.author.id  # update after successful processing

            if idx % 25 == 0:
                print(f"Progress: {idx}/{len(history)} processed…")

            await asyncio.sleep(config.SLEEP_BETWEEN_SENDS_SEC)

        except discord.HTTPException as http_err:
            print(f"[HTTP {http_err.status}] sending message id={msg.id} type={message_type_name(msg)}: {http_err}")
            await asyncio.sleep(1.5)
            continue
        except Exception as e:
            print(f"[Error] message id={msg.id} type={message_type_name(msg)}: {e}")
            await asyncio.sleep(0.5)
            continue

    print(
        "Done.",
        f"sent_messages={total_sent}, files_reuploaded={total_files_uploaded}, files_linked={total_files_linked},",
        f"skipped={skipped}"
    )
    await client.close()


if __name__ == "__main__":
    client.run(BOT_TOKEN)
