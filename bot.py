import logging
import json
import os
import uuid
import threading
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler

# --- CONFIGURATION ---
BOT_TOKEN = "8241920438:AAG9jrkWWzwmZ9NtxLOWj-MapTb72iEFlLg"
ADMIN_ID = 582152237
DB_FILE = "files_db.json"

# --- FLASK KEEP-ALIVE SERVER ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run_web_server():
    # Render provides the PORT variable
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

# --- BOT LOGIC ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

def load_files():
    if not os.path.exists(DB_FILE): return {}
    try:
        with open(DB_FILE, 'r') as f: return json.load(f)
    except json.JSONDecodeError: return {}

def save_file_entry(name, file_id):
    data = load_files()
    short_id = str(uuid.uuid4())[:8]
    data[short_id] = {"name": name, "file_id": file_id}
    with open(DB_FILE, 'w') as f: json.dump(data, f)
    return short_id

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    files = load_files()
    if not files:
        await update.message.reply_text("No files yet.")
        return
    keyboard = []
    for short_id, file_data in files.items():
        keyboard.append([InlineKeyboardButton(file_data['name'], callback_data=short_id)])
    await update.message.reply_text("👋 Choose a file:", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_document_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    doc = update.message.document
    save_file_entry(doc.file_name, doc.file_id)
    await update.message.reply_text(f"✅ Saved: {doc.file_name}")

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    files = load_files()
    chat_id = update.effective_chat.id
    
    # Delete old message logic
    last_msg_id = context.user_data.get('last_file_msg_id')
    if last_msg_id:
        try: await context.bot.delete_message(chat_id=chat_id, message_id=last_msg_id)
        except Exception: pass

    short_id = query.data
    if short_id in files:
        try:
            msg = await query.message.reply_document(document=files[short_id]['file_id'], caption=f"📄 {files[short_id]['name']}")
            context.user_data['last_file_msg_id'] = msg.message_id
        except Exception: await query.message.reply_text("❌ Error sending file.")
    else:
        await query.message.reply_text("❌ File not found.")

if __name__ == '__main__':
    # 1. Start the dummy web server in a separate thread
    threading.Thread(target=run_web_server).start()
    
    # 2. Start the Bot
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document_upload))
    application.add_handler(CallbackQueryHandler(button_click))
    
    print("Bot is running on Render...")
    application.run_polling()