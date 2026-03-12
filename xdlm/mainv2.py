import os
import json
import time
import requests
import subprocess
from tqdm import tqdm

# ================================
# CONFIG
# ================================

BEARER = "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs=1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"

USER_BY_NAME_HASH = "pLsOiyHJ1eFwPJlNmLp4Bg"
USER_TWEETS_HASH = "5M8UuGym7_VyIEggQIyjxQ"

BASE = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE, "downloads")

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# ================================
# LOAD COOKIES
# ================================

def load_cookies(path="cookies.txt"):

    cookies = {}

    if not os.path.exists(path):
        return cookies

    with open(path, encoding="utf-8") as f:

        for line in f:

            if line.startswith("#") or not line.strip():
                continue

            parts = line.strip().split("\t")

            if len(parts) >= 7:
                cookies[parts[5]] = parts[6]

    return cookies


cookies = load_cookies()

# ================================
# SESSION
# ================================

session = requests.Session()
session.cookies.update(cookies)

HEADERS = {
    "authorization": f"Bearer {BEARER}",
    "x-csrf-token": cookies.get("ct0", ""),
    "x-twitter-active-user": "yes",
    "x-twitter-auth-type": "OAuth2Session",
    "User-Agent": "Mozilla/5.0"
}

session.headers.update(HEADERS)

# ================================
# DOWNLOAD FILE
# ================================

def download_file(url, path):

    r = session.get(url, stream=True)

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


# ================================
# MEDIA API
# ================================

def get_media(tweet_url):

    api = tweet_url.replace("x.com", "api.vxtwitter.com")

    r = session.get(api)

    try:
        return r.json()
    except:
        return None


def download_media(data, username):

    tweet_id = data.get("tweet_id")

    if not tweet_id:
        return

    folder = os.path.join(DOWNLOAD_DIR, username)
    os.makedirs(folder, exist_ok=True)

    if "media_extended" not in data:
        return

    count = 1

    for m in data["media_extended"]:

        if m["type"] == "image":

            url = m["url"] + "?name=orig"

            filename = f"{tweet_id}_{count}.jpg"
            path = os.path.join(folder, filename)

            if os.path.exists(path):
                continue

            print("📸", filename)

            download_file(url, path)

            count += 1

        elif m["type"] == "video":

            m3u8 = m["url"]

            filename = f"{tweet_id}.mp4"
            path = os.path.join(folder, filename)

            if os.path.exists(path):
                continue

            print("🎬", filename)

            subprocess.run([
                "ffmpeg",
                "-loglevel", "error",
                "-y",
                "-i", m3u8,
                "-c", "copy",
                path
            ])


# ================================
# GET USER ID
# ================================

def get_user_id(username):

    url = f"https://x.com/i/api/graphql/{USER_BY_NAME_HASH}/UserByScreenName"

    variables = {
        "screen_name": username,
        "withGrokTranslatedBio": False
    }

    params = {
        "variables": json.dumps(variables)
    }

    r = session.get(url, params=params)

    data = r.json()

    return data["data"]["user"]["result"]["rest_id"]


# ================================
# GET TWEETS
# ================================

def get_tweets(user_id):

    tweets = []
    seen = set()

    cursor = None
    last_cursor = None

    while True:

        url = f"https://x.com/i/api/graphql/{USER_TWEETS_HASH}/UserTweets"

        variables = {
            "userId": user_id,
            "count": 20,
            "includePromotedContent": True,
            "withVoice": True
        }

        if cursor:
            variables["cursor"] = cursor

        params = {
            "variables": json.dumps(variables)
        }

        r = session.get(url, params=params)

        time.sleep(2)

        try:
            data = r.json()
        except:
            print("Rate limit / response bukan JSON")
            break

        result = data.get("data", {}).get("user", {}).get("result", {})

        timeline = result.get("timeline_v2") or result.get("timeline")

        if not timeline:
            break

        instructions = timeline["timeline"]["instructions"]

        new_found = 0

        for ins in instructions:

            entries = ins.get("entries", [])

            for entry in entries:

                entry_id = entry.get("entryId", "")

                if entry_id.startswith("tweet-"):

                    tid = entry_id.split("-")[1]

                    if tid not in seen:
                        tweets.append(tid)
                        seen.add(tid)
                        new_found += 1

                if entry_id.startswith("cursor-bottom"):
                    cursor = entry["content"]["value"]

        print("Collected:", len(tweets))

        if not cursor:
            break

        if cursor == last_cursor:
            break

        if new_found == 0:
            break

        last_cursor = cursor

    return tweets


# ================================
# GRAB PROFILE -> TXT
# ================================

def grab_profile():

    username = input("Username X: ")

    username = username.replace("https://x.com/", "").replace("@", "")

    user_id = get_user_id(username)

    ids = get_tweets(user_id)

    if not ids:
        print("Tidak menemukan tweet")
        return

    filename = f"tweets_{username}.txt"

    with open(filename, "w") as f:

        for tid in ids:

            url = f"https://x.com/{username}/status/{tid}?s=20"

            f.write(url + "\n")

    print("\nTotal tweet:", len(ids))
    print("Disimpan ke:", filename)


# ================================
# SINGLE DOWNLOAD
# ================================

def single():

    url = input("URL: ")

    username = url.split("/")[3]

    data = get_media(url)

    if data and "media_extended" in data:

        download_media(data, username)


# ================================
# BULK DOWNLOAD TXT
# ================================

def bulk():

    file = input("Nama file txt: ")

    if not os.path.exists(file):
        print("File tidak ditemukan")
        return

    with open(file) as f:

        for url in f.read().splitlines():

            username = url.split("/")[3]

            data = get_media(url)

            if data and "media_extended" in data:

                download_media(data, username)

            time.sleep(1)


# ================================
# MENU
# ================================

def menu():

    while True:

        print("""
==============================
  X MEDIA DOWNLOADER
==============================

1. Download Single URL
2. Grab Semua Tweet Akun -> TXT
3. Bulk Download dari TXT
4. Exit
""")

        pilih = input("Pilih menu: ")

        if pilih == "1":
            single()

        elif pilih == "2":
            grab_profile()

        elif pilih == "3":
            bulk()

        elif pilih == "4":
            break


menu()