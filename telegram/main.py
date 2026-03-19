import os
import asyncio
from pathlib import Path
from telethon import TelegramClient, errors

# =========================
# KONFIGURASI
# =========================
API_ID = 1916950                 # ganti dengan api_id kamu
API_HASH = "9e268fee501ad809e4f5f598adcb970c"         # ganti dengan api_hash kamu
SESSION_NAME = "my_telegram_session"

# Bisa pakai:
# - username publik, mis. "@nama_channel"
# - ID chat/channel, mis. -1001234567890
# - link t.me/c/... TIDAK selalu stabil untuk dipakai langsung
TARGET = -1003892909915

DOWNLOAD_DIR = "downloads"
LIMIT = 100                        # 0 = tanpa batas
REVERSE = False                    # False = terbaru ke lama, True = lama ke terbaru

# Filter tipe file opsional:
# None = semua media
# Pilihan contoh: "photo", "video", "document"
MEDIA_TYPE = None


def media_matches(message, media_type: str | None) -> bool:
    if not message or not message.media:
        return False

    if media_type is None:
        return True

    media_type = media_type.lower()

    if media_type == "photo":
        return bool(message.photo)

    if media_type == "video":
        return bool(message.video)

    if media_type == "document":
        return bool(message.document)

    return False


async def main():
    Path(DOWNLOAD_DIR).mkdir(parents=True, exist_ok=True)

    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

    await client.start()
    me = await client.get_me()
    print(f"Login sukses sebagai: {me.first_name} (@{me.username})")

    try:
        entity = await client.get_entity(TARGET)
    except ValueError:
        print("Target tidak ditemukan. Pastikan akunmu memang punya akses ke group/channel tersebut.")
        await client.disconnect()
        return

    print(f"Mulai ambil media dari: {getattr(entity, 'title', None) or getattr(entity, 'username', None) or entity.id}")

    downloaded = 0
    scanned = 0

    try:
        async for message in client.iter_messages(entity, limit=None if LIMIT == 0 else LIMIT, reverse=REVERSE):
            scanned += 1

            if not media_matches(message, MEDIA_TYPE):
                continue

            try:
                file_path = await message.download_media(file=DOWNLOAD_DIR)
                if file_path:
                    downloaded += 1
                    print(f"[{downloaded}] Downloaded: {file_path}")
            except errors.FloodWaitError as e:
                print(f"Flood wait {e.seconds} detik. Menunggu...")
                await asyncio.sleep(e.seconds)
            except Exception as e:
                print(f"Gagal download message_id={message.id}: {e}")

    finally:
        await client.disconnect()

    print("\nSelesai")
    print(f"Pesan discan   : {scanned}")
    print(f"Media didownload: {downloaded}")


if __name__ == "__main__":
    asyncio.run(main())