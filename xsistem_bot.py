import telebot
import sqlite3
import random
import string
import os
from telebot import types

# ========== CONFIGURASI ==========
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = int(os.environ.get("ADMIN_CHAT_ID", "5720343562"))
DATABASE = "xsistem.db"
UPLOAD_FOLDER = "bukti_deposit"
# =================================

bot = telebot.TeleBot(TOKEN)

# Buat folder untuk simpan gambar
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS reset_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        request_id TEXT UNIQUE,
        cs_user_id INTEGER,
        cs_username TEXT,
        target_account_id TEXT DEFAULT 'AUTO',
        game_name TEXT DEFAULT 'GAME',
        status TEXT DEFAULT 'pending',
        new_password TEXT,
        admin_id INTEGER,
        photo_path TEXT
    )
    ''')
    conn.commit()
    conn.close()
    print("✅ Database siap!")

def generate_password():
    # 9 karakter: huruf besar, kecil, angka
    uppercase = ''.join(random.choice(string.ascii_uppercase) for _ in range(3))
    lowercase = ''.join(random.choice(string.ascii_lowercase) for _ in range(3))
    numbers = ''.join(random.choice(string.digits) for _ in range(3))
    password_chars = list(uppercase + lowercase + numbers)
    random.shuffle(password_chars)
    return ''.join(password_chars)

# ========== TRIGGER WORDS ==========
@bot.message_handler(func=lambda message: any(word in message.text.lower() for word in ['repas', 'repass', 'reset']))
def handle_trigger(message):
    """Handle trigger words: repas, repass, reset"""
    user_id = message.from_user.id
    cs_user = message.from_user
    
    try:
        # Generate request ID
        request_id = f"X{random.randint(1000, 9999)}"
        
        # Simpan ke database
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO reset_requests 
        (request_id, cs_user_id, cs_username)
        VALUES (?, ?, ?)
        ''', (request_id, cs_user.id, cs_user.username))
        conn.commit()
        conn.close()
        
        # Konfirmasi ke user
        bot.reply_to(message,
            f"✅ *REQUEST DITERIMA!*\n\n"
            f"📋 Kode: `{request_id}`\n\n"
            "⏳ Menunggu approval admin...",
            parse_mode='Markdown'
        )
        
        # Kirim notifikasi ke admin
        send_to_admin(request_id, cs_user.username)
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

def send_to_admin(request_id, cs_username):
    """Kirim notifikasi ke admin"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_reset = types.InlineKeyboardButton("✅ RESET", callback_data=f"ok_{request_id}")
    btn_decline = types.InlineKeyboardButton("❌ TOLAK", callback_data=f"no_{request_id}")
    markup.add(btn_reset, btn_decline)
    
    admin_msg = (
        f"🔄 *REQUEST BARU*\n"
        f"━━━━━━━━━━━━━━\n"
        f"📋 Kode: `{request_id}`\n"
        f"🛡️ CS: @{cs_username}\n"
        f"⏰ Waktu: {datetime.now().strftime('%H:%M:%S')}"
    )
    
    bot.send_message(ADMIN_CHAT_ID, admin_msg, parse_mode='Markdown', reply_markup=markup)

# ========== HANDLE FOTO ==========
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    """Handle foto yang dikirim kapan saja"""
    user_id = message.from_user.id
    
    # Cari request terakhir dari user ini yang masih pending
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
    SELECT request_id, photo_path
    FROM reset_requests 
    WHERE cs_user_id = ? AND status = 'pending' 
    ORDER BY request_time DESC LIMIT 1
    ''', (user_id,))
    
    result = cursor.fetchone()
    
    if result:
        request_id, existing_photo = result
        
        # Jika sudah ada foto sebelumnya
        if existing_photo:
            conn.close()
            return
        
        # Download foto
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        # Simpan foto
        timestamp = int(time.time())
        photo_filename = f"{request_id}_{timestamp}.jpg"
        photo_path = os.path.join(UPLOAD_FOLDER, photo_filename)
        
        with open(photo_path, 'wb') as new_file:
            new_file.write(downloaded_file)
        
        # Update database
        cursor.execute('''UPDATE reset_requests SET photo_path = ? WHERE request_id = ?''', 
                      (photo_path, request_id))
        conn.commit()
        
        # Kirim foto ke admin
        with open(photo_path, 'rb') as photo:
            bot.send_photo(
                ADMIN_CHAT_ID, 
                photo,
                caption=f"📸 *BUKTI*\nKode: {request_id}\nCS: @{cs_username}",
                parse_mode='Markdown'
            )
        
    conn.close()

# ========== APPROVAL SYSTEM ==========
@bot.callback_query_handler(func=lambda call: call.data.startswith("ok_"))
def approve_request(call):
    request_id = call.data.split("_")[1]
    new_password = generate_password()
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute('''SELECT cs_user_id FROM reset_requests WHERE request_id = ?''', (request_id,))
    result = cursor.fetchone()
    
    if result:
        cs_user_id = result[0]
        
        # Update database
        cursor.execute('''
        UPDATE reset_requests 
        SET status = 'completed',
            new_password = ?,
            admin_id = ?,
        WHERE request_id = ?
        ''', (new_password, call.from_user.id, request_id))
        conn.commit()
        
        # Kirim password ke CS
     bot.send_message(
    cs_user_id,
    f"✅ *PASSWORD READY!*\n\n"
    f"👤 ID: `{user_id}`\n"  # Ganti Kode dengan ID user
    f"🔐 Password: `{new_password}`\n\n"
    f"⚠️ Berikan ke user segera!",
    parse_mode='Markdown'
)
        
        # Update pesan admin
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="✅ SELESAI",
            reply_markup=None
        )
        
        bot.answer_callback_query(call.id, "Password dikirim")
    
    conn.close()

@bot.callback_query_handler(func=lambda call: call.data.startswith("no_"))
def decline_request(call):
    request_id = call.data.split("_")[1]
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute('''SELECT cs_user_id FROM reset_requests WHERE request_id = ?''', (request_id,))
    result = cursor.fetchone()
    
    if result:
        cs_user_id = result[0]
        bot.send_message(cs_user_id, f"❌ Request {request_id} DITOLAK")
    
    cursor.execute('''
    UPDATE reset_requests 
    SET status = 'rejected',
        admin_id = ?,
        process_time = CURRENT_TIMESTAMP
    WHERE request_id = ?
    ''', (call.from_user.id, request_id))
    
    conn.commit()
    conn.close()
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="❌ DITOLAK",
        reply_markup=None
    )
    
    bot.answer_callback_query(call.id, "Request ditolak")

# ========== START BOT ==========
if __name__ == "__main__":
    print("=" * 50)
    print("🚀 Starting X-Sistem Bot (Trigger Mode)")
    print("=" * 50)
    
    try:
        init_db()
        print(f"✅ Admin ID: {ADMIN_CHAT_ID}")
        print("🤖 Bot is running! Trigger words: repas, repass, reset")
        print("=" * 50)
        
        bot.polling(none_stop=True, timeout=30)
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        import time
        while True:
            time.sleep(60)


