import re
import random
import string
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# ========== CONFIG ==========
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
CAPTAIN_CHAT_ID = -1001234567890  # GANTI DENGAN CHAT ID GROUP CAPTAIN

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
async def handle_cs_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    text = message.text or message.caption or ""
    
    if any(trigger in text.lower() for trigger in RESET_TRIGGERS):
        # Simpan data CS
        context.user_data['cs_id'] = update.effective_user.id
        context.user_data['cs_name'] = update.effective_user.full_name
        context.user_data['original_request'] = text
        
        # Keyboard untuk captain
        keyboard = [
            [InlineKeyboardButton("✅ Reset", callback_data="captain_reset"),
             InlineKeyboardButton("❌ Tolak", callback_data="captain_reject")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Kirim ke captain
        await context.bot.send_message(
            chat_id=CAPTAIN_CHAT_ID,
            text=f"🔔 *RESET REQUEST*\n\n"
                 f"CS: {update.effective_user.full_name}\n"
                 f"Pesan:\n`{text[:300]}`\n\n"
                 f"Pilih:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        await message.reply_text("✅ Request ke captain.")

# ========== HANDLER PILIHAN CAPTAIN ==========
async def handle_captain_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    cs_id = context.user_data.get('cs_id')
    cs_name = context.user_data.get('cs_name', 'CS')
    original_text = context.user_data.get('original_request', '')
    
    if not cs_id:
        await query.edit_message_text("❌ Error: CS data hilang")
        return
    
    if query.data == "captain_reset":
        # EKSTRAKSI USER_ID DAN ASSET
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
        
        # Generate password
        new_password = generate_random_password()
        
        # FORMAT YANG DIMINTA
        response_to_cs = (
            f"{user_id} - {asset}\n"
            f"Password baru : {new_password}"
        )
        
        # Kirim ke CS
        await context.bot.send_message(
            chat_id=cs_id,
            text=response_to_cs
        )
        
        # Update di group captain
        await query.edit_message_text(
            text=f"✅ Reset untuk {user_id}\nPassword dikirim ke {cs_name}."
        )
    
    elif query.data == "captain_reject":
        # Kirim ke CS
        await context.bot.send_message(
            chat_id=cs_id,
            text="Permintaan anda ditolak Captain !!"
        )
        
        # Update di group captain
        await query.edit_message_text(
            text=f"❌ Request ditolak\nNotif ke {cs_name}."
        )

# ========== MAIN ==========
def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(MessageHandler(
        filters.TEXT | filters.PHOTO | filters.CAPTION, 
        handle_cs_message
    ))
    application.add_handler(CallbackQueryHandler(handle_captain_choice))
    
    print("Bot running...")
    application.run_polling()

if __name__ == "__main__":
    main()
