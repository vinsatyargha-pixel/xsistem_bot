import os
import re
import random
import string
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# ========== CONFIG ==========
BOT_TOKEN = "8087735462:AAGduMGrAaut2mlPanwlsCq7K-82fqIFuOo"  # Ganti dengan token botmu
CAPTAIN_CHAT_ID = -5720343562  # Ganti dengan chat ID captain/group admin

# ========== TRIGGER KATA ==========
RESET_TRIGGERS = ["/repass", "/reset", "/repas"]

# ========== FUNGSI GENERATE PASSWORD ==========
def generate_random_password(length=10):
    uppercase = string.ascii_uppercase
    lowercase = string.ascii_lowercase
    digits = string.digits
    
    password_chars = [
        random.choice(uppercase),
        random.choice(lowercase),
        random.choice(digits)
    ]
    
    all_chars = uppercase + lowercase + digits
    for _ in range(length - 3):
        password_chars.append(random.choice(all_chars))
    
    random.shuffle(password_chars)
    return ''.join(password_chars)

# ========== HANDLER PESAN DARI CS ==========
# ========== HANDLER PESAN DARI CS ==========
async def handle_cs_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    text = message.text or message.caption or ""
    
    if any(trigger in text.lower() for trigger in RESET_TRIGGERS):
        keyboard = [
            [
                InlineKeyboardButton("✅ Reset", callback_data="captain_reset"),
                InlineKeyboardButton("❌ Tolak", callback_data="captain_reject")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Kirim ke group captain
        await context.bot.send_message(
            chat_id=CAPTAIN_CHAT_ID,
            text=f"🔔 *Permintaan Reset Password*\n\n"
                 f"CS: {update.effective_user.full_name}\n"
                 f"Pesan:\n`{text[:300]}`\n\n"
                 f"Silakan pilih tindakan:",
            reply_markup=reply_markup,
            parse_mode='Markdown',
            reply_to_message_id=message.message_id if message.photo else None
        )
        
        await message.reply_text("✅ Permintaan sudah diteruskan ke captain.")
        
        # Kirim ke group captain
        await context.bot.send_message(
            chat_id=CAPTAIN_CHAT_ID,
            text=f"🔔 *Permintaan Reset Password*\n\n"
                 f"CS: {update.effective_user.full_name}\n"
                 f"Pesan:\n`{text[:300]}`\n\n"
                 f"Silakan pilih tindakan:",
            reply_markup=reply_markup,
            parse_mode='Markdown',
            reply_to_message_id=message.message_id if message.photo else None
        )
        
        await message.reply_text("✅ Permintaan sudah diteruskan ke captain.")

# ========== HANDLER PILIHAN CAPTAIN ==========
async def handle_captain_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if update.effective_chat.id != CAPTAIN_CHAT_ID:
        return
    
    original_message = query.message.reply_to_message
    original_text = original_message.text or original_message.caption or ""
    
    if query.data == "captain_reset":
        patterns = [
            r'(\w+)[\s\-]+([A-Za-z0-9]+)',
            r'(\w+)\s*-\s*([A-Za-z0-9]+)',
        ]
        
        user_id = "UNKNOWN"
        asset = "UNKNOWN"
        
        for pattern in patterns:
            match = re.search(pattern, original_text)
            if match:
                user_id = match.group(1).strip()
                asset = match.group(2).strip()
                break
        
        new_password = generate_random_password()
        
        # Format untuk CS
        response_to_cs = (
            f"✅ *PASSWORD READY!*\n\n"
            f"👤 ID: `{user_id}`\n"
            f"🔐 Password: `{new_password}`\n\n"
            f"⚠️ Berikan ke user segera!"
        )
        
        # Kirim ke CS
        await context.bot.send_message(
            chat_id=CS_USER_ID,
            text=response_to_cs,
            parse_mode='Markdown'
        )
        
        # Update pesan di group captain
        await query.edit_message_text(
            text=f"✅ *Reset Disetujui*\n\n"
                 f"User: `{user_id}`\n"
                 f"Asset: `{asset}`\n"
                 f"Password baru sudah dikirim ke CS.",
            parse_mode='Markdown'
        )
    
    elif query.data == "captain_reject":
        await query.edit_message_text(
            text="❌ *Permintaan Ditolak*\n\n"
                 "CS dimohon memberi notice ke user:\n\n"
                 "⚠️ *Permintaan anda ditolak Captain !!*",
            parse_mode='Markdown'
        )
        
        # Notifikasi ke CS
        await context.bot.send_message(
            chat_id=CS_USER_ID,
            text="❌ Permintaan reset password DITOLAK oleh Captain.\n"
                 "Berikan notice ke user: *Permintaan anda ditolak Captain !!*",
            parse_mode='Markdown'
        )

# ========== START COMMAND ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot Reset Password siap!")

# ========== MAIN ==========
def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Handler
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_cs_message))
    application.add_handler(CallbackQueryHandler(handle_captain_choice))
    
    print("Bot sedang berjalan...")
    application.run_polling()

if __name__ == "__main__":
    main()
