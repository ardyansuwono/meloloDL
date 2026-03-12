import os
import requests
import subprocess
from tqdm import tqdm

API_DOMAIN = "api.vxtwitter.com"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://x.com/"
}

BASE = os.path.dirname(os.path.abspath(__file__))

VIDEO_DIR = os.path.join(BASE, "downloads", "videos")
IMAGE_DIR = os.path.join(BASE, "downloads", "images")

os.makedirs(VIDEO_DIR, exist_ok=True)
os.makedirs(IMAGE_DIR, exist_ok=True)


def download_file(url, path):

    r = requests.get(url, headers=HEADERS, stream=True)

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


def get_data(url):

    api = url.replace("x.com", API_DOMAIN)

    r = requests.get(api, headers=HEADERS)

    try:
        return r.json()
    except:
        return None


def handle_download(data, tweet_url):

    tweet_id = tweet_url.split("/")[-1]

    if "media_extended" not in data:
        print("❌ Tidak ada media")
        return

    img_count = 1

    for media in data["media_extended"]:

        # =====================
        # IMAGE
        # =====================
        if media["type"] == "image":

            img = media["url"] + "?name=orig"

            filename = f"{tweet_id}_{img_count}.jpg"

            path = os.path.join(IMAGE_DIR, filename)

            print("📸 Download:", filename)

            download_file(img, path)

            img_count += 1

        # =====================
        # VIDEO
        # =====================
        elif media["type"] == "video":

            m3u8 = media["url"]

            filename = f"{tweet_id}.mp4"

            path = os.path.join(VIDEO_DIR, filename)

            print("🎬 Download video:", filename)

            subprocess.run([
                "ffmpeg",
                "-loglevel", "error",
                "-y",
                "-i", m3u8,
                "-c", "copy",
                path
            ])


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