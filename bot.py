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

user_files = {}
await_password = {}


# -----------------------
# Debug handler
# -----------------------

async def debug(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("DEBUG MESSAGE:", update.message)


# -----------------------
# Start command
# -----------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    print("START COMMAND")

    if update.effective_user.id != OWNER_ID:
        print("IGNORED USER:", update.effective_user.id)
        return

    await update.message.reply_text("🤖 Exbot ready. Send archive files.")


# -----------------------
# Receive file
# -----------------------
async def receive_file(update: Update, context: ContextTypes.DEFAULT_TYPE):

    print("RECEIVE_FILE TRIGGERED")

    if not update.effective_message:
        print("NO MESSAGE")
        return

    if update.effective_user.id != OWNER_ID:
        print("WRONG OWNER")
        return

    doc = update.effective_message.document

    if not doc:
        print("NO DOCUMENT FOUND")
        return

    print("FILE RECEIVED:", doc.file_name)

    file = await doc.get_file()

    path = os.path.join(DOWNLOAD_DIR, doc.file_name)

    await file.download_to_drive(path)

    uid = update.effective_user.id

    user_files.setdefault(uid, []).append(path)

    caption = update.effective_message.caption or ""

    password = ""

    caption_lower = caption.lower()

    # Detect password in caption
    if "password" in caption_lower or "pass" in caption_lower:
        try:
            password = caption.split(":")[-1].strip()
        except:
            password = ""

    context.user_data["password"] = password

    await update.effective_message.reply_text(
        f"📥 {doc.file_name} downloaded"
    )

    if password == "":
        await_password[uid] = True
        await update.effective_message.reply_text(
            "🔑 Send archive password or type none"
        )
        return

    await run_import(update, context)


# -----------------------
# Password handler
# -----------------------

async def password(update: Update, context: ContextTypes.DEFAULT_TYPE):

    uid = update.effective_user.id

    if uid not in await_password:
        return

    pwd = update.message.text

    if pwd == "none":
        pwd = ""

    context.user_data["password"] = pwd

    await_password.pop(uid)

    await run_import(update, context)


# -----------------------
# Import system
# -----------------------

async def run_import(update, context):

    uid = update.effective_user.id

    files = sorted(user_files[uid])

    archive = find_archive_start(files)

    password = context.user_data.get("password", "")

    msg = await update.effective_message.reply_text("⚙ Starting extraction")

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
# Delete command
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

    await update.message.reply_text("Database deleted")


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
app.add_handler(CommandHandler("delete", delete))

# File handler FIRST
app.add_handler(MessageHandler(filters.Document.ALL, receive_file))

# Password handler
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, password))

# Debug LAST
app.add_handler(MessageHandler(filters.ALL, debug))
if __name__ == "__main__":

    asyncio.get_event_loop().create_task(keep_alive())

    print("EXBOT STARTED")

    app.run_polling()
