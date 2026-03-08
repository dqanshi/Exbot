import os
import logging
import time

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import *
from extractor import extract_stream, extract_to_disk
from parser import parse_line
from db import insert_rows
from split_detect import find_archive_start


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
    workers=16
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

@app.on_message(filters.command("dex") & filters.private)
async def dex_cmd(client, message):

    if message.from_user.id != OWNER_ID:
        return

    parts = message.text.split(maxsplit=1)

    password = ""

    if len(parts) > 1:
        password = parts[1].strip()

    files = []

    for f in os.listdir(DOWNLOAD_DIR):
        if ".7z" in f:
            files.append(os.path.join(DOWNLOAD_DIR, f))

    if not files:
        await message.reply_text("❌ No archive files found")
        return

    files.sort()

    archive = find_archive_start(files)

    msg = await message.reply_text("⚙ Starting extraction...")

    await run_import(msg, archive, password)
    
    
# -------------------------
# Receive file
# -------------------------

@app.on_message(filters.private & filters.document)
async def receive_file(client, message):

    if message.from_user.id != OWNER_ID:
        return

    doc = message.document
    uid = message.from_user.id

    path = os.path.join(DOWNLOAD_DIR, doc.file_name)

    msg = await message.reply_text("⬇️ Preparing download...")

    start_time = time.time()

    async def progress(current, total):

        elapsed = time.time() - start_time
        speed = current / elapsed / 1024 / 1024 if elapsed > 0 else 0
        percent = current * 100 / total

        text = f"""
⬇️ Downloading

{progress_bar(percent)}

{current//1024//1024} MB / {total//1024//1024} MB
⚡ {speed:.2f} MB/s
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

    if uid not in user_files:
        await callback.message.reply_text("❌ No files uploaded")
        return

    await_password[uid] = True

    await callback.message.reply_text(
        "🔐 Send archive password or type `none`"
    )



@app.on_message(filters.command("dex"))

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
# Extraction + Import
# -------------------------

async def run_import(message, archive, password=""):

    status = await message.reply_text("📦 Extracting archive...")

    process = extract_stream(archive, password)

    batch = []
    processed = 0
    last_update = 0

    BATCH = BATCH_SIZE

    # Read first line to detect streaming
    first_line = process.stdout.readline()

    # STREAM MODE
    if first_line:

        line = first_line

        while True:

            if not line:
                break

            processed += 1

            try:
                row = parse_line(line)

                if row:
                    batch.append(row)

            except Exception as e:
                logging.error(e)

            # insert batch
            if len(batch) >= BATCH:
                insert_rows(batch.copy())
                batch.clear()

            # update progress every 50k rows
            if processed - last_update >= 50000:

                percent = min((processed / 182000000) * 100, 100)

                try:
                    await status.edit_text(
                        f"""
📦 Importing dataset

{progress_bar(percent)}

Rows processed: {processed:,}
"""
                    )
                except:
                    pass

                last_update = processed

            line = process.stdout.readline()

    # FALLBACK MODE (extract to disk)
    else:

        await status.edit_text("⚠ Streaming failed. Extracting to disk...")

        filepath = extract_to_disk(archive, password)

        with open(filepath, "r", errors="ignore") as f:

            for line in f:

                processed += 1

                try:
                    row = parse_line(line)

                    if row:
                        batch.append(row)

                except Exception as e:
                    logging.error(e)

                if len(batch) >= BATCH:
                    insert_rows(batch.copy())
                    batch.clear()

                if processed - last_update >= 50000:

                    percent = min((processed / 182000000) * 100, 100)

                    try:
                        await status.edit_text(
                            f"""
📦 Importing dataset

{progress_bar(percent)}

Rows processed: {processed:,}
"""
                        )
                    except:
                        pass

                    last_update = processed

    # Insert remaining rows
    if batch:
        insert_rows(batch.copy())

    await status.edit_text(
        f"""
✅ Import completed

Total rows processed: {processed:,}
"""
    )


print("EXBOT STARTED")

app.run()
