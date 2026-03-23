import os
import re
import requests
from urllib.parse import urlparse

DOWNLOAD_DIR = "downloads"
BULK_FILE = "bulk.txt"


def extract_mp4(url):
    print("Mencari video source...")

    r = requests.get(url, allow_redirects=True)
    html = r.text

    match = re.search(r'https://cdn\d+\.videy\.co/[a-zA-Z0-9]+\.mp4', html)

    if match:
        video_url = match.group(0)
        print("Video ditemukan:", video_url)
        return video_url
    else:
        print("Tidak menemukan link MP4.")
        return None


def download_file(url):
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    filename = os.path.basename(urlparse(url).path)

    # Jika tidak ada ekstensi mp4, tambahkan
    if not filename.lower().endswith(".mp4"):
        filename += ".mp4"

    filepath = os.path.join(DOWNLOAD_DIR, filename)

    print(f"\nDownloading: {filename}")

    r = requests.get(url, stream=True)
    total = int(r.headers.get('content-length', 0))
    downloaded = 0

    with open(filepath, "wb") as f:
        for chunk in r.iter_content(8192):
            if chunk:
                f.write(chunk)
                downloaded += len(chunk)

                if total > 0:
                    percent = downloaded * 100 / total
                    bar = int(30 * downloaded / total)
                    print(
                        f"\r[{'█'*bar}{'-'*(30-bar)}] {percent:.1f}%",
                        end=""
                    )

    print("\nSelesai:", filepath)


def single_download():
    url = input("Masukkan URL: ").strip()

    if "vidays.de" in url:
        url = extract_mp4(url)

    if url:
        download_file(url)


def bulk_download():

    if not os.path.exists(BULK_FILE):
        print("bulk.txt tidak ditemukan.")
        return

    with open(BULK_FILE) as f:
        urls = [line.strip() for line in f if line.strip()]

    print(f"{len(urls)} URL ditemukan\n")

    for i, url in enumerate(urls, 1):

        print(f"\n=== {i}/{len(urls)} ===")

        if "vidays.de" in url:
            url = extract_mp4(url)

        if url:
            download_file(url)


def main():

    while True:

        print("\n===== VIDEO DOWNLOADER =====")
        print("1. Single Download")
        print("2. Bulk Download")
        print("3. Keluar")

        choice = input("Pilih: ")

        if choice == "1":
            single_download()

        elif choice == "2":
            bulk_download()

        elif choice == "3":
            break


if __name__ == "__main__":
    main()