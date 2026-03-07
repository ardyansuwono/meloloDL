import requests
import os
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm

BASE = "https://api.sonzaix.indevs.in"

OUTPUT_DIR = "output"

THREADS = 12


os.makedirs(OUTPUT_DIR, exist_ok=True)


def clean_title(title):
    return re.sub(r'[\\/*?:"<>|]', "", title)


# SEARCH DRAMA
def search_drama(query):

    url = f"{BASE}/melolo/search?q={query}&result=10&page=1"

    res = requests.get(url).json()

    dramas = []

    for item in res["data"]:
        for book in item["books"]:
            dramas.append({
                "title": book["drama_name"],
                "id": book["drama_id"],
                "episodes": book["episode_count"]
            })

    return dramas


# GET EPISODES
def get_episode_list(drama_id):

    url = f"{BASE}/melolo/detail/{drama_id}"

    res = requests.get(url).json()

    return res["data"]["video_list"]


# GET STREAM URL
def get_video_url(video_id):

    url = f"{BASE}/melolo/stream/{video_id}"

    res = requests.get(url).json()

    qualities = res["data"]["qualities"]

    return qualities[-1]["url"]


# DOWNLOAD VIDEO
def download_video(ep, drama_folder):

    ep_num = ep["episode"]

    video_id = ep["video_id"]

    filename = os.path.join(drama_folder, f"ep{ep_num:03}.mp4")

    if os.path.exists(filename):
        return

    url = get_video_url(video_id)

    r = requests.get(url, stream=True)

    with open(filename, "wb") as f:

        for chunk in r.iter_content(1024 * 256):
            f.write(chunk)


# MULTI DOWNLOAD
def download_all(episodes, drama_folder):

    print("\nDownloading episodes...\n")

    with ThreadPoolExecutor(max_workers=THREADS) as exe:

        list(tqdm(
            exe.map(lambda ep: download_video(ep, drama_folder), episodes),
            total=len(episodes)
        ))


# MERGE VIDEO
def merge_videos(drama_folder, title):

    print("\nMerging video...\n")

    files = sorted([f for f in os.listdir(drama_folder) if f.startswith("ep")])

    list_file = os.path.join(drama_folder, "list.txt")

    with open(list_file, "w") as f:

        for file in files:
            f.write(f"file '{file}'\n")

    output_name = f"{title}.mp4"

    cmd = [
        "ffmpeg",
        "-loglevel", "error",
        "-fflags", "+genpts",
        "-f", "concat",
        "-safe", "0",
        "-i", "list.txt",
        "-c", "copy",
        "-reset_timestamps", "1",
        "-avoid_negative_ts", "make_zero",
        output_name
    ]

    subprocess.run(cmd, cwd=drama_folder)

    os.remove(list_file)

    print("Merge selesai")


# DELETE EPISODES
def cleanup(drama_folder):

    print("Cleaning temporary files...\n")

    for f in os.listdir(drama_folder):

        if f.startswith("ep") and f.endswith(".mp4"):

            os.remove(os.path.join(drama_folder, f))


def main():

    query = input("Cari drama: ")

    dramas = search_drama(query)

    print("\n=== HASIL ===\n")

    for i, d in enumerate(dramas):
        print(f"{i+1}. {d['title']} ({d['episodes']} episode)")

    choice = int(input("\nPilih: ")) - 1

    drama = dramas[choice]

    title = clean_title(drama["title"])

    drama_id = drama["id"]

    drama_folder = os.path.join(OUTPUT_DIR, title)

    os.makedirs(drama_folder, exist_ok=True)

    print("\nMengambil episode list...\n")

    episodes = get_episode_list(drama_id)

    print(f"Total episode: {len(episodes)}")

    download_all(episodes, drama_folder)

    merge_videos(drama_folder, title)

    cleanup(drama_folder)

    print("\nSelesai!")

    print(f"\nVideo final:\n{drama_folder}/{title}.mp4")


if __name__ == "__main__":
    main()