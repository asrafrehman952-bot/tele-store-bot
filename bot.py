import sqlite3
import uuid
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# Yahan apna BotFather wala token double quotes ke andar dalein
BOT_TOKEN = "8702664754:AAGSEa3r1l3_x63LpxirRj2UzyzUGDtLon4"


def init_db():
    conn = sqlite3.connect("bot_store.db")
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_id TEXT,
            chat_id INTEGER,
            message_id INTEGER
        )
        """
    )
    conn.commit()
    conn.close()

def save_message_ref(batch_id: str, chat_id: int, message_id: int):
    conn = sqlite3.connect("bot_store.db")
    c = conn.cursor()
    c.execute(
        "INSERT INTO messages (batch_id, chat_id, message_id) VALUES (?, ?, ?)",
        (batch_id, chat_id, message_id),
    )
    conn.commit()
    conn.close()

def get_message_refs(batch_id: str):
    conn = sqlite3.connect("bot_store.db")
    c = conn.cursor()
    c.execute(
        "SELECT chat_id, message_id FROM messages WHERE batch_id = ?",
        (batch_id,),
    )
    rows = c.fetchall()
    conn.close()
    return rows

user_sessions = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args

    if args:
        batch_id = args[0]
        stored_refs = get_message_refs(batch_id)

        if not stored_refs:
            await update.message.reply_text("❌ No content found for this link or it expired.")
            return

        await update.message.reply_text("📦 Here is your saved content:")
        for src_chat_id, src_msg_id in stored_refs:
            try:
                await context.bot.copy_message(
                    chat_id=user_id,
                    from_chat_id=src_chat_id,
                    message_id=src_msg_id,
                )
            except Exception as e:
                await update.message.reply_text(f"Could not retrieve message: {e}")
        return

    await update.message.reply_text(
        "👋 Welcome! Commands:\n\n"
        "• `/save` - Start a new collection\n"
        "• Send or forward any messages/files you want to store\n"
        "• `/finish` - Get your shareable link"
    )

async def start_saving(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    batch_id = uuid.uuid4().hex[:10]
    user_sessions[user_id] = batch_id

    await update.message.reply_text(
        "📥 **Recording session started!**\n"
        "Send or forward all the messages, texts, or media you want to bundle together.\n\n"
        "When you're done, send `/finish`."
    )

async def finish_saving(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_sessions:
        await update.message.reply_text("You haven't started a session. Send `/save` first.")
        return

    batch_id = user_sessions.pop(user_id)
    items = get_message_refs(batch_id)

    if not items:
        await update.message.reply_text("⚠️ No messages were saved. Send `/save` to try again.")
        return

    bot_info = await context.bot.get_me()
    share_link = f"https://t.me/{bot_info.username}?start={batch_id}"

    await update.message.reply_text(
        f"✅ **Saved {len(items)} item(s)!**\n\n"
        f"🔗 Here is your link:\n`{share_link}`\n\n"
        f"Whenever anyone clicks this link, the bot will deliver all the saved messages.",
        parse_mode="Markdown"
    )

async def handle_incoming_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_sessions:
        batch_id = user_sessions[user_id]
        save_message_ref(batch_id, update.message.chat_id, update.message.message_id)
        await update.message.reply_text("📥 Message added to batch.")

def main():
    init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("save", start_saving))
    app.add_handler(CommandHandler("finish", finish_saving))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_incoming_messages))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
