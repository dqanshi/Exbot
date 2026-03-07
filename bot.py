import os
import logging
import asyncio

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

from config import *
from extractor import extract_stream
from parser import parse_line
from db import insert_rows, setup_database
from split_detect import find_archive_start
from state import save_state, load_state
from security import verify_password, full_wipe


# -----------------------
# Setup folders
# -----------------------

os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    filename="logs/bot.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

setup_database()

# store uploaded files
user_files = {}


# -----------------------
# Start command
# -----------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != OWNER_ID:
        return

    await update.message.reply_text(
        "🤖 Exbot ready.\n\n"
        "Forward archive files.\n"
        "When finished send /extract"
    )


# -----------------------
# Receive files
# -----------------------

async def receive_file(update: Update, context: ContextTypes.DEFAULT_TYPE):

    print("RECEIVE_FILE TRIGGERED")

    # check user
    if update.effective_user.id != OWNER_ID:
        print("WRONG USER")
        return

    message = update.effective_message

    if not message:
        print("NO MESSAGE")
        return

    doc = message.document

    if not doc:
        print("NO DOCUMENT")
        return

    print("FILE RECEIVED:", doc.file_name)

    file = await doc.get_file()

    path = os.path.join(DOWNLOAD_DIR, doc.file_name)

    await file.download_to_drive(path)

    uid = update.effective_user.id

    # create storage list
    if uid not in user_files:
        user_files[uid] = []

    # store archive path
    user_files[uid].append(path)

    print("FILES STORED:", user_files)

    await message.reply_text(
        f"📥 {doc.file_name} saved.\nSend more parts or run /extract"
    )


# -----------------------
# Extract command
# -----------------------

async def extract(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != OWNER_ID:
        return

    uid = update.effective_user.id

    print("USER FILES:", user_files)

    if uid not in user_files or len(user_files[uid]) == 0:
        await update.message.reply_text("❌ No archive files uploaded.")
        return

    await update.effective_message.reply_text("⚙ Starting extraction...")
    
    await run_import(update, context)


# -----------------------
# Import system
# -----------------------

async def run_import(update, context):

    uid = update.effective_user.id

    files = sorted(user_files[uid])

    # detect first archive part
    archive = find_archive_start(files)

    password = context.user_data.get("password", "")

    msg = await update.message.reply_text("📦 Extracting archive...")

    process = extract_stream(archive, password)

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
            logging.error(f"parse error {e}")

        if len(batch) >= BATCH_SIZE:

            insert_rows(batch)
            batch.clear()

        processed += 1

        if processed % 50000 == 0:
            save_state(processed)

    insert_rows(batch)

    await msg.edit_text("✅ Import completed")


# -----------------------
# Delete database
# -----------------------

async def delete(update, context):

    if update.effective_user.id != OWNER_ID:
        return

    parts = update.message.text.split()

    if len(parts) != 2:
        await update.message.reply_text("Invalid command")
        return

    if not verify_password(parts[1]):
        await update.message.reply_text("Access denied")
        return

    full_wipe()

    await update.message.reply_text("🗑 Database deleted")


# -----------------------
# Keep alive
# -----------------------

async def keep_alive():

    while True:
        logging.info("BOT ALIVE")
        await asyncio.sleep(300)


# -----------------------
# Bot setup
# -----------------------

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("extract", extract))
app.add_handler(CommandHandler("delete", delete))

# file handler
app.add_handler(MessageHandler(filters.Document.ALL, receive_file))


if __name__ == "__main__":

    asyncio.get_event_loop().create_task(keep_alive())

    print("EXBOT STARTED")

    app.run_polling()
