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
USER_MEDIA_HASH = "U1Zgdsu2qjBi8JF74lTmJQ"

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
# GRAPHQL PARAMS
# ================================

FEATURES = {
    "rweb_video_screen_enabled": False,
    "profile_label_improvements_pcf_label_in_post_enabled": True,
    "responsive_web_profile_redirect_enabled": False,
    "rweb_tipjar_consumption_enabled": False,
    "verified_phone_label_enabled": False,
    "creator_subscriptions_tweet_preview_api_enabled": True,
    "responsive_web_graphql_timeline_navigation_enabled": True,
    "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
    "premium_content_api_read_enabled": False,
    "communities_web_enable_tweet_community_results_fetch": True,
    "c9s_tweet_anatomy_moderator_badge_enabled": True,
    "responsive_web_grok_analyze_button_fetch_trends_enabled": False,
    "responsive_web_grok_analyze_post_followups_enabled": True,
    "responsive_web_jetfuel_frame": True,
    "responsive_web_grok_share_attachment_enabled": True,
    "responsive_web_grok_annotations_enabled": True,
    "articles_preview_enabled": True,
    "responsive_web_edit_tweet_api_enabled": True,
    "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
    "view_counts_everywhere_api_enabled": True,
    "longform_notetweets_consumption_enabled": True,
    "responsive_web_twitter_article_tweet_consumption_enabled": True,
    "tweet_awards_web_tipping_enabled": False,
    "content_disclosure_indicator_enabled": True,
    "content_disclosure_ai_generated_indicator_enabled": True,
    "responsive_web_grok_show_grok_translated_post": False,
    "responsive_web_grok_analysis_button_from_backend": True,
    "post_ctas_fetch_enabled": False,
    "freedom_of_speech_not_reach_fetch_enabled": True,
    "standardized_nudges_misinfo": True,
    "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
    "longform_notetweets_rich_text_read_enabled": True,
    "longform_notetweets_inline_media_enabled": False,
    "responsive_web_grok_image_annotation_enabled": True,
    "responsive_web_grok_imagine_annotation_enabled": True,
    "responsive_web_grok_community_note_auto_translation_is_enabled": False,
    "responsive_web_enhance_cards_enabled": False
}

FIELD_TOGGLES = {
    "withArticlePlainText": False
}

# ================================
# UTIL
# ================================

def safe_get_json(resp):
    try:
        return resp.json()
    except Exception:
        return None


def normalize_username(username):
    return (
        username.replace("https://x.com/", "")
        .replace("http://x.com/", "")
        .replace("@", "")
        .strip("/")
        .strip()
    )


def pick_best_video_variant(variants):
    mp4_variants = [
        v for v in variants
        if v.get("content_type") == "video/mp4" and v.get("url")
    ]
    if not mp4_variants:
        return None
    return max(mp4_variants, key=lambda x: x.get("bitrate", 0))


def has_media_in_tweet_result(tweet_result):
    legacy = tweet_result.get("legacy", {})
    return (
        "extended_entities" in legacy or
        ("entities" in legacy and "media" in legacy["entities"])
    )

# ================================
# DOWNLOAD
# ================================

def download_file(url, path):
    r = session.get(url, stream=True, timeout=60)
    r.raise_for_status()

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
# VXTWITTER FALLBACK
# ================================

def get_media(tweet_url):
    api = tweet_url.replace("x.com", "api.vxtwitter.com")
    r = session.get(api, timeout=30)
    return safe_get_json(r)


def download_media_vx(data, username):
    tweet_id = data.get("tweet_id")
    if not tweet_id:
        return False

    folder = os.path.join(DOWNLOAD_DIR, username)
    os.makedirs(folder, exist_ok=True)

    media_extended = data.get("media_extended", [])
    if not media_extended:
        return False

    count = 1
    downloaded_any = False

    for m in media_extended:
        if m.get("type") == "image":
            url = m.get("url")
            if not url:
                continue

            url = url + "?name=orig"
            filename = f"{tweet_id}_{count}.jpg"
            path = os.path.join(folder, filename)

            if not os.path.exists(path):
                print("📸", filename)
                download_file(url, path)
                downloaded_any = True

            count += 1

        elif m.get("type") == "video":
            m3u8 = m.get("url")
            if not m3u8:
                continue

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
            downloaded_any = True

    return downloaded_any

