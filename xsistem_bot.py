import telebot
import random
import string
from telebot import types
import time
import requests
import os
import threading
import tempfile  # https://github.com/vinsatyargha-pixel/xsistem_bot/blob/main/xsistem_bot.py
from flask import Flask
import re
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import logging

# ================= SETUP LOGGING =================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ================= CONFIG =================
TOKEN = "8087735462:AAGII-XvO3hJy3YgDd3b0vjiIHjnQCn4Ej4"
bot = telebot.TeleBot(TOKEN)

ADMIN_USERNAMES = ["Vingeance", "bangjoshh"]
GROUP_ID = -1003855148883
SPREADSHEET_ID = "1Fl2YsqEQ7P4lWyesFxKiqZbPq233dPovmXocmn0x_6Y"
TARGET_SHEET_NAME = "X"

pending_injections = {}

# ========== FLASK SERVER ==========
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "🤖 X-SISTEM BOT IS RUNNING", 200

@web_app.route('/health')
def health():
    return "✅ OK", 200

@web_app.route('/ping')
def ping():
    return "🏓 PONG", 200

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"🌐 Starting Flask server on port {port}")
    web_app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# ========== AUTO PINGER ==========
def ping_self():
    logger.info("⏰ Starting auto-pinger...")
    time.sleep(30)
    while True:
        try:
            url = "https://cek-rekening-fi8f.onrender.com"
            response = requests.get(url + "/ping", timeout=10)
            now = time.strftime("%H:%M:%S")
            if response.status_code == 200:
                logger.info(f"✅ [{now}] Ping successful")
            else:
                logger.warning(f"⚠️ [{now}] Ping failed")
        except Exception as e:
            logger.error(f"❌ [{now}] Ping error: {e}")
        time.sleep(480)

# ========== GOOGLE SHEETS ==========
def get_sheet():
    try:
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
        if os.getenv("GOOGLE_CREDENTIALS_JSON"):
            import json
            creds_dict = json.loads(os.getenv("GOOGLE_CREDENTIALS_JSON"))
            creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        else:
            creds = Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
        
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        
        all_sheets = spreadsheet.worksheets()
        for sheet in all_sheets:
            if sheet.title.upper() == TARGET_SHEET_NAME.upper():
                return sheet
        return None
    except Exception as e:
        logger.error(f"❌ Google Sheets error: {e}")
        return None

def find_empty_row(sheet):
    try:
        column_d = sheet.col_values(4)
        for i in range(3, len(column_d) + 2):
            if i >= len(column_d) or column_d[i] == "":
                return i + 1
        return len(column_d) + 1
    except Exception as e:
        return 4

# ========== SUNIK BANK ==========
def parse_injection_text(text):
    patterns = {
        'no_rek': r"No Rek Bank\s*:\s*(.+)",
        'jenis_bank': r"Jenis Bank\s*:\s*(.+)",
        'nama_bank': r"Nama Bank\s*:\s*(.+)",
        'nominal': r"Nominal Suntik\s*:\s*(.+)",
        'saldo_akhir': r"Saldo Akhir Bank\s*:\s*(.+)",
        'asset': r"Asset\s*:\s*(.+)",
        'wallet': r"Wallet Addres\s*:\s*(.+)",
        'officer': r"OFFICER\s*:\s*(.+)"
    }
    extracted = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        extracted[key] = match.group(1).strip() if match else "N/A"
    return extracted

def update_spreadsheet_all_data(data, approver_name):
    try:
        sheet = get_sheet()
        if not sheet:
            return False
        target_row = find_empty_row(sheet)
        sheet.update(range_name=f"D{target_row}", values=[[data['no_rek']]])
        sheet.update(range_name=f"G{target_row}", values=[[data['nominal']]])
        sheet.update(range_name=f"H{target_row}", values=[[data['saldo_akhir']]])
        sheet.update(range_name=f"K{target_row}", values=[[approver_name]])
        logger.info(f"✅ Data saved to row {target_row}")
        return True
    except Exception as e:
        logger.error(f"Failed update: {e}")
        return False

