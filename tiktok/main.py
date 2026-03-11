import os
import requests
from tqdm import tqdm
from TikTokApi import TikTokApi

API_URL = "https://tikwm.com/api/"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

VIDEO_DIR = os.path.join(BASE_DIR, "downloads", "videos")
IMAGE_DIR = os.path.join(BASE_DIR, "downloads", "images")

os.makedirs(VIDEO_DIR, exist_ok=True)
os.makedirs(IMAGE_DIR, exist_ok=True)


def download_file(url, filepath):

    r = requests.get(url, stream=True)

    total = int(r.headers.get("content-length", 0))

    with open(filepath, "wb") as f, tqdm(
        desc=os.path.basename(filepath),
        total=total,
        unit="B",
        unit_scale=True,
        unit_divisor=1024
    ) as bar:

        for chunk in r.iter_content(1024):

            if chunk:
                f.write(chunk)
                bar.update(len(chunk))


def get_tiktok_data(url):

    params = {"url": url}

    r = requests.get(API_URL, params=params)

    data = r.json()

    if not data.get("data"):
        print("Video tidak ditemukan")
        return None

    return data["data"]


def handle_download(data):

    # PHOTO MODE
    if data.get("images"):

        print("Photo mode terdeteksi")

        post_folder = os.path.join(IMAGE_DIR, data["id"])

        os.makedirs(post_folder, exist_ok=True)

        for i, img in enumerate(data["images"]):

            filepath = os.path.join(post_folder, f"image_{i+1}.jpg")

            download_file(img, filepath)

        print("Images saved:", post_folder)

    # VIDEO MODE
    else:

        video_url = data["play"]

        filename = f"{data['id']}.mp4"

        filepath = os.path.join(VIDEO_DIR, filename)

        print("Downloading video:", filename)

        download_file(video_url, filepath)

        print("Saved:", filepath)


def download_single():

    url = input("Masukkan URL TikTok: ")

    data = get_tiktok_data(url)

    if data:
        handle_download(data)


def download_multi():

    print("Masukkan beberapa URL (ketik 'done' untuk selesai)")

    links = []

    while True:

        link = input("URL: ")

        if link.lower() == "done":
            break

        links.append(link)

    for link in links:

        try:

            data = get_tiktok_data(link)

            if data:
                handle_download(data)

        except:
            print("Gagal:", link)


def download_bulk():

    file = input("Nama file txt: ")

    if not os.path.exists(file):
        print("File tidak ditemukan")
        return

    with open(file, "r") as f:
        links = f.read().splitlines()

    for link in links:

        try:

            data = get_tiktok_data(link)

            if data:
                handle_download(data)

        except:
            print("Gagal:", link)


def download_account():

    username = input("Masukkan username TikTok: ")

    print("Mengambil video dari akun:", username)

    with TikTokApi() as api:

        user = api.user(username=username)

        for video in user.videos(count=50):

            try:

                data = video.as_dict

                video_url = data["video"]["playAddr"]

                filename = f"{data['id']}.mp4"

                filepath = os.path.join(VIDEO_DIR, filename)

                download_file(video_url, filepath)

            except:
                pass


def menu():

    while True:

        print("""
==============================
 TIKTOK DOWNLOADER TOOL
==============================

1. Download Single URL
2. Download Multi URL
3. Grabbing Akun TikTok
4. Bulk Download (TXT)
5. Exit

""")

        choice = input("Pilih menu: ")

        if choice == "1":
            download_single()

        elif choice == "2":
            download_multi()

        elif choice == "3":
            download_account()

        elif choice == "4":
            download_bulk()

        elif choice == "5":
            print("Bye!")
            break

        else:
            print("Menu tidak valid")


if __name__ == "__main__":
    menu()