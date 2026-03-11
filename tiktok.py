import requests
import os
from tqdm import tqdm

API_URL = "https://tikwm.com/api/"

# lokasi script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# folder download
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")


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


def download_video(data):

    video_folder = os.path.join(DOWNLOAD_DIR, "videos")

    os.makedirs(video_folder, exist_ok=True)

    video_url = data["play"]

    filename = f"{data['id']}.mp4"

    filepath = os.path.join(video_folder, filename)

    print("Download video tanpa watermark...")

    download_file(video_url, filepath)

    print("Saved:", filepath)


def download_images(data):

    images = data.get("images")

    if not images:
        return

    post_folder = os.path.join(DOWNLOAD_DIR, "images", data["id"])

    os.makedirs(post_folder, exist_ok=True)

    for i, img in enumerate(images):

        filepath = os.path.join(post_folder, f"image_{i+1}.jpg")

        download_file(img, filepath)

    print("Images saved in:", post_folder)


def main():

    print("=== TikTok Downloader ===")

    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    url = input("Masukkan URL TikTok: ")

    data = get_tiktok_data(url)

    if not data:
        return

    if data.get("images"):
        download_images(data)
    else:
        download_video(data)


if __name__ == "__main__":
    main()