def send_admin_confirmation(data, original_message):
    text_data = data['text_data']
    approval_msg = (
        "💉 **PERMINTAAN SUNTIK BANK**\n\n"
        f"JENIS BANK : {text_data['jenis_bank']}\n"
        f"📊 Saldo Akhir: {text_data['saldo_akhir']}\n"
        f"No Rek Bank : {text_data['no_rek']}\n"
        f"📌 Asset: {text_data['asset']}\n"
        f"👤 Officer: {data['officer']}\n\n"
        "Konfirmasi Admin:\n\nAPPROVED atau DECLINE"
    )
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ APPROVED", callback_data=f"inj_approve_{data['message_id']}"),
        types.InlineKeyboardButton("❌ DECLINE", callback_data=f"inj_decline_{data['message_id']}")
    )
    sent_msg = bot.send_message(GROUP_ID, approval_msg, reply_markup=markup, parse_mode='HTML')
    if data['is_photo'] and data['photo_id']:
        try:
            bot.send_photo(GROUP_ID, data['photo_id'], caption=f"📸 Screenshot dari {data['officer']}")
        except:
            pass
    pending_injections[data['message_id']] = {**text_data, 'officer': data['officer'], 'user_id': data['user_id'], 'is_photo': data['is_photo'], 'admin_message_id': sent_msg.message_id}

# ========== REPORT ==========
def parse_report_text(text):
    try:
        data = {'original_text': text}
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        first_line = lines[0].upper() if lines else ""
        report_types = ['REPORT CROSSBANK', 'REPORT PENDINGAN', 'REPORT PROCESS PENDINGAN', 'REPORT MISTAKE', 'REPORT REFUND', 'REPORT FEE', 'REPORT KODE UNIK', 'REPORT BALANCING BANK']
        for report_type in report_types:
            if report_type in first_line:
                data['report_type'] = report_type
                break
        for line in lines[1:]:
            if ':' in line:
                parts = line.split(':', 1)
                if len(parts) == 2:
                    key = parts[0].strip().lower().replace(' ', '_')
                    value = parts[1].strip()
                    data[key] = value
        return data
    except Exception as e:
        return {'original_text': text}

def save_crossbank_report(data):
    try:
        web_app_url = "https://script.google.com/macros/s/AKfycbxstoyv-fjhTU9AifzvK3NQXhSoTIQ3mDWoerRPYAguO8UGjWuFlWUqZQ6KXGzVlDmTPg/exec"
        response = requests.post(web_app_url, json={'message': {'text': data['original_text']}}, timeout=10)
        return (True, "OK") if response.status_code == 200 else (False, f"Error {response.status_code}")
    except Exception as e:
        return False, str(e)

def handle_report_from_caption(caption_text, message):
    try:
        data = parse_report_text(caption_text)
        if 'officer' not in data or not data['officer']:
            data['officer'] = message.from_user.username or message.from_user.first_name
        data['original_text'] = caption_text
        success, result = save_crossbank_report(data)
        bot.reply_to(message, "✅ REPORT BERHASIL DISIMPAN!" if success else f"❌ Gagal: {result}")
    except Exception as e:
        bot.reply_to(message, "❌ Error")

def handle_report_generic(message, report_type):
    try:
        text = message.text.strip() if message.text else ""
        if not text:
            return
        data = parse_report_text(text)
        if 'officer' not in data or not data['officer']:
            data['officer'] = message.from_user.username or message.from_user.first_name
        data['original_text'] = text
        success, result = save_crossbank_report(data)
        bot.reply_to(message, "✅ REPORT BERHASIL DISIMPAN!" if success else f"❌ Gagal: {result}")
    except Exception as e:
        bot.reply_to(message, "❌ Error")

# ========== FUNGSI RESET ==========
def buat_password():
    import random
    import string
    
    # Wajib: 1 huruf besar + 1 angka
    huruf_besar = random.choice(string.ascii_uppercase)
    angka_wajib = random.choice(string.digits)
    
    # Sisa 6 karakter: huruf kecil
    sisa = ''.join(random.choices(string.ascii_lowercase, k=6))
    
    # Gabung dan acak
    password_list = list(huruf_besar + angka_wajib + sisa)
    random.shuffle(password_list)
    
    return ''.join(password_list)