# ================================
# PARSE MEDIA
# ================================

def parse_media_from_tweet_result(tweet_result):
    media_list = []

    legacy = tweet_result.get("legacy", {})
    extended = legacy.get("extended_entities", {})
    media_items = extended.get("media", [])

    for media in media_items:
        mtype = media.get("type")

        if mtype == "photo":
            url = media.get("media_url_https")
            if url:
                media_list.append({
                    "type": "image",
                    "url": url + "?name=orig"
                })

        elif mtype in ("video", "animated_gif"):
            video_info = media.get("video_info", {})
            variants = video_info.get("variants", [])

            best = pick_best_video_variant(variants)
            if best and best.get("url"):
                media_list.append({
                    "type": "video",
                    "url": best["url"]
                })
            else:
                m3u8 = next(
                    (
                        v.get("url")
                        for v in variants
                        if v.get("content_type") == "application/x-mpegURL"
                    ),
                    None
                )
                if m3u8:
                    media_list.append({
                        "type": "video_m3u8",
                        "url": m3u8
                    })

    return media_list


def download_parsed_media(tweet_id, media_list, username):
    if not media_list:
        return False

    folder = os.path.join(DOWNLOAD_DIR, username)
    os.makedirs(folder, exist_ok=True)

    count = 1
    downloaded_any = False

    for media in media_list:
        mtype = media["type"]
        url = media["url"]

        if mtype == "image":
            filename = f"{tweet_id}_{count}.jpg"
            path = os.path.join(folder, filename)

            if not os.path.exists(path):
                print("📸", filename)
                download_file(url, path)
                downloaded_any = True

            count += 1

        elif mtype == "video":
            filename = f"{tweet_id}.mp4"
            path = os.path.join(folder, filename)

            if os.path.exists(path):
                continue

            print("🎬", filename)
            download_file(url, path)
            downloaded_any = True

        elif mtype == "video_m3u8":
            filename = f"{tweet_id}.mp4"
            path = os.path.join(folder, filename)

            if os.path.exists(path):
                continue

            print("🎬", filename)
            subprocess.run([
                "ffmpeg",
                "-loglevel", "error",
                "-y",
                "-i", url,
                "-c", "copy",
                path
            ])
            downloaded_any = True

    return downloaded_any

