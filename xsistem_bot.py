import telebot
import sqlite3
import random
import string
import os
from datetime import datetime
from telebot import types
import time

# ========== CONFIGURASI ==========
TOKEN = os.environ.get("TOKEN", "MASUKKAN_TOKEN_ANDA_DISINI")  # Railway akan pakai environment variable
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
        target_account_id TEXT,
        game_name TEXT,
        request_time DATETIME DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'pending',
        new_password TEXT,
        admin_id INTEGER,
        process_time DATETIME,
        photo_path TEXT
    )
    ''')
    conn.commit()
    conn.close()
    print("✅ Database siap!")

def generate_password():
    upper = random.choice(string.ascii_uppercase)
    lower = random.choice(string.ascii_lowercase)
    numbers = ''.join(random.choice(string.digits) for _ in range(3))
    special = random.choice('!@#$%^&*')
    password_chars = list(upper + lower + numbers + special)
    random.shuffle(password_chars)
    return ''.join(password_chars)

# ========== SINGLE COMMAND FLOW ==========
@bot.message_handler(commands=['start', 'help'])
def start_command(message):
    help_text = """
    🤖 *X-SISTEM BOT - Reset Password*

    *CARA PAKAI:*
    `/reset ID_AKUN NAMA_GAME`
    
    *Contoh:*
    `/reset Tampias77 G200M`

    *Bisa juga kirim bukti deposit (foto)*
    Kirim foto setelah command /reset
    
    *Cek Status:*
    `/status KODE`
    
    *Admin:* `/admin`
    """
    bot.send_message(message.chat.id, help_text, parse_mode='Markdown')

@bot.message_handler(commands=['reset'])
def handle_reset(message):
    """Handle command /reset dengan atau tanpa foto"""
    user_id = message.from_user.id
    cs_user = message.from_user
    
    try:
        # Parse command: /reset ID GAME
        parts = message.text.split(maxsplit=2)
        
        if len(parts) < 3:
            bot.reply_to(message, 
                "❌ *Format salah!*\n\n"
                "Gunakan: `/reset ID_AKUN NAMA_GAME`\n"
                "Contoh: `/reset Tampias77 G200M`\n\n"
                "Bisa juga kirim foto sebagai bukti deposit.",
                parse_mode='Markdown'
            )
            return
        
        account_id = parts[1]
        game_name = parts[2]
        
        # Generate request ID
        request_id = f"X{random.randint(1000, 9999)}"
        
        # Simpan ke database (tanpa foto dulu)
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO reset_requests 
        (request_id, cs_user_id, cs_username, target_account_id, game_name)
        VALUES (?, ?, ?, ?, ?)
        ''', (request_id, cs_user.id, cs_user.username, account_id, game_name))
        conn.commit()
        conn.close()
        
        # Konfirmasi ke user
        bot.reply_to(message,
            f"✅ *REQUEST DITERIMA!*\n\n"
            f"📋 Kode: `{request_id}`\n"
            f"👤 ID: `{account_id}`\n"
            f"🎮 Game: {game_name}\n\n"
            "⏳ Menunggu approval admin...\n\n"
            "📸 *Bisa kirim bukti deposit (foto) sekarang juga*",
            parse_mode='Markdown'
        )
        
        # Langsung kirim notifikasi ke admin
        send_to_admin(request_id, account_id, game_name, cs_user.username)
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(content_types=['photo'])
def handle_photo_anytime(message):
    """Handle foto yang dikirim kapan saja (relate ke request terakhir)"""
    user_id = message.from_user.id
    
    # Cari request terakhir dari user ini yang masih pending
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
    SELECT request_id, target_account_id, game_name, photo_path
    FROM reset_requests 
    WHERE cs_user_id = ? AND status = 'pending' 
    ORDER BY request_time DESC LIMIT 1
    ''', (user_id,))
    
    result = cursor.fetchone()
    
    if result:
        request_id, account_id, game_name, existing_photo = result
        
        # Jika sudah ada foto sebelumnya, skip
        if existing_photo:
            bot.reply_to(message, "⚠️ Request ini sudah ada bukti deposit sebelumnya.")
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
        cursor.execute('''
        UPDATE reset_requests SET photo_path = ? WHERE request_id = ?
        ''', (photo_path, request_id))
        conn.commit()
        
        # Konfirmasi ke user
        bot.reply_to(message,
            f"✅ *BUKTI DEPOSIT DITERIMA!*\n\n"
            f"📋 Kode: `{request_id}`\n"
            f"👤 ID: `{account_id}`\n"
            f"🎮 Game: {game_name}\n"
            f"📸 Bukti: ✅ Tersedia\n\n"
            "Request diperbarui dengan bukti.",
            parse_mode='Markdown'
        )
        
        # Update notifikasi ke admin
        update_admin_with_photo(request_id, photo_path)
        
    else:
        bot.reply_to(message, 
            "❌ Tidak ada request pending.\n"
            "Kirim dulu: `/reset ID GAME`",
            parse_mode='Markdown'
        )
    
    conn.close()

def send_to_admin(request_id, account_id, game_name, cs_username):
    """Kirim notifikasi awal ke admin"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_reset = types.InlineKeyboardButton("✅ RESET", callback_data=f"ok_{request_id}")
    btn_decline = types.InlineKeyboardButton("❌ TOLAK", callback_data=f"no_{request_id}")
    markup.add(btn_reset, btn_decline)
    
    admin_msg = (
        f"🔄 *REQUEST BARU*\n"
        f"━━━━━━━━━━━━━━\n"
        f"📋 Kode: `{request_id}`\n"
        f"👤 ID: `{account_id}`\n"
        f"🎮 Game: {game_name}\n"
        f"🛡️ CS: @{cs_username}\n"
        f"📸 Bukti: ❌ Belum ada\n"
        f"⏰ Waktu: {datetime.now().strftime('%H:%M:%S')}\n\n"
        f"*User bisa kirim foto nanti*"
    )
    
    bot.send_message(ADMIN_CHAT_ID, admin_msg, parse_mode='Markdown', reply_markup=markup)

def update_admin_with_photo(request_id, photo_path):
    """Update admin dengan foto yang baru dikirim"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
    SELECT target_account_id, game_name, cs_username
    FROM reset_requests WHERE request_id = ?
    ''', (request_id,))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        account_id, game_name, cs_username = result
        
        # Kirim foto ke admin
        with open(photo_path, 'rb') as photo:
            bot.send_photo(
                ADMIN_CHAT_ID, 
                photo,
                caption=f"📸 *BUKTI DITAMBAHKAN*\nRequest: {request_id}\nID: {account_id}\nCS: @{cs_username}",
                parse_mode='Markdown'
            )