def extract_reset_info(text):
    """Extract user_id dan asset dari teks reset"""
    text_lower = text.lower()
    
    for cmd in ['/reset', '/repass', '/repas']:
        cmd_pos = text_lower.find(cmd)
        if cmd_pos != -1:
            after_cmd = text[cmd_pos + len(cmd):].strip()
            
            # Hapus titik dua jika ada
            if after_cmd.startswith(':'):
                after_cmd = after_cmd[1:].strip()
            elif after_cmd.startswith('：'):
                after_cmd = after_cmd[1:].strip()
            
            # Split dan ambil 2 kata pertama
            parts = after_cmd.split()
            if len(parts) >= 2:
                user_id = parts[0].strip()
                asset = parts[1].strip()
                user_id = re.sub(r'[^\w\-]', '', user_id)
                asset = re.sub(r'[^\w\-]', '', asset)
                if user_id and asset:
                    return user_id, asset
            
            # Coba format dash
            if '-' in after_cmd:
                parts_dash = after_cmd.split('-', 1)
                if len(parts_dash) >= 2:
                    user_id = parts_dash[0].strip()
                    asset = parts_dash[1].split()[0].strip() if parts_dash[1] else ''
                    user_id = re.sub(r'[^\w\-]', '', user_id)
                    asset = re.sub(r'[^\w\-]', '', asset)
                    if user_id and asset:
                        return user_id, asset
    
    return None, None

# ========== HANDLER FOTO (GABUNGAN SEMUA - CASE INSENSITIVE) ==========
@bot.message_handler(content_types=['photo'])
def handle_photo_with_caption(message):
    caption = message.caption or ""
    logger.info(f"📸 Photo from @{message.from_user.username}")
    logger.info(f"   Caption: {caption[:200]}...")
    
    # Convert ke lower untuk pengecekan case insensitive
    caption_lower = caption.lower()
    
    # PRIORITY 1: SUNTIK BANK (case insensitive)
    if "tolong suntik dari rek tampungan kps" in caption_lower:
        logger.info("   → Detected: SUNTIK BANK")
        
        parsed_data = parse_injection_text(caption)
        
        # Log hasil parsing
        logger.info(f"   Parsed: no_rek={parsed_data['no_rek']}, nominal={parsed_data['nominal']}")
        
        # Jika officer tidak ditemukan, pakai username pengirim
        if parsed_data['officer'] == "N/A":
            parsed_data['officer'] = message.from_user.username or message.from_user.first_name
        
        # Jika asset tidak ditemukan, kasih default
        if parsed_data['asset'] == "N/A":
            parsed_data['asset'] = "Tidak diketahui"
        
        injection_data = {
            'text_data': parsed_data,
            'user_id': message.from_user.id,
            'officer': message.from_user.username or message.from_user.first_name,
            'message_id': message.message_id,
            'is_photo': True,
            'photo_id': message.photo[-1].file_id
        }
        
        send_admin_confirmation(injection_data, message)
        bot.reply_to(message, "✅ Permintaan suntik bank telah dikirim ke admin untuk konfirmasi.")
        return
    
    # PRIORITY 2: REPORT (case insensitive)
    caption_upper = caption.upper()
    report_keywords = ['REPORT CROSSBANK', 'REPORT PENDINGAN', 'REPORT PROCESS PENDINGAN',
                       'REPORT MISTAKE', 'REPORT REFUND', 'REPORT FEE',
                       'REPORT KODE UNIK', 'REPORT BALANCING BANK']
    for keyword in report_keywords:
        if keyword in caption_upper:
            logger.info(f"   → Detected: REPORT")
            handle_report_from_caption(caption, message)
            return
    
    # PRIORITY 3: RESET PASSWORD (case insensitive)
    reset_commands = ['/reset', '/repass', '/repas']
    if any(cmd in caption_lower for cmd in reset_commands):
        logger.info("   → Detected: RESET PASSWORD")
        user_id, asset = extract_reset_info(caption)
        
        if user_id and asset:
            logger.info(f"   → Reset: User={user_id}, Asset={asset}")
            markup = types.InlineKeyboardMarkup(row_width=2)
            markup.add(
                types.InlineKeyboardButton("✅ Reset", callback_data=f"ok_{message.from_user.id}_{user_id}_{asset}"),
                types.InlineKeyboardButton("❌ Tolak", callback_data=f"no_{message.from_user.id}")
            )
            bot.reply_to(
                message,
                f"🔔 *RESET REQUEST*\n\n👤 CS: {message.from_user.first_name}\n🆔 User: `{user_id}`\n🎮 Asset: `{asset}`\n\n**PILIH:**",
                reply_markup=markup,
                parse_mode='HTML'
            )
        else:
            logger.warning(f"   → Failed to extract reset info")
        return
    
    # Jika tidak ada yang cocok
    logger.info("   → Ignored (no matching pattern)")

