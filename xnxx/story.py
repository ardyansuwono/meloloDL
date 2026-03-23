import requests
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
from tqdm import tqdm
import re
import html
import os
import google.generativeai as genai


# =========================
# GEMINI SETUP
# =========================

API_KEY = os.getenv("GEMINI_API_KEY")

USE_GEMINI = False

if API_KEY:
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel("gemini-3.0-flash")
    USE_GEMINI = True


# =========================
# CLEAN TEXT
# =========================

def clean_text(text):

    text = html.unescape(text)

    text = re.sub(r"\s+", " ", text)

    text = text.replace(" .", ".")
    text = text.replace(" ,", ",")

    return text.strip()


# =========================
# SCRAPE STORY
# =========================

def scrape_story(url):

    headers = {"User-Agent": "Mozilla/5.0"}

    response = requests.get(url, headers=headers)

    soup = BeautifulSoup(response.text, "html.parser")

    panels = soup.find_all("div", class_="block_panel")

    if len(panels) < 2:
        print("❌ Isi cerita tidak ditemukan.")
        return None, None

    title = soup.find("h2").text.strip()

    story_panel = panels[1]

    story_text = story_panel.get_text("\n")

    story_text = story_text.split("Read")[0]

    paragraphs = [
        clean_text(p)
        for p in story_text.split("\n")
        if p.strip()
    ]

    return title, paragraphs


# =========================
# GOOGLE TRANSLATE
# =========================

def translate_story(paragraphs):

    translator = GoogleTranslator(source="auto", target="id")

    translated = []

    print("\n🔄 Menerjemahkan cerita...\n")

    for p in tqdm(paragraphs, desc="Progress", unit="paragraph"):

        try:
            translated.append(clean_text(translator.translate(p)))
        except:
            translated.append(p)

    return translated


# =========================
# GEMINI REWRITE
# =========================

def rewrite_gemini(text):

    if not USE_GEMINI:
        return text

    print("\n✨ Menulis ulang dengan Gemini (bahasa santai)...\n")

    prompt = f"""
Ubah teks berikut menjadi bahasa Indonesia santai seperti cerita novel.
Gunakan bahasa natural dan tidak terlalu formal.

TEXT:
{text}
"""

    try:

        response = model.generate_content(prompt)

        return response.text

    except Exception as e:

        print("⚠️ Gemini gagal digunakan:", e)

        return text


# =========================
# SAVE TXT
# =========================

def save_story(title, text):

    filename = re.sub(r"[^\w\s-]", "", title)

    filename = filename.replace(" ", "_") + ".txt"

    with open(filename, "w", encoding="utf-8") as f:
        f.write(text)

    print("\n================================")
    print("✅ File berhasil disimpan:", filename)
    print("================================\n")


# =========================
# PROCESS SINGLE URL
# =========================

def process_url(url, rewrite=False):

    print("\n📥 Mengambil cerita...")

    title, paragraphs = scrape_story(url)

    if not paragraphs:
        return

    translated = translate_story(paragraphs)

    final_text = "\n\n".join(translated)

    if rewrite:
        final_text = rewrite_gemini(final_text)

    save_story(title, final_text)


# =========================
# MULTIPLE URL
# =========================

def process_multiple(rewrite=False):

    urls = input(
        "\nMasukkan banyak URL (pisahkan dengan koma):\n> "
    ).split(",")

    for url in urls:

        url = url.strip()

        if not url:
            continue

        print("\n==============================")
        print("Memproses:", url)
        print("==============================")

        process_url(url, rewrite)


# =========================
# CLI MENU
# =========================

def main():

    while True:

        print("\n===== STORY TRANSLATOR CLI =====")
        print("1. Translate URL")
        print("2. Translate banyak URL")
        print("3. Translate + Gemini rewrite")
        print("4. Keluar")

        choice = input("\nPilih menu: ")

        if choice == "1":

            url = input("\nMasukkan URL cerita:\n> ")

            process_url(url, rewrite=False)

        elif choice == "2":

            process_multiple(rewrite=False)

        elif choice == "3":

            url = input("\nMasukkan URL cerita:\n> ")

            process_url(url, rewrite=True)

        elif choice == "4":

            print("Keluar...")
            break

        else:

            print("Pilihan tidak valid.")


# =========================

if __name__ == "__main__":
    main()