# ========== APPROVAL SYSTEM ==========
@bot.callback_query_handler(func=lambda call: call.data.startswith("ok_"))
def approve_request(call):
    request_id = call.data.split("_")[1]
    new_password = generate_password()
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Ambil data request
    cursor.execute('''
    SELECT cs_user_id, target_account_id, game_name, photo_path 
    FROM reset_requests WHERE request_id = ?
    ''', (request_id,))
    
    result = cursor.fetchone()
    
    if result:
        cs_user_id, account_id, game_name, photo_path = result
        
        # Update database
        cursor.execute('''
        UPDATE reset_requests 
        SET status = 'completed',
            new_password = ?,
            admin_id = ?,
            process_time = CURRENT_TIMESTAMP
        WHERE request_id = ?
        ''', (new_password, call.from_user.id, request_id))
        
        conn.commit()
        
        # Kirim password ke CS
        message_text = (
            f"✅ *PASSWORD READY!*\n\n"
            f"📋 Kode: `{request_id}`\n"
            f"👤 ID: `{account_id}`\n"
            f"🎮 Game: {game_name}\n"
            f"🔐 Password: `{new_password}`\n\n"
            f"⚠️ Berikan ke user segera!"
        )
        
        # Jika ada foto, kirim juga
        if photo_path and os.path.exists(photo_path):
            try:
                with open(photo_path, 'rb') as photo:
                    bot.send_photo(cs_user_id, photo, caption=message_text, parse_mode='Markdown')
            except:
                bot.send_message(cs_user_id, message_text, parse_mode='Markdown')
        else:
            bot.send_message(cs_user_id, message_text, parse_mode='Markdown')
        
        # Update pesan admin
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"✅ SELESAI\nKode: {request_id}\nPassword: {new_password}",
            reply_markup=None,
            parse_mode='Markdown'
        )
        
        bot.answer_callback_query(call.id, f"Password: {new_password}")
    
    conn.close()

