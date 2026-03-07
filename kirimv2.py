import os
import asyncio
import subprocess
from telethon import TelegramClient
from telethon.errors import FloodWaitError
from telethon.tl.types import DocumentAttributeVideo
from pymediainfo import MediaInfo
from tqdm import tqdm

# ======================
# TELEGRAM API
# ======================

api_id = 1916950
api_hash = "9e268fee501ad809e4f5f598adcb970c"

client = TelegramClient("mysession", api_id, api_hash)

# ======================
# GET VIDEO FILES
# ======================

def get_video_files(folder):

    videos = []

    for root, dirs, files in os.walk(folder):

        for file in files:

            if file.lower().endswith((".mp4", ".mkv", ".avi", ".mov")):
                videos.append(os.path.join(root, file))

    videos.sort()

    return videos

# ======================
# GENERATE CAPTION
# ======================

def generate_caption(file_path):

    filename = os.path.basename(file_path)

    caption = os.path.splitext(filename)[0]

    caption = caption.replace(".", " ").replace("_", " ").title()

    return caption

# ======================
# GET VIDEO METADATA
# ======================

def get_video_metadata(file_path):

    media_info = MediaInfo.parse(file_path)

    for track in media_info.tracks:

        if track.track_type == "Video":

            duration = int(track.duration / 1000)
            width = track.width
            height = track.height

            return duration, width, height

    return 0, 0, 0

# ======================
# GENERATE THUMBNAIL
# ======================

def generate_thumbnail(video_path):

    thumb_path = video_path + ".jpg"

    command = [
        "ffmpeg",
        "-y",
        "-ss", "00:00:05",
        "-i", video_path,
        "-vframes", "1",
        "-q:v", "2",
        thumb_path
    ]

    subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    return thumb_path

# ======================
# UPLOAD FILE
# ======================

async def upload_file(target, file_path, index, total):

    filename = os.path.basename(file_path)

    caption = generate_caption(file_path)

    duration, width, height = get_video_metadata(file_path)

    thumb = generate_thumbnail(file_path)

    file_size = os.path.getsize(file_path)

    print(f"\nUploading ({index}/{total})")
    print(filename)

    with tqdm(
        total=file_size,
        unit="B",
        unit_scale=True,
        unit_divisor=1024,
        desc=filename
    ) as pbar:

        async def progress(current, total):

            pbar.total = total
            pbar.update(current - pbar.n)

        retry = 3

        while retry > 0:

            try:

                await client.send_file(
                    target,
                    file_path,
                    caption=caption,
                    thumb=thumb,
                    supports_streaming=True,
                    attributes=[
                        DocumentAttributeVideo(
                            duration=duration,
                            w=width,
                            h=height,
                            supports_streaming=True
                        )
                    ],
                    workers=24,
                    part_size_kb=1024,
                    progress_callback=progress
                )

                print("✅ Upload selesai")

                break

            except FloodWaitError as e:

                wait = int(e.seconds)

                print(f"\n⚠ FloodWait {wait} detik. Menunggu...")

                await asyncio.sleep(wait)

            except Exception as e:

                retry -= 1

                print(f"\n❌ Error upload: {e}")

                if retry > 0:

                    print("🔁 Retry upload dalam 5 detik...")

                    await asyncio.sleep(5)

                else:

                    print("❌ Upload gagal")

# ======================
# MAIN MENU
# ======================

async def main():

    print("\n=== TELEGRAM VIDEO UPLOADER ===\n")

    print("1. Cowok")
    print("2. Cewek")
    print("3. Saved Messages")
    print("4. Custom Target\n")

    choice = input("Pilih tujuan (1-4): ").strip()

    if choice == "1":

        target_input = "https://t.me/+UMMnQy0_eUJlNjI1"

    elif choice == "2":

        target_input = "https://t.me/+-b0j641W63gzNDVl"

    elif choice == "3":

        target_input = "me"

    elif choice == "4":

        target_input = input("Masukkan username / link / ID: ")

    else:

        print("❌ Pilihan tidak valid")

        return

    print("\nResolving target...")

    target = await client.get_entity(target_input)

    print("✅ Target ditemukan")

    folder = input("\nMasukkan path folder video: ")

    if not os.path.isdir(folder):

        print("❌ Folder tidak ditemukan")

        return

    videos = get_video_files(folder)

    if not videos:

        print("❌ Tidak ada video ditemukan")

        return

    total = len(videos)

    print(f"\nTotal video ditemukan: {total}")

    for i, video in enumerate(videos, start=1):

        await upload_file(target, video, i, total)

    print("\n🎉 Semua upload selesai")

# ======================
# START CLIENT
# ======================

with client:

    client.loop.run_until_complete(main())