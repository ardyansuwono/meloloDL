import asyncio
import time
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

CHUNK_SIZE = 10
CHUNK_REST = 25
AFTER_FLOOD_EXTRA = 5
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


def clear_progress():
    path = Path(PROGRESS_FILE)
    if path.exists():
        path.unlink()


def format_seconds(seconds: float) -> str:
    seconds = max(0, int(seconds))
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours}j {minutes}m {secs}d"
    if minutes > 0:
        return f"{minutes}m {secs}d"
    return f"{secs}d"


def format_size(num_bytes: int) -> str:
    if num_bytes <= 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(num_bytes)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.2f} {unit}"
        size /= 1024


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
        print("Berhasil join atau akun memang sudah join.")
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


async def download_media(messages_cache, out_dir: Path):
    total = len(messages_cache)
    success_count = 0
    fail_count = 0
    total_bytes_downloaded = 0
    overall_start = time.time()

    print(f"Mulai download {total} media...\n")

    for idx, message in enumerate(messages_cache, start=1):
        try:
            file_size = 0
            if message.file and getattr(message.file, "size", None):
                file_size = message.file.size

            file_start = time.time()
            last_update = 0.0

            def progress_callback(current: int, total_bytes: int):
                nonlocal last_update
                now = time.time()

                if now - last_update < 0.5 and current < total_bytes:
                    return

                last_update = now
                elapsed_file = now - file_start
                speed = current / elapsed_file if elapsed_file > 0 else 0
                eta_file = (total_bytes - current) / speed if speed > 0 else 0
                percent_file = (current / total_bytes * 100) if total_bytes > 0 else 0
                percent_total = (((idx - 1) + (current / total_bytes if total_bytes > 0 else 0)) / total) * 100

                print(
                    f"\r[{idx}/{total}] "
                    f"Total {percent_total:.1f}% | "
                    f"File {percent_file:.1f}% | "
                    f"{format_size(current)}/{format_size(total_bytes)} | "
                    f"{format_size(speed)}/s | "
                    f"ETA file: {format_seconds(eta_file)}",
                    end="",
                    flush=True
                )

            path = await message.download_media(
                file=out_dir,
                progress_callback=progress_callback
            )

            print()

            if path:
                success_count += 1
                total_bytes_downloaded += file_size

                elapsed_total = time.time() - overall_start
                avg_speed_total = total_bytes_downloaded / elapsed_total if elapsed_total > 0 else 0
                overall_percent = (idx / total) * 100 if total else 0
                remaining_items = total - idx
                avg_files_per_sec = success_count / elapsed_total if elapsed_total > 0 else 0
                eta_total = remaining_items / avg_files_per_sec if avg_files_per_sec > 0 else 0

                print(
                    f"[{idx}/{total}] "
                    f"{overall_percent:.1f}% | OK | "
                    f"Size: {format_size(file_size)} | "
                    f"AvgSpeed: {format_size(avg_speed_total)}/s | "
                    f"ETA total: {format_seconds(eta_total)} | "
                    f"{path}"
                )
            else:
                fail_count += 1
                print(f"[{idx}/{total}] GAGAL | msg_id={message.id} | download_media return None")

        except errors.FloodWaitError as e:
            print(f"\n[{idx}/{total}] FloodWait {e.seconds}s, menunggu...")
            await asyncio.sleep(e.seconds + 2)

        except Exception as e:
            fail_count += 1
            print(f"\n[{idx}/{total}] ERROR | msg_id={message.id} | {e}")

    total_elapsed = time.time() - overall_start

    print("\n=== RINGKASAN DOWNLOAD ===")
    print(f"Total item   : {total}")
    print(f"Berhasil     : {success_count}")
    print(f"Gagal        : {fail_count}")
    print(f"Total ukuran : {format_size(total_bytes_downloaded)}")
    print(f"Durasi       : {format_seconds(total_elapsed)}")
    if total_elapsed > 0:
        print(f"Rata-rata    : {format_size(total_bytes_downloaded / total_elapsed)}/s")

    return success_count