@bot.callback_query_handler(func=lambda call: call.data.startswith("no_"))
def decline_request(call):
    request_id = call.data.split("_")[1]
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT cs_user_id FROM reset_requests WHERE request_id = ?
    ''', (request_id,))
    
    result = cursor.fetchone()
    
    if result:
        cs_user_id = result[0]
        bot.send_message(cs_user_id, f"❌ Request {request_id} DITOLAK oleh admin.")
    
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
        text=f"❌ DITOLAK\nKode: {request_id}",
        reply_markup=None
    )
    
    bot.answer_callback_query(call.id, "Request ditolak")

# ========== COMMAND LAINNYA ==========
@bot.message_handler(commands=['status'])
def check_status(message):
    try:
        request_id = message.text.split()[1]
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('''
        SELECT request_id, target_account_id, status, new_password
        FROM reset_requests WHERE request_id = ?
        ''', (request_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            bot.reply_to(message, "❌ Kode tidak ditemukan.")
            return
        
        req_id, account_id, status, password = result
        
        status_msg = {
            'pending': '⏳ Menunggu',
            'completed': '✅ Selesai',
            'rejected': '❌ Ditolak'
        }.get(status, status)
        
        response = (
            f"📊 *STATUS REQUEST*\n"
            f"━━━━━━━━━━━━━━\n"
            f"📋 Kode: `{req_id}`\n"
            f"👤 ID: `{account_id}`\n"
            f"📈 Status: {status_msg}\n"
        )
        
        if password:
            response += f"🔐 Password: `{password}`\n"
            
        bot.reply_to(message, response, parse_mode='Markdown')
        
    except:
        bot.reply_to(message, "Format: /status [kode]\nContoh: /status X1234")

@bot.message_handler(commands=['admin', 'pending'])
def admin_commands(message):
    if message.from_user.id != ADMIN_CHAT_ID:
        bot.reply_to(message, "❌ Hanya admin!")
        return
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    if 'pending' in message.text:
        cursor.execute('''
        SELECT request_id, target_account_id, cs_username, request_time
        FROM reset_requests WHERE status = 'pending'
        ORDER BY request_time ASC
        ''')
        
        requests = cursor.fetchall()
        
        if not requests:
            bot.reply_to(message, "✅ Tidak ada request pending.")
        else:
            response = "⏳ *REQUEST PENDING:*\n━━━━━━━━━━━━━━\n"
            for req in requests:
                req_id, account_id, cs_user, req_time = req
                response += f"📋 `{req_id}`\n👤 `{account_id}`\n🛡️ @{cs_user}\n⏰ {req_time}\n━━━━━━━━━━━━━━\n"
            
            bot.reply_to(message, response, parse_mode='Markdown')
    else:
        cursor.execute("SELECT COUNT(*) FROM reset_requests WHERE status = 'pending'")
        pending = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM reset_requests")
        total = cursor.fetchone()[0]
        
        bot.reply_to(message,
            f"👑 *ADMIN PANEL*\n\n"
            f"⏳ Pending: {pending} request\n"
            f"📊 Total: {total} request\n\n"
            f"Commands:\n"
            f"/pending - Lihat request pending\n"
            f"/status [kode] - Cek status",
            parse_mode='Markdown'
        )
    
    conn.close()

# ========== FOR GRUP SUPPORT ==========
@bot.message_handler(func=lambda message: message.chat.type in ['group', 'supergroup'] and '/reset' in message.text)
def handle_group_reset(message):
    """Handle jika ada yang ketik /reset di grup"""
    user = message.from_user
    bot.reply_to(message,
        f"👋 Hai @{user.username}!\n\n"
        "Untuk request reset password:\n"
        "1. Chat langsung ke @Xsistem_Bot\n"
        "2. Kirim perintah: `/reset ID_AKUN NAMA_GAME`\n\n"
        "⚠️ *Password akan dikirim via chat pribadi*",
        parse_mode='Markdown',
        reply_to_message_id=message.message_id
    )

if __name__ == "__main__":
    print("=" * 50)
    print("🚀 Starting X-Sistem Bot v3.0")
    print("=" * 50)
    init_db()
    print(f"✅ Admin ID: {ADMIN_CHAT_ID}")
    print(f"📁 Upload folder: {UPLOAD_FOLDER}")
    print("🤖 Bot is running! Press Ctrl+C to stop.")
    print("=" * 50)

    bot.polling(none_stop=True)
    if __name__ == "__main__":
    try:
        print("=" * 50)
        print("🚀 Attempting to start bot...")
        print(f"Token length: {len(TOKEN) if TOKEN else 'TOKEN EMPTY!'}")
        print(f"Admin ID: {ADMIN_CHAT_ID}")
        print("=" * 50)
        
        init_db()
        print("✅ Database initialized")
        
        print("🤖 Starting bot polling...")
        bot.polling(none_stop=True, timeout=60)
        
    except Exception as e:
        print(f"❌ CRITICAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        # Keep container alive for debugging
        while True:
            time.sleep(10)
