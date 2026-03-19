import asyncio
from pathlib import Path
from telethon import TelegramClient, errors
from telethon.tl.functions.messages import ImportChatInviteRequest
from telethon.tl.types import Channel, Chat, User

API_ID = 1916950
API_HASH = "9e268fee501ad809e4f5f598adcb970c"
SESSION_NAME = "my_telegram_session"

BASE_DIR = Path("downloads")
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".mp4", ".pdf", ".zip"}
LIMIT = 0

FORWARD_DELAY_SECONDS = 2.5      # jeda antar forward
DOWNLOAD_DELAY_SECONDS = 0.5     # jeda antar download
BATCH_SIZE = 15                  # istirahat tiap 20 item
BATCH_REST_SECONDS = 20          # lama istirahat antar batch
PROGRESS_FILE = "forward_progress.txt"


def get_ext(message) -> str:
    if message.file and message.file.ext:
        return message.file.ext.lower()
    return ""


def is_valid_media(message) -> bool:
    if not message or not message.media:
        return False

    ext = get_ext(message)
    if ALLOWED_EXTENSIONS and ext not in ALLOWED_EXTENSIONS:
        return False

    return True


def sanitize_name(name: str) -> str:
    return "".join(c if c.isalnum() or c in (" ", "_", "-") else "_" for c in name).strip() or "unknown"


def parse_target_input(value: str):
    value = value.strip()
    if not value:
        return value
    if value.lstrip("-").isdigit():
        return int(value)
    return value


def load_last_forwarded_id() -> int:
    path = Path(PROGRESS_FILE)
    if not path.exists():
        return 0
    try:
        return int(path.read_text(encoding="utf-8").strip() or "0")
    except Exception:
        return 0


def save_last_forwarded_id(message_id: int):
    Path(PROGRESS_FILE).write_text(str(message_id), encoding="utf-8")


async def join_if_needed(client: TelegramClient, target: str):
    if not isinstance(target, str):
        return

    link = target.strip()
    invite_hash = None

    if "t.me/+" in link:
        invite_hash = link.split("t.me/+", 1)[1].split("?", 1)[0].strip("/")
    elif "t.me/joinchat/" in link:
        invite_hash = link.split("t.me/joinchat/", 1)[1].split("?", 1)[0].strip("/")

    if not invite_hash:
        return

    try:
        print("Mencoba join via invite link...")
        await client(ImportChatInviteRequest(invite_hash))
        print("Berhasil join atau sudah join.")
    except errors.UserAlreadyParticipantError:
        print("Akun sudah join.")
    except Exception as e:
        print(f"Tidak bisa join otomatis: {e}")


async def resolve_entity(client: TelegramClient, target):
    if isinstance(target, str):
        await join_if_needed(client, target)
    return await client.get_entity(target)


def describe_entity(entity) -> str:
    if isinstance(entity, User):
        return f"{entity.first_name or ''} {entity.last_name or ''}".strip() or str(entity.id)
    if isinstance(entity, (Channel, Chat)):
        return getattr(entity, "title", None) or getattr(entity, "username", None) or str(entity.id)
    return str(getattr(entity, "id", "unknown"))


async def scan_media(client: TelegramClient, entity, limit: int = 0):
    total_media = 0
    messages_cache = []

    print("Scanning media...")
    async for message in client.iter_messages(entity, limit=None if limit == 0 else limit):
        if is_valid_media(message):
            total_media += 1
            messages_cache.append(message)

    return total_media, messages_cache


async def forward_media_safely(client: TelegramClient, messages_cache, forward_to):
    count = 0
    processed_in_batch = 0
    last_done_id = load_last_forwarded_id()

    # skip yang sudah pernah berhasil diforward
    pending_messages = [m for m in messages_cache if m.id > last_done_id]
    total_pending = len(pending_messages)

    print(f"Progress sebelumnya sampai msg id: {last_done_id}")
    print(f"Sisa yang akan diproses: {total_pending}")

    for idx, message in enumerate(pending_messages, start=1):
        try:
            await client.forward_messages(forward_to, message)
            count += 1
            processed_in_batch += 1
            save_last_forwarded_id(message.id)

            print(f"[{idx}/{total_pending}] Forwarded msg {message.id}")

            await asyncio.sleep(FORWARD_DELAY_SECONDS)

            if processed_in_batch >= BATCH_SIZE:
                print(f"Istirahat batch {BATCH_REST_SECONDS}s...")
                await asyncio.sleep(BATCH_REST_SECONDS)
                processed_in_batch = 0

        except errors.FloodWaitError as e:
            print(f"FloodWait {e.seconds}s, menunggu lalu lanjut...")
            await asyncio.sleep(e.seconds + 3)

        except Exception as e:
            print(f"Error forward msg {message.id}: {e}")

    return count


async def main():
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

    # Auto-sleep untuk flood wait pendek, biar lebih halus.
    # Flood wait yang lebih panjang tetap akan dilempar kalau melewati threshold ini.
    client.flood_sleep_threshold = 60

    await client.start()

    try:
        raw_target = input("Masukkan target sumber: ").strip()
        target = parse_target_input(raw_target)

        entity = await resolve_entity(client, target)
        chat_name = describe_entity(entity)

        print(f"\nSumber: {chat_name}")

        total_media, messages_cache = await scan_media(client, entity, LIMIT)
        print(f"Total media ditemukan: {total_media}")

        if total_media == 0:
            print("Tidak ada media yang cocok.")
            return

        raw_forward = input("Masukkan tujuan forward (me/@username/-100xxxx): ").strip()
        forward_to = parse_target_input(raw_forward)
        forward_entity = await resolve_entity(client, forward_to)

        print(f"Tujuan forward: {describe_entity(forward_entity)}")
        print("\nMulai forward aman...\n")

        count = await forward_media_safely(client, messages_cache, forward_to)
        print(f"\nSelesai forward berhasil: {count}")

    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())