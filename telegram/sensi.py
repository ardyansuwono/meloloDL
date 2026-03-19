from telethon.sync import TelegramClient
from telethon.sessions import StringSession

api_id = 1916950
api_hash = "9e268fee501ad809e4f5f598adcb970c"

with TelegramClient(StringSession(), api_id, api_hash) as client:
    print(client.session.save())