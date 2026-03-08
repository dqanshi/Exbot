import os
import logging
import time
from pyrogram.errors import FloodWait
import asyncio
from pyrogram import Client, filters
from config import *
from extractor import extract_stream
from parser import parse_line
from db import insert_rows
from split_detect import find_archive_start

from db import get_row_count

start_line = get_row_count()

print("[DEBUG] database rows:", start_line)
    
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

    parts = message.text.split(maxsplit=1)

    password = ""
    if len(parts) > 1:
        password = parts[1]

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

    print("[DEBUG] calling run_import")

    try:
        msg = await message.reply_text("⚙ Starting extraction...")
    except Exception as e:
        print("[ERROR] Telegram reply failed:", e)
        msg = message

    await run_import(msg, archive, password)


# -------------------------
# Import function
# -------------------------

from state import load_state, save_state

start_line = load_state()
print("[DEBUG] resuming from line", start_line)


async def run_import(message, archive, password=""):

    print("[DEBUG] run_import started")
    print("[DEBUG] archive =", archive)

    try:
        status = await message.reply_text("📦 Extracting archive...")
    except:
        status = message

    process = extract_stream(archive, password)

    batch = []
    processed = 0
    last_update = 0

    BATCH = BATCH_SIZE

    start_time = time.time()

    print("[DEBUG] starting stream read")

    # streaming loop
    for line in iter(process.stdout.readline, ''):

        processed += 1

        # skip rows already processed
        if processed <= start_line:
            continue

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

            success = insert_rows(batch.copy())

            if success:
                batch.clear()

        # -------------------------
        # Progress update
        # -------------------------

        if processed - last_update >= 50000:

            elapsed = time.time() - start_time
            speed = processed / elapsed if elapsed > 0 else 0

            print(f"[DEBUG] processed={processed} speed={speed:.0f} rows/sec")

            percent = min((processed / 182000000) * 100, 100)

            text = f"""
📦 Importing dataset

{progress_bar(percent)}

Rows processed: {processed:,}
⚡ Speed: {speed:,.0f} rows/sec
"""

            try:
                await status.edit_text(text)

            except FloodWait as e:

                print(f"[TELEGRAM] FloodWait {e.value}s")

                await asyncio.sleep(e.value)

                try:
                    await status.edit_text(text)
                except:
                    pass

            except Exception as e:
                print("[TELEGRAM] edit error:", e)

            last_update = processed

    # -------------------------
    # Insert remaining rows
    # -------------------------

    if batch:

        print(f"[DEBUG] inserting final batch {len(batch)}")

        insert_rows(batch.copy())

    print(f"[DEBUG] import completed, total rows={processed}")

    try:
        await status.edit_text(
            f"""
✅ Import completed

Total rows processed: {processed:,}
"""
        )

    except FloodWait as e:

        await asyncio.sleep(e.value)

        try:
            await status.edit_text(
                f"""
✅ Import completed

Total rows processed: {processed:,}
"""
            )
        except:
            pass

    except:
        pass
# -------------------------
# Run bot
# -------------------------

print("EXBOT STARTED")

app.run()
