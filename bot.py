import os
import json
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
# Setup
# -----------------------

os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

FILES_DB = "uploaded_files.json"

logging.basicConfig(
    filename="logs/bot.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

setup_database()


# -----------------------
# helpers
# -----------------------

def load_files():
    if not os.path.exists(FILES_DB):
        return {}
    with open(FILES_DB, "r") as f:
        return json.load(f)


def save_files(data):
    with open(FILES_DB, "w") as f:
        json.dump(data, f)


# -----------------------
# start
# -----------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != OWNER_ID:
        return

    await update.effective_message.reply_text(
        "🤖 Exbot ready\n\n"
        "Forward archive files.\n"
        "Then send /extract"
    )


# -----------------------
# receive file
# -----------------------

async def receive_file(update: Update, context: ContextTypes.DEFAULT_TYPE):

    print("RECEIVE_FILE TRIGGERED")

    if update.effective_user.id != OWNER_ID:
        return

    message = update.effective_message
    doc = message.document

    if not doc:
        return

    print("FILE RECEIVED:", doc.file_name)

    file = await doc.get_file()

    path = os.path.join(DOWNLOAD_DIR, doc.file_name)

    await file.download_to_drive(path)

    uid = str(update.effective_user.id)

    files = load_files()

    if uid not in files:
        files[uid] = []

    files[uid].append(path)

    save_files(files)

    print("FILES STORED:", files)

    await message.reply_text(
        f"📥 {doc.file_name} saved\n"
        f"Send more parts or /extract"
    )


# -----------------------
# extract command
# -----------------------

async def extract(update: Update, context: ContextTypes.DEFAULT_TYPE):

    uid = str(update.effective_user.id)

    files = load_files()

    print("USER FILES:", files)

    if uid not in files or len(files[uid]) == 0:
        await update.effective_message.reply_text("❌ No archive files uploaded.")
        return

    await update.effective_message.reply_text("⚙ Starting extraction...")

    await run_import(update, context, files[uid])


# -----------------------
# import
# -----------------------

async def run_import(update, context, files):

    files = sorted(files)

    archive = find_archive_start(files)

    password = context.user_data.get("password", "")

    msg = await update.effective_message.reply_text("📦 Extracting...")

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
# bot setup
# -----------------------

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("extract", extract))

app.add_handler(MessageHandler(filters.Document.ALL, receive_file))


# -----------------------
# run
# -----------------------

if __name__ == "__main__":

    print("EXBOT STARTED")

    app.run_polling()
