import os
import requests
import subprocess
import random
import time
from tqdm import tqdm

API_DOMAIN = "api.vxtwitter.com"

BASE = os.path.dirname(os.path.abspath(__file__))

VIDEO_DIR = os.path.join(BASE, "downloads", "videos")
IMAGE_DIR = os.path.join(BASE, "downloads", "images")

os.makedirs(VIDEO_DIR, exist_ok=True)
os.makedirs(IMAGE_DIR, exist_ok=True)


# =========================
# RANDOM USER AGENT
# =========================

USER_AGENTS = [
"Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
"Mozilla/5.0 (X11; Linux x86_64)",
"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0",
"Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)",
"Mozilla/5.0 (Linux; Android 13)"
]


def get_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Referer": "https://x.com/"
    }


# =========================
# SMART DELAY
# =========================

fail_count = 0


def smart_delay():

    global fail_count

    base = random.uniform(2, 5)

    delay = base + (fail_count * 2)

    print(f"⏳ Delay {delay:.2f} detik")

    time.sleep(delay)


# =========================
# UNIQUE FILE NAME
# =========================

def get_unique_filename(directory, filename):

    base, ext = os.path.splitext(filename)

    counter = 1
    new_name = filename
    path = os.path.join(directory, new_name)

    while os.path.exists(path):

        new_name = f"{base}_{counter}{ext}"
        path = os.path.join(directory, new_name)

        counter += 1

    return path


# =========================
# DOWNLOAD FILE
# =========================

def download_file(url, path):

    global fail_count

    for attempt in range(3):

        try:

            r = requests.get(
                url,
                headers=get_headers(),
                stream=True,
                timeout=30
            )

            if r.status_code != 200:
                raise Exception("Download gagal")

            size = int(r.headers.get("content-length", 0))

            with open(path, "wb") as f, tqdm(
                total=size,
                unit="B",
                unit_scale=True,
                desc=os.path.basename(path)
            ) as bar:

                for chunk in r.iter_content(1024):

                    if chunk:
                        f.write(chunk)
                        bar.update(len(chunk))

            fail_count = 0
            return

        except Exception:

            print("⚠️ Retry download...", attempt + 1)

            fail_count += 1

            time.sleep(random.uniform(3, 7))


# =========================
# GET DATA
# =========================

def get_data(url):

    global fail_count

    api = url.replace("x.com", API_DOMAIN)

    for attempt in range(3):

        try:

            r = requests.get(
                api,
                headers=get_headers(),
                timeout=15
            )

            if r.status_code == 429:

                print("🚫 Rate limited. Menunggu...")

                fail_count += 1

                time.sleep(15)

                continue

            data = r.json()

            fail_count = 0

            return data

        except Exception:

            fail_count += 1

            time.sleep(random.uniform(3, 7))

    return None


# =========================
# HANDLE DOWNLOAD
# =========================

def handle_download(data, tweet_url):

    tweet_id = tweet_url.split("/")[-1]

    media_list = data.get("media_extended", [])

    if not media_list:
        print("❌ Tidak ada media")
        return

    img_count = 1

    for media in media_list:

        media_type = media.get("type")

        if media_type == "image":

            img = media["url"] + "?name=orig"

            filename = f"{tweet_id}_{img_count}.jpg"

            path = get_unique_filename(IMAGE_DIR, filename)

            print("📸 Download:", os.path.basename(path))

            download_file(img, path)

            img_count += 1

            smart_delay()

        elif media_type == "video":

            m3u8 = media["url"]

            filename = f"{tweet_id}.mp4"

            path = get_unique_filename(VIDEO_DIR, filename)

            print("🎬 Download video:", os.path.basename(path))

            subprocess.run([
                "ffmpeg",
                "-loglevel", "error",
                "-y",
                "-i", m3u8,
                "-c", "copy",
                path
            ])

            smart_delay()


# =========================
# DOWNLOAD MODES
# =========================

def download_single():

    url = input("URL X/Twitter: ")

    data = get_data(url)

    if data:
        handle_download(data, url)


def download_multi():

    print("Masukkan URL (ketik done jika selesai)")

    while True:

        url = input("URL: ")

        if url == "done":
            break

        data = get_data(url)

        if data:
            handle_download(data, url)

        smart_delay()


def download_bulk():

    file = input("Nama file txt: ")

    if not os.path.exists(file):
        print("File tidak ditemukan")
        return

    with open(file) as f:

        for link in f.read().splitlines():

            data = get_data(link)

            if data:
                handle_download(data, link)

            smart_delay()


# =========================
# MENU
# =========================

def menu():

    while True:

        print("""
==============================
  X / TWITTER DOWNLOADER
==============================

1. Download Single URL
2. Download Multi URL
3. Bulk Download (TXT)
4. Exit
""")

        pilih = input("Pilih menu: ")

        if pilih == "1":
            download_single()

        elif pilih == "2":
            download_multi()

        elif pilih == "3":
            download_bulk()

        elif pilih == "4":
            break


menu()