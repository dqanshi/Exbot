import os
import logging

from pyrogram import Client, filters

from config import *
from extractor import extract_stream
from parser import parse_line
from db import insert_rows
from split_detect import find_archive_start
from state import save_state, load_state
from security import verify_password, full_wipe


# -------------------
# Setup
# -------------------

os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    filename="logs/bot.log",
    level=logging.INFO
)

user_files = {}
await_password = {}


# -------------------
# Start
# -------------------

@Client.on_message(filters.command("start"))
async def start(client, message):

    if message.from_user.id != OWNER_ID:
        return

    await message.reply_text(
        "🤖 Exbot Ready\n\n"
        "Forward archive files\n"
        "When finished send /extract"
    )


# -------------------
# Receive archive
# -------------------

@Client.on_message(filters.document)
async def receive_file(client, message):

    if message.from_user.id != OWNER_ID:
        return

    doc = message.document

    print("FILE RECEIVED:", doc.file_name)

    path = os.path.join(DOWNLOAD_DIR, doc.file_name)

    await message.download(file_name=path)

    uid = message.from_user.id

    if uid not in user_files:
        user_files[uid] = []

    user_files[uid].append(path)

    print("FILES STORED:", user_files)

    await message.reply_text(
        f"📥 {doc.file_name} saved\n"
        "Send more parts or /extract"
    )


# -------------------
# Extract command
# -------------------

@Client.on_message(filters.command("extract"))
async def extract(client, message):

    if message.from_user.id != OWNER_ID:
        return

    uid = message.from_user.id

    if uid not in user_files or not user_files[uid]:
        await message.reply_text("❌ No archive files uploaded")
        return

    files = sorted(user_files[uid])

    archive = find_archive_start(files)

    await message.reply_text("⚙ Starting extraction...")

    await run_import(message, archive)


# -------------------
# Import pipeline
# -------------------

async def run_import(message, archive):

    process = extract_stream(archive)

    batch = []
    processed = 0

    resume_line = load_state()

    while True:

        line = process.stdout.readline()

        if not line:
            break

        try:

            row = parse_line(line)

            if row:
                batch.append(row)

        except Exception as e:
            logging.error(e)

        if len(batch) >= BATCH_SIZE:

            insert_rows(batch)
            batch.clear()

        processed += 1

        if processed % 50000 == 0:
            save_state(processed)

    insert_rows(batch)

    await message.reply_text("✅ Import completed")


# -------------------
# Delete command
# -------------------

@Client.on_message(filters.command("delete"))
async def delete(client, message):

    if message.from_user.id != OWNER_ID:
        return

    parts = message.text.split()

    if len(parts) != 2:
        await message.reply_text("Invalid command")
        return

    if not verify_password(parts[1]):
        await message.reply_text("Access denied")
        return

    full_wipe()

    await message.reply_text("Database deleted")


# -------------------
# Run bot
# -------------------

app = Client(
    "exbot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

app.run()
