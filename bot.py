import os
import logging
import asyncio

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import *
from extractor import extract_stream
from parser import parse_line
from db import insert_rows
from split_detect import find_archive_start
from state import save_state, load_state


# -------------------------
# Setup
# -------------------------

os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    filename="logs/bot.log",
    level=logging.INFO
)

app = Client(
    "exbot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workers=8  # faster downloads
)

user_files = {}
user_password = {}
await_password = {}


# -------------------------
# Progress bar
# -------------------------

def progress_bar(percent):

    filled = int(percent / 5)
    bar = "█" * filled + "░" * (20 - filled)

    return f"{bar} {percent:.1f}%"


# -------------------------
# Start
# -------------------------

@app.on_message(filters.command("start"))
async def start(client, message):

    if message.from_user.id != OWNER_ID:
        return

    await message.reply_text(
        "🤖 Exbot Ready\n\n"
        "Forward archive files\n"
        "When finished press Extract"
    )


# -------------------------
# Receive archive
# -------------------------

@app.on_message(filters.private & filters.document)
async def receive_file(client, message):

    if message.from_user.id != OWNER_ID:
        return

    doc = message.document
    uid = message.from_user.id

    path = os.path.join(DOWNLOAD_DIR, doc.file_name)

    msg = await message.reply_text("⬇️ Preparing download...")

    async def progress(current, total):

        percent = current * 100 / total

        text = f"""
⬇️ Downloading

{progress_bar(percent)}

{current//1024//1024} MB / {total//1024//1024} MB
"""

        try:
            await msg.edit_text(text)
        except:
            pass

    await message.download(
        file_name=path,
        progress=progress
    )

    if uid not in user_files:
        user_files[uid] = []

    user_files[uid].append(path)

    # Detect password from caption
    caption = message.caption or ""

    if "password" in caption.lower():
        try:
            pwd = caption.split(":")[-1].strip()
            user_password[uid] = pwd
        except:
            pass

    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("⚙ Extract", callback_data="extract")]]
    )

    await msg.edit_text(
        f"""✅ {doc.file_name} downloaded

Files ready: {len(user_files[uid])}

Send more files or press Extract""",
        reply_markup=keyboard
    )


# -------------------------
# Extract button
# -------------------------

@app.on_callback_query(filters.regex("extract"))
async def extract_button(client, callback):

    uid = callback.from_user.id
    message = callback.message

    if uid not in user_files:
        await message.reply_text("❌ No files uploaded")
        return

    if uid not in user_password:

        await message.reply_text(
            "🔐 Archive password required.\nSend password or type `none`"
        )

        await_password[uid] = True
        return

    files = sorted(user_files[uid])
    archive = find_archive_start(files)

    await message.edit_text("⚙ Starting extraction...")

    await run_import(message, archive, user_password.get(uid, ""))


# -------------------------
# Extract command
# -------------------------

@app.on_message(filters.command("extract"))
async def extract_cmd(client, message):

    uid = message.from_user.id

    if uid not in user_files:
        await message.reply_text("❌ No files uploaded")
        return

    if uid not in user_password:

        await message.reply_text(
            "🔐 Archive password required.\nSend password or type `none`"
        )

        await_password[uid] = True
        return

    files = sorted(user_files[uid])
    archive = find_archive_start(files)

    msg = await message.reply_text("⚙ Starting extraction...")

    await run_import(msg, archive, user_password.get(uid, ""))


# -------------------------
# Password input
# -------------------------

@app.on_message(filters.private & filters.text)
async def password_handler(client, message):

    uid = message.from_user.id

    if uid not in await_password:
        return

    pwd = message.text

    if pwd.lower() == "none":
        pwd = ""

    user_password[uid] = pwd
    await_password.pop(uid)

    files = sorted(user_files[uid])
    archive = find_archive_start(files)

    msg = await message.reply_text("⚙ Starting extraction...")

    await run_import(msg, archive, pwd)


# -------------------------
# Extraction + DB import
# -------------------------

async def run_import(message, archive, password=""):

    process = extract_stream(archive, password)

    batch = []
    processed = 0
    last_update = 0

    status = await message.reply_text("📦 Extracting archive...")

    resume_line = load_state()

    while True:

        line = process.stdout.readline()

        if not line:
            break

        processed += 1

        try:

            row = parse_line(line)

            if row:
                batch.append(row)

        except Exception as e:
            logging.error(e)

        if len(batch) >= BATCH_SIZE:

            insert_rows(batch)
            batch.clear()

        if processed - last_update > 50000:

            percent = min((processed / 180000000) * 100, 100)

            await status.edit_text(
                f"""
📦 Importing dataset

{progress_bar(percent)}

Rows processed: {processed:,}
"""
            )

            last_update = processed

    insert_rows(batch)

    await status.edit_text(
        f"""
✅ Import completed

Total rows processed: {processed:,}
"""
    )


print("EXBOT STARTED")

app.run()
