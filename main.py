import requests
import os
from tqdm import tqdm

API_URL = "https://tikwm.com/api/"

# lokasi folder script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# folder downloads
BASE_DOWNLOAD_FOLDER = os.path.join(BASE_DIR, "downloads")


def create_folder(path):
    os.makedirs(path, exist_ok=True)


def get_tiktok_data(url):
    params = {"url": url}

    try:
        response = requests.get(API_URL, params=params)

        if response.status_code != 200:
            print("❌ Gagal menghubungi API")
            return None

        data = response.json()

        if not data.get("data"):
            print("❌ Video tidak ditemukan")
            return None

        return data["data"]

    except Exception as e:
        print("❌ Error:", e)
        return None


def download_file(url, filepath):

    response = requests.get(url, stream=True)

    total_size = int(response.headers.get("content-length", 0))

    with open(filepath, "wb") as file, tqdm(
        desc=os.path.basename(filepath),
        total=total_size,
        unit="B",
        unit_scale=True,
        unit_divisor=1024,
    ) as bar:

        for chunk in response.iter_content(chunk_size=1024):

            if chunk:
                file.write(chunk)
                bar.update(len(chunk))


def download_video(data):

    video_folder = os.path.join(BASE_DOWNLOAD_FOLDER, "videos")

    create_folder(video_folder)

    video_url = data["play"]

    filename = f"{data['id']}_video.mp4"

    filepath = os.path.join(video_folder, filename)

    print("⬇️ Downloading video tanpa watermark...")

    download_file(video_url, filepath)

    print("✅ Video tersimpan di:", filepath)


def download_images(data):

    images = data.get("images")

    if not images:
        print("❌ Tidak ada gambar ditemukan")
        return

    images_folder = os.path.join(BASE_DOWNLOAD_FOLDER, "images")

    post_folder = os.path.join(images_folder, data["id"])

    create_folder(post_folder)

    print(f"⬇️ Downloading {len(images)} gambar...")

    for i, img_url in enumerate(images):

        filename = f"image_{i+1}.jpg"

        filepath = os.path.join(post_folder, filename)

        download_file(img_url, filepath)

    print("✅ Semua gambar tersimpan di:", post_folder)


def main():

    print("=== TikTok Downloader (Video + Photo Mode) ===")

    create_folder(BASE_DOWNLOAD_FOLDER)

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