# ========== HANDLER TEXT UNTUK SUNTIK BANK (CASE INSENSITIVE) ==========
@bot.message_handler(func=lambda m: m.text and "tolong suntik dari rek tampungan kps" in m.text.lower())
def handle_injection_request(message):
    # Skip kalo mengandung command reset/report
    if any(cmd in message.text.lower() for cmd in ['/reset', '/repass', '/repas', 'report']):
        return
    
    logger.info(f"📝 Text injection from {message.from_user.username}")
    parsed_data = parse_injection_text(message.text)
    if parsed_data['officer'] == "N/A":
        parsed_data['officer'] = message.from_user.username or message.from_user.first_name
    injection_data = {
        'text_data': parsed_data,
        'user_id': message.from_user.id,
        'officer': message.from_user.username or message.from_user.first_name,
        'message_id': message.message_id,
        'is_photo': False,
        'photo_id': None
    }
    send_admin_confirmation(injection_data, message)
    bot.reply_to(message, "✅ Permintaan suntik bank telah dikirim ke admin.")

# ========== HANDLER TEXT UNTUK RESET (CASE INSENSITIVE) ==========
@bot.message_handler(func=lambda m: m.text and any(
    cmd in m.text.lower() for cmd in ['/reset', '/repass', '/repas']
))
def handle_reset_text(message):
    # Skip suntik bank
    if "tolong suntik dari rek tampungan kps" in message.text.lower():
        return
    
    # Skip report
    text_upper = message.text.upper()
    report_keywords = ['REPORT CROSSBANK', 'REPORT PENDINGAN', 'REPORT PROCESS PENDINGAN',
                       'REPORT MISTAKE', 'REPORT REFUND', 'REPORT FEE',
                       'REPORT KODE UNIK', 'REPORT BALANCING BANK']
    for keyword in report_keywords:
        if keyword in text_upper:
            return
    
    user_id, asset = extract_reset_info(message.text)
    if not user_id or not asset:
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ Reset", callback_data=f"ok_{message.from_user.id}_{user_id}_{asset}"),
        types.InlineKeyboardButton("❌ Tolak", callback_data=f"no_{message.from_user.id}")
    )
    bot.reply_to(
        message,
        f"🔔 *RESET REQUEST*\n\n👤 CS: {message.from_user.first_name}\n🆔 User: `{user_id}`\n🎮 Asset: `{asset}`\n\n**PILIH:**",
        reply_markup=markup,
        parse_mode='HTML'
    )

# ========== HANDLER REPORT TEXT (CASE INSENSITIVE) ==========
@bot.message_handler(func=lambda m: m.text and m.text.upper().strip().startswith('REPORT CROSSBANK'))
def handle_crossbank_message(message): handle_report_generic(message, 'CROSSBANK')

@bot.message_handler(func=lambda m: m.text and m.text.upper().strip().startswith('REPORT PENDINGAN'))
def handle_pendingan_message(message): handle_report_generic(message, 'PENDINGAN')

@bot.message_handler(func=lambda m: m.text and m.text.upper().strip().startswith('REPORT PROCESS PENDINGAN'))
def handle_process_pendingan_message(message): handle_report_generic(message, 'PROCESS PENDINGAN')

@bot.message_handler(func=lambda m: m.text and m.text.upper().strip().startswith('REPORT MISTAKE'))
def handle_mistake_message(message): handle_report_generic(message, 'MISTAKE')

@bot.message_handler(func=lambda m: m.text and m.text.upper().strip().startswith('REPORT REFUND'))
def handle_refund_message(message): handle_report_generic(message, 'REFUND')

