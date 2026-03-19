import asyncio
from telethon import TelegramClient

API_ID = 1916950
API_HASH = "9e268fee501ad809e4f5f598adcb970c"

OUTPUT_FILE = "daftar_dialog.txt"

async def main():
    client = TelegramClient("my_telegram_session", API_ID, API_HASH)
    await client.start()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        async for dialog in client.iter_dialogs():
            line = f"{dialog.id} | {dialog.name}\n"
            f.write(line)
            print(line.strip())  # optional: tetap tampil di terminal

    await client.disconnect()
    print(f"\nSelesai! Data disimpan di: {OUTPUT_FILE}")

asyncio.run(main())