# ================================
# GRAPHQL
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

    r = session.get(url, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()
    return data["data"]["user"]["result"]["rest_id"]

# ================================
# TIMELINE WALKER
# ================================

def iter_instruction_entries(data):
    result = data.get("data", {}).get("user", {}).get("result", {})
    timeline = result.get("timeline_v2") or result.get("timeline")

    if not timeline:
        return []

    instructions = timeline.get("timeline", {}).get("instructions", [])
    all_entries = []

    for ins in instructions:
        # bentuk biasa
        if "entries" in ins:
            for entry in ins.get("entries", []):
                all_entries.append(entry)

        # bentuk tunggal
        if "entry" in ins and isinstance(ins.get("entry"), dict):
            all_entries.append(ins["entry"])

        # bentuk media grid lanjutan
        if "moduleItems" in ins:
            for module_item in ins.get("moduleItems", []):
                all_entries.append(module_item)

    return all_entries


def extract_tweet_result_candidates_from_entry(entry):
    candidates = []

    # bentuk moduleItems item
    tweet_result = (
        entry.get("item", {})
        .get("itemContent", {})
        .get("tweet_results", {})
        .get("result", {})
    )
    if tweet_result:
        candidates.append(tweet_result)

    # bentuk entry biasa
    content = entry.get("content", {})

    tweet_result = (
        content.get("itemContent", {})
        .get("tweet_results", {})
        .get("result", {})
    )
    if tweet_result:
        candidates.append(tweet_result)

    # bentuk TimelineTimelineModule
    if content.get("__typename") == "TimelineTimelineModule":
        for item in content.get("items", []):
            tweet_result = (
                item.get("item", {})
                .get("itemContent", {})
                .get("tweet_results", {})
                .get("result", {})
            )
            if tweet_result:
                candidates.append(tweet_result)

    return candidates


def extract_cursor_from_entry(entry):
    entry_id = entry.get("entryId", "")
    content = entry.get("content", {})

    if entry_id.startswith("cursor-bottom"):
        return content.get("value")

    if content.get("__typename") == "TimelineTimelineCursor":
        if content.get("cursorType") == "Bottom":
            return content.get("value")

    return None


def extract_bottom_cursor_from_instructions(data):
    result = data.get("data", {}).get("user", {}).get("result", {})
    timeline = result.get("timeline_v2") or result.get("timeline")

    if not timeline:
        return None

    instructions = timeline.get("timeline", {}).get("instructions", [])

    for ins in instructions:
        if "entries" in ins:
            for entry in ins.get("entries", []):
                cursor = extract_cursor_from_entry(entry)
                if cursor:
                    return cursor

    return None


def extract_tweet_ids_from_timeline(data, seen):
    tweets = []

    entries = iter_instruction_entries(data)
    cursor = extract_bottom_cursor_from_instructions(data)

    for entry in entries:
        for tweet_result in extract_tweet_result_candidates_from_entry(entry):
            tid = tweet_result.get("rest_id")
            if tid and has_media_in_tweet_result(tweet_result) and tid not in seen:
                tweets.append(tid)
                seen.add(tid)

        entry_id = entry.get("entryId", "")
        if "tweet-" in entry_id:
            tid = entry_id.split("tweet-")[-1]
            tid = tid.split("-")[0] if "-" in tid else tid

            if tid.isdigit() and tid not in seen:
                tweets.append(tid)
                seen.add(tid)

    return tweets, cursor


def extract_media_map_from_timeline(data, media_map):
    entries = iter_instruction_entries(data)

    for entry in entries:
        for tweet_result in extract_tweet_result_candidates_from_entry(entry):
            tid = tweet_result.get("rest_id")
            if not tid:
                continue

            parsed = parse_media_from_tweet_result(tweet_result)
            if parsed:
                media_map[tid] = parsed

    return media_map

# ================================
# GET ALL TWEETS
# ================================

def get_tweets(user_id):
    tweets = []
    seen = set()

    cursor = None
    last_cursor = None
    same_cursor_count = 0
    empty_page_count = 0
    page = 0

    while True:
        page += 1

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

        r = session.get(url, params=params, timeout=30)
        time.sleep(2)

        data = safe_get_json(r)
        if not data:
            print("Rate limit / response bukan JSON")
            break

        new_ids, new_cursor = extract_tweet_ids_from_timeline(data, seen)
        tweets.extend(new_ids)

        print(f"Page {page} | +{len(new_ids)} | total={len(tweets)} | cursor={new_cursor}")

        if not new_cursor:
            print("Cursor habis")
            break

        if new_cursor == last_cursor:
            same_cursor_count += 1
        else:
            same_cursor_count = 0

        if len(new_ids) == 0:
            empty_page_count += 1
        else:
            empty_page_count = 0

        if same_cursor_count >= 2:
            print("Cursor tidak berubah terus, stop")
            break

        if empty_page_count >= 3:
            print("3 halaman berturut-turut kosong, stop")
            break

        last_cursor = new_cursor
        cursor = new_cursor

    return tweets

# ================================
# GET MEDIA TWEETS
# ================================

def get_media_tweets(user_id, return_media_map=False):
    tweets = []
    seen = set()
    media_map = {}

    cursor = None
    last_cursor = None
    same_cursor_count = 0
    empty_page_count = 0
    page = 0

    while True:
        page += 1

        url = f"https://x.com/i/api/graphql/{USER_MEDIA_HASH}/UserMedia"

        variables = {
            "userId": user_id,
            "count": 20,
            "includePromotedContent": False,
            "withClientEventToken": False,
            "withBirdwatchNotes": False,
            "withVoice": True
        }

        if cursor:
            variables["cursor"] = cursor

        params = {
            "variables": json.dumps(variables),
            "features": json.dumps(FEATURES),
            "fieldToggles": json.dumps(FIELD_TOGGLES)
        }

        r = session.get(url, params=params, timeout=30)
        time.sleep(2)

        data = safe_get_json(r)
        if not data:
            print("Rate limit / response bukan JSON")
            break

        new_ids, new_cursor = extract_tweet_ids_from_timeline(data, seen)
        tweets.extend(new_ids)
        extract_media_map_from_timeline(data, media_map)

        print(f"Page {page} | +{len(new_ids)} | total={len(tweets)} | cursor={new_cursor}")

        if len(new_ids) == 0:
            print("DEBUG: halaman ini tidak menghasilkan ID baru")
            try:
                result = data.get("data", {}).get("user", {}).get("result", {})
                timeline = result.get("timeline_v2") or result.get("timeline")
                instructions = timeline.get("timeline", {}).get("instructions", [])
                print("Jumlah instructions:", len(instructions))
                print(json.dumps(data, indent=2)[:2500])
            except Exception:
                pass

        if not new_cursor:
            print("Cursor habis")
            break

        if new_cursor == last_cursor:
            same_cursor_count += 1
        else:
            same_cursor_count = 0

        if len(new_ids) == 0:
            empty_page_count += 1
        else:
            empty_page_count = 0

        if same_cursor_count >= 2:
            print("Cursor tidak berubah terus, stop")
            break

        if empty_page_count >= 3:
            print("3 halaman berturut-turut kosong, stop")
            break

        last_cursor = new_cursor
        cursor = new_cursor

    if return_media_map:
        return tweets, media_map

    return tweets

# ================================
# ACTIONS
# ================================

def grab_profile():
    username = input("Username X: ")
    username = normalize_username(username)

    user_id = get_user_id(username)
    ids = get_tweets(user_id)

    if not ids:
        print("Tidak menemukan tweet")
        return

    filename = f"tweets_{username}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        for tid in ids:
            f.write(f"https://x.com/{username}/status/{tid}?s=20\n")

    print("\nTotal tweet:", len(ids))
    print("Disimpan ke:", filename)


def grab_profile_media_only():
    username = input("Username X: ")
    username = normalize_username(username)

    user_id = get_user_id(username)
    ids = get_media_tweets(user_id)

    if not ids:
        print("Tidak menemukan postingan media")
        return

    filename = f"media_tweets_{username}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        for tid in ids:
            f.write(f"https://x.com/{username}/status/{tid}?s=20\n")

    print("\nTotal postingan media:", len(ids))
    print("Disimpan ke:", filename)


def bulk_media_from_profile():
    username = input("Username X: ")
    username = normalize_username(username)

    user_id = get_user_id(username)
    ids, media_map = get_media_tweets(user_id, return_media_map=True)

    if not ids:
        print("Tidak menemukan postingan media")
        return

    print(f"\nTotal postingan media ditemukan: {len(ids)}")
    print("Mulai download...")

    downloaded = 0

    for tid in ids:
        media_list = media_map.get(tid, [])

        if media_list:
            ok = download_parsed_media(tid, media_list, username)
            if ok:
                downloaded += 1
        else:
            tweet_url = f"https://x.com/{username}/status/{tid}?s=20"
            data = get_media(tweet_url)
            if data and "media_extended" in data:
                ok = download_media_vx(data, username)
                if ok:
                    downloaded += 1

        time.sleep(1)

    print(f"\nSelesai. Total tweet media yang diproses: {len(ids)}")
    print(f"Berhasil download dari: {downloaded} tweet")


def single():
    url = input("URL: ").strip()

    try:
        username = url.split("/")[3]
    except Exception:
        print("URL tidak valid")
        return

    data = get_media(url)
    if data and "media_extended" in data:
        if download_media_vx(data, username):
            return

    print("Media tidak ditemukan / fallback gagal")


def bulk():
    file = input("Nama file txt: ").strip()

    if not os.path.exists(file):
        print("File tidak ditemukan")
        return

    with open(file, encoding="utf-8") as f:
        for url in f.read().splitlines():
            url = url.strip()
            if not url:
                continue

            try:
                username = url.split("/")[3]
            except Exception:
                print("Skip URL invalid:", url)
                continue

            data = get_media(url)
            if data and "media_extended" in data:
                download_media_vx(data, username)
            else:
                print("Skip, media tidak ditemukan:", url)

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
4. Grab Tweet Media Saja -> TXT
5. Grab + Download Media Akun Langsung
6. Exit
""")

        pilih = input("Pilih menu: ").strip()

        if pilih == "1":
            single()
        elif pilih == "2":
            grab_profile()
        elif pilih == "3":
            bulk()
        elif pilih == "4":
            grab_profile_media_only()
        elif pilih == "5":
            bulk_media_from_profile()
        elif pilih == "6":
            break
        else:
            print("Menu tidak valid")


if __name__ == "__main__":
    menu()