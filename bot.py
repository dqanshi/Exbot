import os
import logging
import time

from pyrogram import Client, filters
from config import *
from extractor import extract_stream
from parser import parse_line
from db import insert_rows
from split_detect import find_archive_start


# -------------------------
# Setup folders
# -------------------------

os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    filename="logs/bot.log",
    level=logging.INFO
)


# -------------------------
# Telegram Client
# -------------------------

app = Client(
    "exbot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workers=16
)


# -------------------------
# Progress bar
# -------------------------

def progress_bar(percent):

    filled = int(percent / 5)
    bar = "█" * filled + "░" * (20 - filled)

    return f"{bar} {percent:.1f}%"


# -------------------------
# Start command
# -------------------------

@app.on_message(filters.command("start"))
async def start(client, message):

    if message.from_user.id != OWNER_ID:
        return

    await message.reply_text(
        "🤖 Exbot Ready\n\n"
        "Send /dex to start importing archives from server."
    )


# -------------------------
# /dex command
# -------------------------

@app.on_message(filters.command("dex") & filters.private)
async def dex_cmd(client, message):

    if message.from_user.id != OWNER_ID:
        return

    print("[DEBUG] /dex command received")

    files = []

    for f in os.listdir(DOWNLOAD_DIR):

        if f.endswith(".7z") or ".7z." in f:
            files.append(os.path.join(DOWNLOAD_DIR, f))

    print("[DEBUG] files found:", files)

    if not files:
        await message.reply_text("❌ No archive files found")
        return

    files.sort()

    archive = find_archive_start(files)

    print("[DEBUG] archive selected:", archive)

    msg = await message.reply_text("⚙ Starting extraction...")

    await run_import(msg, archive)


# -------------------------
# Import function
# -------------------------

async def run_import(message, archive, password=""):

    status = await message.reply_text("📦 Extracting archive...")

    print("[DEBUG] run_import started")
    print("[DEBUG] archive =", archive)

    process = extract_stream(archive, password)

    batch = []
    processed = 0
    last_update = 0

    BATCH = BATCH_SIZE

    start_time = time.time()

    print("[DEBUG] starting stream read")

    # STREAM READ FIX
    for line in process.stdout:

        processed += 1

        try:

            row = parse_line(line)

            if row:
                batch.append(row)

        except Exception as e:
            logging.error(e)

        # -------------------------
        # Insert batch
        # -------------------------

        if len(batch) >= BATCH:

            print(f"[DEBUG] inserting batch {len(batch)}")

            insert_rows(batch.copy())

            batch.clear()

        # -------------------------
        # Progress update
        # -------------------------

        if processed - last_update >= 50000:

            elapsed = time.time() - start_time
            speed = processed / elapsed if elapsed > 0 else 0

            print(f"[DEBUG] processed={processed} speed={speed:.0f} rows/sec")

            percent = min((processed / 182000000) * 100, 100)

            try:

                await status.edit_text(
                    f"""
📦 Importing dataset

{progress_bar(percent)}

Rows processed: {processed:,}
⚡ Speed: {speed:,.0f} rows/sec
"""
                )

            except:
                pass

            last_update = processed

    # -------------------------
    # Insert remaining rows
    # -------------------------

    if batch:

        print(f"[DEBUG] inserting final batch {len(batch)}")

        insert_rows(batch.copy())

    print(f"[DEBUG] import completed, total rows={processed}")

    await status.edit_text(
        f"""
✅ Import completed

Total rows processed: {processed:,}
"""
    )


# -------------------------
# Run bot
# -------------------------

print("EXBOT STARTED")

app.run()
