import os
from typing import List

from telethon import TelegramClient, events
from telethon.errors import RPCError

from keep_alive import keep_alive


def _get_required_secret(key: str, cast_type):
    raw = os.getenv(key)
    if raw is None:
        raise RuntimeError(f"Missing required secret: {key}")
    try:
        return cast_type(raw)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"Invalid value for secret {key}: {raw}") from exc


API_ID = _get_required_secret("API_ID", int)
API_HASH = _get_required_secret("API_HASH", str)

# IMPORTANT: unique session name for Render
SESSION_NAME = os.getenv("SESSION_NAME", "render_session")

CHANNEL_ID = _get_required_secret("CHANNEL_ID", int)

_alert_recipient_raw = os.getenv("ALERT_RECIPIENT_IDS", "").strip()
if _alert_recipient_raw:
    ALERT_RECIPIENT_IDS: List[int] = [
        int(user_id.strip())
        for user_id in _alert_recipient_raw.split(",")
        if user_id.strip()
    ]
else:
    ALERT_RECIPIENT_IDS = [_get_required_secret("MAIN_USER_ID", int)]

# The session file MUST NOT be committed to GitHub
client = TelegramClient(SESSION_NAME, API_ID, API_HASH)


def format_event_message(event) -> str:
    sender = getattr(event.sender, "first_name", "Someone")
    text = event.raw_text or "(no text content)"

    media_hint = ""
    if event.message.media:
        media_hint = "\n\n[Attached media present]"

    return f"📢 New message in your private channel\n\nSender: {sender}\n\n{text}{media_hint}"


async def start_listener():
    print("🚀 Starting Telegram Alert System...")

    try:
        await client.start()
    except Exception as exc:
        print("❌ Failed to start Telethon:", exc)
        print("💡 If this is AuthKeyDuplicatedError, delete the session file and redeploy.")
        raise

    me = await client.get_me()
    print(f"✅ Logged in as {me.first_name} (id={me.id})")

    try:
        channel_entity = await client.get_entity(CHANNEL_ID)
        print("📌 Channel resolved successfully.")
    except Exception as exc:
        print("❌ Error resolving channel:", exc)
        raise

    @client.on(events.NewMessage(chats=channel_entity))
    async def handler(event):
        message_preview = format_event_message(event)
        print("🔔 New message detected:")
        print(message_preview)

        for recipient in ALERT_RECIPIENT_IDS:
            try:
                await client.send_message(recipient, message_preview)
                print(f"➡️ Alert sent to {recipient}")
            except RPCError as exc:
                print(f"❌ Failed to alert {recipient}: {exc}")

    print("👂 Listening for new messages...")
    await client.run_until_disconnected()


def main():
    keep_alive()
    client.loop.run_until_complete(start_listener())


if __name__ == "__main__":
    main()
