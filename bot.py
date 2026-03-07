import os
import logging
import asyncio

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
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


# Create folders
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# Logging
logging.basicConfig(
    filename="logs/bot.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)
setup_database()

user_files = {}
await_password = {}


# -----------------------
# Progress Bar
# -----------------------

def progress_bar(p):

    size = 20
    filled = int(size * p / 100)

    bar = "█" * filled + "░" * (size - filled)

    return f"""
📦 Importing Dataset

{bar} {p}%

Processing records...
"""


# -----------------------

async def debug(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("MESSAGE TYPE:", update.message)




# Start Menu
# -----------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.message.from_user.id != OWNER_ID:
        return

    keyboard = [
        [InlineKeyboardButton("📦 Upload Archive", callback_data="upload")],
        [InlineKeyboardButton("📊 Status", callback_data="status")]
    ]

    await update.message.reply_text(
        """
🤖 **Exbot Ready**

Send archive files to start extraction.

Supported:
• .7z
• .rar
• split archives

Bot will automatically extract and import data.
""",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# -----------------------
# Receive Archive
# -----------------------

async def receive_file(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message:
        return

    if update.message.from_user.id != OWNER_ID:
        return

    # ignore messages that are not files
    if not update.message.document:
        return

    doc = update.message.document
    file = await doc.get_file()

    path = os.path.join(DOWNLOAD_DIR, doc.file_name)

    await file.download_to_drive(path)

    uid = update.message.from_user.id

    user_files.setdefault(uid, []).append(path)

    caption = update.message.caption or ""

    password = ""

    if "pass" in caption.lower():
        password = caption.split(":")[-1].strip()

    context.user_data["password"] = password

    await update.message.reply_text(
        f"📥 {doc.file_name} downloaded."
    )

    # ask password if needed
    if context.user_data.get("password") == "":
        await_password[uid] = True

        await update.message.reply_text(
            "🔑 Send archive password or type none"
        )
        return

    await run_import(update, context)
    


# -----------------------
# Password Handler
# -----------------------

async def password(update: Update, context: ContextTypes.DEFAULT_TYPE):

    uid = update.message.from_user.id

    if uid not in await_password:
        return

    pwd = update.message.text

    if pwd == "none":
        pwd = ""

    context.user_data["password"] = pwd

    await_password.pop(uid)

    await run_import(update, context)


# -----------------------
# Import System
# -----------------------

async def run_import(update, context):

    uid = update.message.from_user.id

    files = sorted(user_files[uid])

    archive = find_archive_start(files)

    password = context.user_data.get("password", "")

    msg = await update.message.reply_text("⚙ Starting extraction...")

    process = extract_stream(archive, password)

    batch = []
    processed = 0

    resume_line = load_state()

    while True:

        line = process.stdout.readline()

        if not line:
            break

        stderr_line = process.stderr.readline()

        # progress from 7z
        if "%" in stderr_line:
            try:
                percent = int(stderr_line.strip().replace("%", ""))
                await msg.edit_text(progress_bar(percent))
            except:
                pass

        if processed < resume_line:
            processed += 1
            continue

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

    await msg.edit_text("✅ Import completed.")


# -----------------------
# Status Command
# -----------------------

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.message.from_user.id != OWNER_ID:
        return

    await update.message.reply_text(
        "🟢 Exbot is running.\nSystem ready."
    )


# -----------------------
# Emergency Delete
# -----------------------

async def delete(update, context):

    if update.message.from_user.id != OWNER_ID:
        return

    parts = update.message.text.split()

    if len(parts) != 2:
        await update.message.reply_text("Invalid command")
        return

    if not verify_password(parts[1]):
        await update.message.reply_text("Access denied")
        return

    await update.message.reply_text("⚠ Deleting dataset...")

    full_wipe()

    await update.message.reply_text("🗑 Dataset removed.")


# -----------------------
# Keep Bot Alive
# -----------------------

async def keep_alive():

    while True:
        logging.info("Bot heartbeat alive")
        await asyncio.sleep(300)


# -----------------------
# Main
# -----------------------

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("status", status))
app.add_handler(CommandHandler("delete", delete))

app.add_handler(MessageHandler(filters.ALL, debug))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, password))


async def main():

    asyncio.create_task(keep_alive())

    await app.initialize()
    await app.start()
    await app.updater.start_polling()


if __name__ == "__main__":
    app.run_polling()
