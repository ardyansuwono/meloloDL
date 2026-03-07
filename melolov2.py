import requests
import os
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm

BASE = "https://api.sonzaix.indevs.in"

OUTPUT_DIR = "output"
THREADS = 8

os.makedirs(OUTPUT_DIR, exist_ok=True)


def clean_title(title):
    return re.sub(r'[\\/*?:"<>|]', "", title)


###########################################################
# MELOLO
###########################################################

def search_melolo(query):

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


def melolo_episode_list(drama_id):

    url = f"{BASE}/melolo/detail/{drama_id}"
    res = requests.get(url).json()

    return res["data"]["video_list"]


def melolo_stream(video_id):

    url = f"{BASE}/melolo/stream/{video_id}"
    res = requests.get(url).json()

    qualities = res["data"]["qualities"]

    best = qualities[-1]

    return best["url"]


def download_melolo(ep, drama_folder):

    ep_num = ep["episode"]
    video_id = ep["video_id"]

    filename = os.path.join(drama_folder, f"ep{ep_num:03}.mp4")

    if os.path.exists(filename):
        return

    url = melolo_stream(video_id)

    r = requests.get(url, stream=True)

    with open(filename, "wb") as f:

        for chunk in r.iter_content(1024 * 256):
            f.write(chunk)


###########################################################
# DRAMABOX
###########################################################

def search_dramabox(query):

    url = f"{BASE}/dramabox/search?q={query}&result=10&page=1"
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


def dramabox_episode_list(drama_id):

    url = f"{BASE}/dramabox/detail/{drama_id}"
    res = requests.get(url).json()

    return res["data"]["chapterList"]


def dramabox_stream(drama_id, episode_index):

    url = f"{BASE}/dramabox/stream?dramaId={drama_id}&episodeIndex={episode_index}"

    for _ in range(5):

        try:

            res = requests.get(url, timeout=10).json()

            if "data" not in res:
                continue

            qualities = res["data"]["qualities"]

            best = max(qualities, key=lambda x: x["quality"])

            return best["videoPath"]

        except:
            pass

    return None


def download_dramabox(ep, drama_id, drama_folder):

    ep_index = ep["chapterIndex"] + 1

    filename = os.path.join(drama_folder, f"ep{ep_index:03}.mp4")

    if os.path.exists(filename):
        return

    video_url = dramabox_stream(drama_id, ep_index)

    if not video_url:
        print(f"Episode {ep_index} gagal ambil stream")
        return

    r = requests.get(video_url, stream=True)

    with open(filename, "wb") as f:

        for chunk in r.iter_content(1024 * 256):
            f.write(chunk)


###########################################################
# DOWNLOAD ENGINE
###########################################################

def download_all(episodes, drama_folder, provider, drama_id):

    print("\nDownloading episodes...\n")

    if provider == "melolo":

        with ThreadPoolExecutor(max_workers=THREADS) as exe:

            list(tqdm(
                exe.map(lambda ep: download_melolo(ep, drama_folder), episodes),
                total=len(episodes)
            ))

    else:

        with ThreadPoolExecutor(max_workers=THREADS) as exe:

            list(tqdm(
                exe.map(lambda ep: download_dramabox(ep, drama_id, drama_folder), episodes),
                total=len(episodes)
            ))


###########################################################
# MERGE
###########################################################

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


###########################################################
# CLEANUP
###########################################################

def cleanup(drama_folder):

    print("Cleaning episode files...\n")

    for f in os.listdir(drama_folder):

        if f.startswith("ep") and f.endswith(".mp4"):

            os.remove(os.path.join(drama_folder, f))


###########################################################
# MAIN
###########################################################

def main():

    print("\nSelect Source:")
    print("1. Melolo")
    print("2. DramaBox")

    source = input("\nChoice: ")

    query = input("\nSearch drama: ")

    if source == "1":

        provider = "melolo"
        dramas = search_melolo(query)

    else:

        provider = "dramabox"
        dramas = search_dramabox(query)

    print("\nResults:\n")

    for i, d in enumerate(dramas):

        print(f"{i+1}. {d['title']}")

    choice = int(input("\nSelect drama: ")) - 1

    drama = dramas[choice]

    title = clean_title(drama["title"])
    drama_id = drama["id"]

    drama_folder = os.path.join(OUTPUT_DIR, title)

    os.makedirs(drama_folder, exist_ok=True)

    print("\nFetching episode list...\n")

    if provider == "melolo":
        episodes = melolo_episode_list(drama_id)
    else:
        episodes = dramabox_episode_list(drama_id)

    print(f"Total episode: {len(episodes)}")

    download_all(episodes, drama_folder, provider, drama_id)

    merge_videos(drama_folder, title)

    cleanup(drama_folder)

    print("\nFinished!")

    print(f"\nFinal video:\n{drama_folder}/{title}.mp4")


if __name__ == "__main__":
    main()