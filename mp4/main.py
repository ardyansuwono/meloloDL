import os
import requests
from urllib.parse import urlparse

DOWNLOAD_DIR = "downloads"
BULK_FILE = "bulk.txt"


def download_file(url):
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    filename = os.path.basename(urlparse(url).path)
    if not filename:
        filename = "video.mp4"

    filepath = os.path.join(DOWNLOAD_DIR, filename)

    print(f"\nDownloading: {filename}")

    try:
        with requests.get(url, stream=True) as r:
            r.raise_for_status()

            total_size = int(r.headers.get("content-length", 0))
            downloaded = 0
            chunk_size = 8192

            with open(filepath, "wb") as f:
                for chunk in r.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

                        if total_size > 0:
                            percent = downloaded * 100 / total_size
                            bar_length = 30
                            filled = int(bar_length * downloaded / total_size)
                            bar = "█" * filled + "-" * (bar_length - filled)

                            print(
                                f"\r[{bar}] {percent:5.1f}% ({downloaded}/{total_size} bytes)",
                                end="",
                                flush=True,
                            )

        print()

    except Exception as e:
        print("\nError:", e)
        return

    size = os.path.getsize(filepath)
    print(f"Ukuran file: {size} bytes")

    if size < 1000000:
        print("File terlalu kecil, kemungkinan bukan video.")
        return

    print(f"Selesai → {filepath}")


def single_download():
    url = input("Masukkan URL MP4: ").strip()
    if url:
        download_file(url)


def bulk_download():
    if not os.path.exists(BULK_FILE):
        print(f"File {BULK_FILE} tidak ditemukan.")
        return

    with open(BULK_FILE, "r") as f:
        urls = [line.strip() for line in f if line.strip()]

    if not urls:
        print("bulk.txt kosong.")
        return

    print(f"\nMenemukan {len(urls)} URL.\n")

    for i, url in enumerate(urls, 1):
        print(f"\n=== Download {i}/{len(urls)} ===")
        download_file(url)

    print("\nBulk download selesai.")


def main():
    while True:
        print("\n===== VIDEO DOWNLOADER =====")
        print("1. Single Download")
        print("2. Bulk Download (bulk.txt)")
        print("3. Keluar")

        choice = input("Pilih menu: ").strip()

        if choice == "1":
            single_download()
        elif choice == "2":
            bulk_download()
        elif choice == "3":
            print("Keluar.")
            break
        else:
            print("Pilihan tidak valid.")


if __name__ == "__main__":
    main()