async def forward_media_batched(client, source_entity, messages_cache, forward_to):
    sent = 0
    last_done_id = load_last_forwarded_id()

    pending_messages = [m for m in messages_cache if m.id > last_done_id]
    pending_ids = [m.id for m in pending_messages]

    total_pending = len(pending_ids)

    print(f"Progress sebelumnya sampai msg id: {last_done_id}")
    print(f"Total pending forward: {total_pending}")

    if total_pending == 0:
        print("Tidak ada pesan baru untuk diforward.")
        return 0

    for start in range(0, total_pending, CHUNK_SIZE):
        chunk_ids = pending_ids[start:start + CHUNK_SIZE]

        try:
            result = await client.forward_messages(
                forward_to,
                chunk_ids,
                from_peer=source_entity
            )

            if isinstance(result, list):
                ok_count = sum(1 for item in result if item is not None)
            else:
                ok_count = 1 if result is not None else 0

            sent += ok_count
            save_last_forwarded_id(max(chunk_ids))

            print(
                f"[{min(start + len(chunk_ids), total_pending)}/{total_pending}] "
                f"Batch forwarded: {ok_count} item | "
                f"msg_ids {chunk_ids[0]}..{chunk_ids[-1]}"
            )

            await asyncio.sleep(CHUNK_REST)

        except errors.FloodWaitError as e:
            print(f"FloodWait {e.seconds}s, menunggu...")
            await asyncio.sleep(e.seconds + AFTER_FLOOD_EXTRA)

        except Exception as e:
            print(f"Batch error msg_ids {chunk_ids[0]}..{chunk_ids[-1]}: {e}")

    return sent


async def main():
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    client.flood_sleep_threshold = 60
    await client.start()

    try:
        print("\n=== TELEGRAM MEDIA TOOL ===")
        print("Sumber bisa berupa:")
        print("- link public: https://t.me/nama_channel")
        print("- invite link: https://t.me/+xxxx")
        print("- username: @nama_channel")
        print("- ID: -100xxxxxxxxxx")
        print()

        raw_target = input("Masukkan target sumber: ").strip()
        target = parse_target_input(raw_target)

        entity = await resolve_entity(client, target)
        chat_name = describe_entity(entity)

        safe_name = sanitize_name(chat_name)
        out_dir = BASE_DIR / safe_name
        out_dir.mkdir(parents=True, exist_ok=True)

        print(f"\nSumber terdeteksi: {chat_name}")
        print(f"Folder download : {out_dir}")

        total_media, messages_cache = await scan_media(client, entity, LIMIT)
        print(f"\nTotal media ditemukan: {total_media}")

        if total_media == 0:
            print("Tidak ada media yang cocok dengan filter.")
            return

        print("\nPilih aksi:")
        print("1. Download semua media")
        print("2. Batch forward semua media")
        print("3. Reset progress batch forward")
        print("4. Batal")

        choice = input("Masukkan pilihan (1/2/3/4): ").strip()

        if choice == "1":
            print("\nMulai download...\n")
            count = await download_media(messages_cache, out_dir)
            print(f"\nSelesai download: {count}/{total_media}")

        elif choice == "2":
            raw_forward = input(
                "Masukkan tujuan forward (contoh: me, @username, -100xxxxxxxxxx, https://t.me/nama_channel): "
            ).strip()

            forward_to = parse_target_input(raw_forward)

            if isinstance(forward_to, str):
                await join_if_needed(client, forward_to)

            try:
                forward_entity = await client.get_entity(forward_to)
                print(f"Tujuan forward: {describe_entity(forward_entity)}")
            except Exception as e:
                print(f"Gagal resolve tujuan forward: {e}")
                return

            print("\nMulai batch forward...\n")
            count = await forward_media_batched(client, entity, messages_cache, forward_to)
            print(f"\nSelesai batch forward: {count} item berhasil")

        elif choice == "3":
            clear_progress()
            print("Progress batch forward berhasil di-reset.")

        else:
            print("Dibatalkan.")

    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())