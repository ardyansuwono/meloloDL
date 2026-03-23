import requests
import re
import subprocess
import os
from urllib.parse import urlparse

HEADERS = {"User-Agent": "Mozilla/5.0"}

DOWNLOAD_DIR = "downloads"


def extract_title_from_url(url):
    path = urlparse(url).path
    return path.split("/")[-1]


def get_m3u8(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        html = r.text

        match = re.search(r'https://[^"\']+\.m3u8[^"\']*', html)

        if match:
            return match.group(0)

        return None

    except Exception as e:
        print("Error:", e)
        return None


def get_duration(m3u8):
    try:
        cmd = [
            "ffprobe",
            "-i", m3u8,
            "-show_entries",
            "format=duration",
            "-v", "quiet",
            "-of",
            "csv=p=0"
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        return float(result.stdout.strip())

    except:
        return None


def download_m3u8(m3u8_url, filename):

    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    output = os.path.join(DOWNLOAD_DIR, filename + ".mp4")

    duration = get_duration(m3u8_url)

    cmd = [
        "ffmpeg",
        "-i", m3u8_url,
        "-c", "copy",
        "-bsf:a", "aac_adtstoasc",
        "-progress", "pipe:1",
        "-loglevel", "error",
        output
    ]

    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    for line in process.stdout:

        if "out_time_ms=" in line and duration:

            out_time_ms = int(line.split("=")[1])
            current_time = out_time_ms / 1000000

            percent = (current_time / duration) * 100

            print(f"\r📥 Downloading: {percent:.2f}% ", end="")

    process.wait()

    print(f"\n✅ Selesai: {output}")


def process_single():

    url = input("Masukkan URL video:\n> ")

    print("🔎 Mencari m3u8...")

    m3u8 = get_m3u8(url)

    if not m3u8:
        print("❌ m3u8 tidak ditemukan")
        return

    filename = extract_title_from_url(url)

    print("Nama file:", filename)

    download_m3u8(m3u8, filename)


def process_bulk():

    file_path = input("Masukkan path file txt:\n> ")

    if not os.path.exists(file_path):
        print("File tidak ditemukan")
        return

    with open(file_path) as f:
        urls = [line.strip() for line in f if line.strip()]

    for i, url in enumerate(urls, 1):

        print(f"\n[{i}/{len(urls)}] Processing")

        m3u8 = get_m3u8(url)

        if not m3u8:
            print("❌ m3u8 tidak ditemukan")
            continue

        filename = extract_title_from_url(url)

        download_m3u8(m3u8, filename)


def menu():

    while True:

        print("\n=== M3U8 Downloader ===")
        print("1. Single URL")
        print("2. Bulk TXT")
        print("0. Exit")

        choice = input("> ")

        if choice == "1":
            process_single()

        elif choice == "2":
            process_bulk()

        elif choice == "0":
            break

        else:
            print("Pilihan tidak valid")


if __name__ == "__main__":
    menu()