@bot.message_handler(func=lambda m: m.text and m.text.upper().strip().startswith('REPORT FEE'))
def handle_fee_message(message): handle_report_generic(message, 'FEE')

@bot.message_handler(func=lambda m: m.text and m.text.upper().strip().startswith('REPORT KODE UNIK'))
def handle_kode_unik_message(message): handle_report_generic(message, 'KODE UNIK')

@bot.message_handler(func=lambda m: m.text and m.text.upper().strip().startswith('REPORT BALANCING BANK'))
def handle_balancing_bank_message(message): handle_report_generic(message, 'BALANCING BANK')

# ========== CALLBACK SUNTIK ==========
@bot.callback_query_handler(func=lambda call: call.data.startswith('inj_'))
def handle_injection_callback(call):
    try:
        parts = call.data.split('_')
        if len(parts) < 3:
            bot.answer_callback_query(call.id, "❌ Format tidak valid")
            return
        action = parts[1]
        msg_id = int(parts[2])
        caller_username = call.from_user.username
        
        # MODIFIKASI: Cek apakah user adalah @OfficerGroupX (ditolak)
        if caller_username == "OfficerGroupX":
            bot.answer_callback_query(call.id, "❌ Maaf, Anda tidak memiliki izin untuk menyetujui suntik bank!", show_alert=True)
            logger.warning(f"⚠️ {caller_username} diblokir dari approve suntik bank")
            return
        
        data = pending_injections.get(msg_id)
        if not data:
            bot.answer_callback_query(call.id, "❌ Data tidak ditemukan")
            return
        
        if action == "approve":
            # MODIFIKASI: Semua user kecuali OfficerGroupX bisa approve
            # Tapi tetap pakai nama approver sesuai username
            approver_name = caller_username  # Pakai username langsung
            
            success = update_spreadsheet_all_data(data, approver_name)
            response_text = "✅ Disetujui & tercatat" if success else "⚠️ Disetujui tapi GAGAL tercatat"
            new_text = f"✅ **DISETUJUI** oleh @{caller_username}\n✍️ Approver: {approver_name}\n\n🏦 Bank: {data.get('jenis_bank', 'N/A')}\n💳 Rekening: {data.get('no_rek', 'N/A')}\n💰 Nominal: {data.get('nominal', 'N/A')}\n📊 Saldo: {data.get('saldo_akhir', 'N/A')}\n👤 Officer: {data.get('officer', 'N/A')}"
            try:
                bot.edit_message_text(chat_id=GROUP_ID, message_id=call.message.message_id, text=new_text, parse_mode='HTML')
            except:
                pass
            bot.answer_callback_query(call.id, response_text)
        elif action == "decline":
            try:
                bot.edit_message_text(chat_id=GROUP_ID, message_id=call.message.message_id, text=f"❌ **DITOLAK** oleh @{caller_username}", parse_mode='HTML')
            except:
                pass
            bot.answer_callback_query(call.id, "❌ Ditolak")
        del pending_injections[msg_id]
    except Exception as e:
        logger.error(f"Callback error: {e}")

# ========== CALLBACK RESET ==========
@bot.callback_query_handler(func=lambda call: call.data.startswith('ok_') or call.data.startswith('no_'))
def handle_reset_callback(call):
    try:
        # ===== AMBIL USERNAME YANG KLIK =====
        caller_username = call.from_user.username
        if not caller_username:
            caller_username = call.from_user.first_name or "Unknown"
        
        # ===== CEK @OfficerGroupX (GA BOLEH KLIK) =====
        if caller_username and caller_username.lower() == "officergroupx":
            bot.answer_callback_query(call.id, "❌ Maaf, Anda tidak memiliki izin untuk mereset password!", show_alert=True)
            logger.warning(f"⚠️ {caller_username} diblokir dari reset password")
            return
        
        # ===== PROSES APPROVE =====
        if call.data.startswith('ok_'):
            # Format: ok_{cs_id}_{user_id}_{asset}
            parts = call.data.split('_')
            
            if len(parts) < 4:
                bot.answer_callback_query(call.id, "❌ Data tidak valid")
                return
            
            cs_id = parts[1]
            
            # user_id bisa mengandung underscore, gabungkan dari index 2 sampai sebelum terakhir
            if len(parts) > 4:
                user_id = '_'.join(parts[2:-1])
            else:
                user_id = parts[2]
            
            asset = parts[-1]
            
            # ===== INI LOG YANG LU MAKSUD =====
            # caller_username udah dapet username lengkap termasuk underscore
            logger.info(f"✅ RESET APPROVED by @{caller_username} for {user_id} ({asset})")
            
            password = buat_password()
            
            # Kirim password ke group
            bot.send_message(
                call.message.chat.id, 
                f"{user_id} - {asset}\nPassword baru : {password}"
            )
            
            # Edit pesan asli menjadi approved
            try:
                bot.edit_message_text(
                    f"✅ *RESET DISETUJUI*\n\nUser: `{user_id}`\nAsset: `{asset}`\nPassword: `{password}`\n\n👤 Disetujui oleh: @{caller_username}", 
                    call.message.chat.id, 
                    call.message.message_id, 
                    parse_mode='HTML'
                )
                bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
            except Exception as e:
                logger.error(f"Gagal edit pesan: {e}")
            
            bot.answer_callback_query(call.id, "✅ Password dikirim")
        
        # ===== PROSES DECLINE =====
        elif call.data.startswith('no_'):
            parts = call.data.split('_')
            
            if len(parts) >= 3:
                if len(parts) > 3:
                    user_id = '_'.join(parts[2:])
                else:
                    user_id = parts[2]
            else:
                user_id = "Unknown"
            
            logger.info(f"❌ RESET DECLINED by @{caller_username} for {user_id}")
            
            try:
                bot.edit_message_text(
                    f"❌ *RESET DITOLAK*\n\nUser: `{user_id}`\n👤 Ditolak oleh: @{caller_username}", 
                    call.message.chat.id, 
                    call.message.message_id, 
                    parse_mode='HTML'
                )
                bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
            except Exception as e:
                logger.error(f"Gagal edit pesan: {e}")
            
            bot.send_message(call.message.chat.id, f"❌ Permintaan reset untuk {user_id} ditolak oleh @{caller_username}")
            bot.answer_callback_query(call.id, "❌ Ditolak")
            
    except Exception as e:
        logger.error(f"Reset callback error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        try:
            bot.answer_callback_query(call.id, "❌ Terjadi kesalahan")
        except:
            pass

# ========== COMMAND HANDLERS ==========
@bot.message_handler(commands=['formatreset'])
def handle_format_reset(message):
    bot.reply_to(message, """📋 CONTOH FORMAT RESET:

/reset : idd1005aw XLY
/reset idd1005aw XLY
/repas GGWP123 XLY
/repass GGWP123-XLY

✅ Bisa pakai foto, yang penting captionnya berisi command di atas""")

@bot.message_handler(commands=['formatreport'])
def handle_format_report(message):
    bot.reply_to(message, """📋 FORMAT REPORT:

REPORT CROSSBANK / REPORT PENDINGAN / REPORT MISTAKE / REPORT REFUND / REPORT FEE / REPORT KODE UNIK / REPORT BALANCING BANK

ASET: BTC
USER ID: xxx
BANK MEMBER: BCA xxx
BANK ASSET: BCA xxx
NO TICKET: xxx
AMOUNT: xxx
CASE: xxx
OFFICER: xxx""")

@bot.message_handler(commands=['report'])
def handle_report_command(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📋 CROSSBANK", callback_data="report_crossbank"),
        types.InlineKeyboardButton("⏳ PENDINGAN", callback_data="report_pendingan"),
        types.InlineKeyboardButton("🔄 PROCESS PENDINGAN", callback_data="report_process_pendingan"),
        types.InlineKeyboardButton("❌ MISTAKE", callback_data="report_mistake"),
        types.InlineKeyboardButton("↩️ REFUND", callback_data="report_refund"),
        types.InlineKeyboardButton("💰 FEE", callback_data="report_fee"),
        types.InlineKeyboardButton("🔢 KODE UNIK", callback_data="report_kode_unik"),
        types.InlineKeyboardButton("⚖️ BALANCING BANK", callback_data="report_balancing_bank")
    )
    bot.reply_to(message, "📊 *PILIH JENIS REPORT:*", reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith('report_'))
def handle_report_type(call):
    formats = {
        'crossbank': "REPORT CROSSBANK\nASET: BTC\nUSER ID: 123456\nBANK MEMBER: BCA\nBANK ASSET: Binance\nNO TICKET: TKT789\nAMOUNT: 5000000\nCASE: Fraud\nOFFICER: John Doe",
        'pendingan': "REPORT PENDINGAN\nASET: BTC\nUSER ID: 123456\nBANK MEMBER: BCA\nBANK ASSET: Binance\nNO TICKET: TKT789\nAMOUNT: 5000000\nCASE: Input Pendingan Deposit\nOFFICER: John Doe",
        'process_pendingan': "REPORT PROCESS PENDINGAN\nASET: BTC\nUSER ID: 123456\nBANK MEMBER: BCA\nBANK ASSET: Binance\nNO TICKET: TKT789\nAMOUNT: 5000000\nCASE: Proses Pendingan Deposit\nOFFICER: John Doe",
        'mistake': "REPORT MISTAKE\nASET: BTC\nUSER ID: 123456\nBANK MEMBER: BCA\nBANK ASSET: Binance\nNO TICKET: TKT789\nAMOUNT: 5000000\nCASE: Kesalahan Input Data\nOFFICER: John Doe",
        'refund': "REPORT REFUND\nASET: BTC\nUSER ID: 123456\nBANK MEMBER: BCA\nBANK ASSET: Binance\nNO TICKET: TKT789\nAMOUNT: 5000000\nCASE: Pengembalian Dana\nOFFICER: John Doe",
        'fee': "REPORT FEE\nASET: BTC\nUSER ID: 123456\nBANK MEMBER: BCA\nBANK ASSET: Binance\nNO TICKET: TKT789\nAMOUNT: 5000000\nCASE: Biaya Admin\nOFFICER: John Doe",
        'kode_unik': "REPORT KODE UNIK\nASET: BTC\nUSER ID: 123456\nBANK MEMBER: BCA\nBANK ASSET: Binance\nNO TICKET: TKT789\nAMOUNT: 5000000\nCASE: Kode Unik Tidak Sesuai\nOFFICER: John Doe",
        'balancing_bank': "REPORT BALANCING BANK\nASET: BTC\nUSER ID: 123456\nBANK MEMBER: BCA\nBANK ASSET: Binance\nNO TICKET: TKT789\nAMOUNT: 5000000\nCASE: Selisih Saldo Bank\nOFFICER: John Doe"
    }
    report_type = call.data.replace('report_', '')
    bot.edit_message_text(f"📋 *FORMAT {report_type.upper()}*\n\n{formats.get(report_type, '')}\n\n*Kirim pesan dengan format di atas*", call.message.chat.id, call.message.message_id, parse_mode='Markdown')
    bot.answer_callback_query(call.id, f"Format {report_type.upper()}")

# ========== IGNORE MEDIA LAIN ==========
@bot.message_handler(content_types=['document', 'video', 'audio', 'voice', 'sticker', 'location', 'contact', 'poll', 'animation'])
def ignore_other_media(message):
    pass

# ========== BOT RUNNER ==========
def run_bot():
    logger.info("Starting Telegram Bot...")
    sheet = get_sheet()
    if sheet:
        logger.info(f"✅ Google Sheets connected")
    else:
        logger.error("❌ Google Sheets FAILED")
    bot.polling(none_stop=True, timeout=30)

if __name__ == "__main__":
    print("=" * 60)
    print("🤖 X-SISTEM BOT - CASE INSENSITIVE")
    print("=" * 60)
    print("💉 Suntik Bank: OK (tolong suntik / TOLONG SUNTIK / ToLong SunTik)")
    print("🔄 Reset: OK (/reset / /RESET / /ReSeT)")
    print("📊 Report: OK (REPORT / Report / report)")
    print("=" * 60)
    
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    pinger_thread = threading.Thread(target=ping_self, daemon=True)
    pinger_thread.start()
    
    try:
        run_bot()
    except Exception as e:
        print(f"❌ Bot stopped: {e}")
