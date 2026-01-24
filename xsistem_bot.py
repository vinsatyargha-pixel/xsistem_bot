import telebot
import random
import string
from telebot import types
import time
import requests
import os
import threading
import tempfile
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
SPREADSHEET_ID = "1_ix7oF2_KPXVnkQP9ScFa98zSBBf6-eLPC9Xzprm7bE"
TARGET_SHEET_NAME = "X"

pending_injections = {}

# ========== FLASK SERVER UNTUK RENDER ==========
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
    """Jalankan Flask server di port Render"""
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"🌐 Starting Flask server on port {port}")
    logger.info(f"🌐 Web server URL: http://0.0.0.0:{port}")
    web_app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# ========== AUTO PINGER UNTUK RENDER ==========
def ping_self():
    """Ping sendiri agar tidak sleep di Render"""
    logger.info("⏰ Starting auto-pinger...")
    time.sleep(30)
    
    while True:
        try:
            url = "https://cek-rekening-fi8f.onrender.com"
            response = requests.get(url + "/ping", timeout=10)
            
            now = time.strftime("%H:%M:%S")
            if response.status_code == 200:
                logger.info(f"✅ [{now}] Ping successful - Bot alive")
            else:
                logger.warning(f"⚠️ [{now}] Ping failed: {response.status_code}")
        except Exception as e:
            now = time.strftime("%H:%M:%S")
            logger.error(f"❌ [{now}] Ping error: {e}")
        
        time.sleep(480)

# ========== GOOGLE SHEETS UNTUK SHEET "X" ==========
def get_sheet():
    """Get the specific sheet named 'X'"""
    try:
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
        
        # Load credentials
        if os.getenv("GOOGLE_CREDENTIALS_JSON"):
            import json
            creds_dict = json.loads(os.getenv("GOOGLE_CREDENTIALS_JSON"))
            creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        else:
            creds = Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
        
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        
        # TAMPILKAN SEMUA SHEET YANG ADA
        logger.info("📋 Sheets available in spreadsheet:")
        all_sheets = spreadsheet.worksheets()
        for sheet in all_sheets:
            logger.info(f"   - '{sheet.title}' (id: {sheet.id})")
        
        # CARI SHEET DENGAN NAMA "X" (case insensitive)
        target_sheet = None
        for sheet in all_sheets:
            # Cek berbagai kemungkinan penamaan
            sheet_name = sheet.title.strip()
            if sheet_name.upper() == TARGET_SHEET_NAME.upper():
                target_sheet = sheet
                logger.info(f"✅ Found target sheet: '{sheet_name}'")
                break
        
        if not target_sheet:
            logger.error(f"❌ Sheet '{TARGET_SHEET_NAME}' not found!")
            logger.error("Available sheets:")
            for sheet in all_sheets:
                logger.error(f"   - '{sheet.title}'")
            return None
        
        # TEST: Baca beberapa data untuk memastikan sheet benar
        try:
            sample_data = sheet.get_all_values()
            logger.info(f"📊 Sheet has {len(sample_data)} rows of data")
            if len(sample_data) > 0:
                logger.info(f"📋 Header row: {sample_data[0]}")
        except Exception as e:
            logger.warning(f"⚠️ Could not read sample data: {e}")
        
        return target_sheet
        
    except gspread.exceptions.SpreadsheetNotFound:
        logger.error(f"❌ Spreadsheet with ID '{SPREADSHEET_ID}' not found!")
        return None
    except Exception as e:
        logger.error(f"❌ Google Sheets error: {e}")
        return None

def find_empty_row(sheet):
    """Mencari baris kosong pertama di kolom D (No Rek Bank)"""
    try:
        # Ambil semua data di kolom D
        column_d = sheet.col_values(4)  # Kolom D adalah kolom ke-4 (index 4)
        
        logger.info(f"🔍 Checking column D: found {len(column_d)} values")
        
        # Cari baris pertama yang kosong (setelah header)
        # Header biasanya di row 1-3, kita mulai dari row 4
        for i in range(3, len(column_d) + 2):  # +2 karena indexing dimulai dari 1
            if i >= len(column_d) or column_d[i] == "":
                logger.info(f"📌 Empty row found at index {i}, row {i+1}")
                return i + 1  # +1 karena row indexing dimulai dari 1
        
        # Jika semua terisi, kembalikan row berikutnya
        next_row = len(column_d) + 1
        logger.info(f"📌 All rows filled, next available row: {next_row}")
        return next_row
    except Exception as e:
        logger.error(f"❌ Error finding empty row: {e}")
        return 4  # Default ke row 4 jika error

# ========== FUNGSI SUNIK BANK ==========
def parse_injection_text(text):
    """Parsing SEMUA data dari format suntik bank"""
    patterns = {
        'no_rek': r"No Rek Bank\s*:\s*(.+)",           # → D (kolom D)
        'jenis_bank': r"Jenis Bank\s*:\s*(.+)",       # → E (kolom E) - TIDAK DIPAKAI
        'nama_bank': r"Nama Bank\s*:\s*(.+)",         # → F (kolom F) - TIDAK DIPAKAI
        'nominal': r"Nominal Suntik\s*:\s*(.+)",      # → G (kolom G)
        'saldo_akhir': r"Saldo Akhir Bank\s*:\s*(.+)", # → H (kolom H)
        'asset': r"Asset\s*:\s*(.+)",                 # → C (kolom C) - TIDAK DIPAKAI
        'wallet': r"Wallet Addres\s*:\s*(.+)",        # → (info saja)
        'officer': r"OFFICER\s*:\s*(.+)"              # → Officer yang request
    }
    
    extracted = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        extracted[key] = match.group(1).strip() if match else "N/A"
    
    logger.info(f"📝 Parsed data: {extracted}")
    return extracted

def update_spreadsheet_all_data(data, approver_name):
    """Update data ke baris kosong berikutnya di sheet X"""
    try:
        logger.info("🔄 Starting spreadsheet update...")
        sheet = get_sheet()
        if not sheet:
            logger.error("❌ Sheet not found")
            return False
        
        # Cari baris kosong berikutnya
        target_row = find_empty_row(sheet)
        logger.info(f"📊 Found empty row: {target_row}")
        
        # MAPPING DATA KE KOLOM:
        # D: NO REK BANK (No Rek Bank)
        # G: NOMINAL SUNTIK (Nominal Suntik)
        # H: SALDO AKHIR BANK (Saldo Akhir Bank)
        # K: APPROVER (Admin)
        # NOTE: Kolom B (DATE), C (ASSET), E (JENIS BANK), dan F (NAMA REK BANK) TIDAK DIISI
        
        updates = [
            ('D', [[data['no_rek']]]),               # No Rek Bank
            ('G', [[data['nominal']]]),              # Nominal Suntik
            ('H', [[data['saldo_akhir']]]),          # Saldo Akhir Bank
            ('K', [[approver_name]])                 # Approver
        ]
        
        logger.info("📊 Updating data to spreadsheet:")
        for col, value in updates:
            cell = f"{col}{target_row}"
            logger.info(f"   {cell} → {value[0][0]}")
            
            try:
                sheet.update(range_name=cell, values=value)
                logger.info(f"   ✅ Updated {cell}")
            except Exception as e:
                logger.error(f"   ❌ Failed to update {cell}: {e}")
                return False
        
        logger.info(f"✅ ALL data recorded to spreadsheet at row {target_row}")
        
        # Verifikasi: baca data yang baru ditulis
        try:
            verify_range = f"D{target_row}:K{target_row}"
            verify_data = sheet.get(verify_range)
            logger.info(f"✅ Verification - Row {target_row} data: {verify_data}")
        except:
            logger.warning("⚠️ Could not verify written data")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to update spreadsheet: {e}", exc_info=True)
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
        "Konfirmasi Admin:\n\n"
        "APPROVED atau DECLINE"
    )
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ APPROVED", callback_data=f"inj_approve_{data['message_id']}"),
        types.InlineKeyboardButton("❌ DECLINE", callback_data=f"inj_decline_{data['message_id']}")
    )
    
    sent_msg = bot.send_message(
        GROUP_ID,
        approval_msg + f"\n\n👑 Admin: @Vingeance @bangjoshh",
        reply_markup=markup,
        parse_mode='Markdown'
    )
    
    if data['is_photo'] and data['photo_id']:
        try:
            bot.send_photo(GROUP_ID, data['photo_id'], caption=f"📸 Screenshot dari {data['officer']}")
        except:
            pass
    
    pending_injections[data['message_id']] = {
        **text_data,
        'officer': data['officer'],
        'user_id': data['user_id'],
        'is_photo': data['is_photo'],
        'admin_message_id': sent_msg.message_id
    }
    
    logger.info(f"✅ Confirmation sent to group. Pending injections: {len(pending_injections)}")

# ========== HANDLER SUNIK BANK ==========
@bot.message_handler(content_types=['photo'])
def handle_photo_with_caption(message):
    if message.caption and "Tolong suntik dari rek Tampungan KPS" in message.caption:
        logger.info(f"📸 Photo with injection request from {message.from_user.username}")
        msg_text = message.caption
        parsed_data = parse_injection_text(msg_text)
        
        # Tambah officer dari pengirim
        if parsed_data['officer'] == "N/A":
            parsed_data['officer'] = message.from_user.username or message.from_user.first_name
        
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

@bot.message_handler(func=lambda m: "Tolong suntik dari rek Tampungan KPS" in m.text)
def handle_injection_request(message):
    if any(cmd in message.text.lower() for cmd in ['/reset', '/repass', '/repas', 'report']):
        return
    
    logger.info(f"📝 Text injection request from {message.from_user.username}")
    msg_text = message.text
    parsed_data = parse_injection_text(msg_text)
    
    # Tambah officer dari pengirim
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
    bot.reply_to(message, "✅ Permintaan suntik bank telah dikirim ke admin untuk konfirmasi.")

# ========== CALLBACK HANDLER ==========
@bot.callback_query_handler(func=lambda call: call.data.startswith('inj_'))
def handle_injection_callback(call):
    try:
        logger.info(f"🔄 CALLBACK RECEIVED: {call.data}")
        
        parts = call.data.split('_')
        if len(parts) != 3:
            bot.answer_callback_query(call.id, "❌ Format tidak valid")
            return
            
        action = parts[1]
        msg_id = int(parts[2])
        
        logger.info(f"   Action: {action}, Msg ID: {msg_id}")
        logger.info(f"   From: {call.from_user.username} (ID: {call.from_user.id})")
        
        data = pending_injections.get(msg_id)
        if not data:
            logger.error(f"❌ Data not found for msg_id: {msg_id}")
            bot.answer_callback_query(call.id, "❌ Data tidak ditemukan.")
            return
        
        logger.info(f"✅ Data found for injection")
        
        if action == "approve":
            logger.info("🔄 Processing APPROVE...")
            
            # Tentukan approver
            if call.from_user.username == "Vingeance":
                approver_name = "Alvin"
            elif call.from_user.username == "bangjoshh":
                approver_name = "Joshua"
            else:
                approver_name = call.from_user.username or "Admin"
            
            # UPDATE SEMUA DATA KE SPREADSHEET
            logger.info(f"📊 Updating ALL data to sheet '{TARGET_SHEET_NAME}'...")
            success = update_spreadsheet_all_data(data, approver_name)
            
            if success:
                logger.info("✅ ALL data recorded to spreadsheet")
            else:
                logger.error("❌ Failed to record data to spreadsheet")
            
            # Edit pesan di group
            new_text = (
                f"✅ **DISETUJUI** oleh @{call.from_user.username or 'admin'}\n"
                f"✍️ Approver: {approver_name}\n\n"
                f"Bank: {data['jenis_bank']} ({data['nama_bank']})\n"
                f"Rekening: {data['no_rek']}\n"
                f"Nominal: {data['nominal']}\n"
                f"Saldo: {data['saldo_akhir']}\n"
                f"Asset: {data['asset']}\n"
                f"Officer: {data['officer']}"
            )
            
            bot.edit_message_text(
                chat_id=GROUP_ID,
                message_id=call.message.message_id,
                text=new_text,
                parse_mode='Markdown'
            )
            
            bot.answer_callback_query(call.id, "✅ Disetujui & SEMUA data tercatat di sheet X")
            
        elif action == "decline":
            logger.info("🔄 Processing DECLINE...")
            
            bot.edit_message_text(
                chat_id=GROUP_ID,
                message_id=call.message.message_id,
                text=f"❌ **DITOLAK** oleh @{call.from_user.username or 'admin'}",
                parse_mode='Markdown'
            )
            bot.answer_callback_query(call.id, "❌ Ditolak")
        
        # Cleanup
        if msg_id in pending_injections:
            del pending_injections[msg_id]
            logger.info(f"🗑️ Cleared pending injection: {msg_id}")
            
    except Exception as e:
        logger.error(f"❌ CRITICAL ERROR in callback: {e}", exc_info=True)
        try:
            bot.answer_callback_query(call.id, "❌ Error processing")
        except:
            pass

# ========== BOT RUNNER ==========
def run_bot():
    logger.info("🤖 Starting Telegram Bot...")
    
    # Test Google Sheets connection saat startup
    logger.info("🔧 Testing Google Sheets connection on startup...")
    sheet = get_sheet()
    if sheet:
        logger.info(f"✅ Connected to sheet: '{sheet.title}'")
    else:
        logger.error("❌ Google Sheets connection FAILED")
    
    bot.polling(none_stop=True, timeout=30)

if __name__ == "__main__":
    print("=" * 60)
    print("🤖 X-SISTEM BOT - COMPLETE DATA RECORDING")
    print(f"📊 Spreadsheet ID: {SPREADSHEET_ID}")
    print(f"📄 Target sheet: {TARGET_SHEET_NAME}")
    print("📝 Recording data to columns (new row for each injection):")
    print("   D: NO REK BANK (No Rek Bank)")
    print("   G: NOMINAL SUNTIK (Nominal Suntik)")
    print("   H: SALDO AKHIR BANK (Saldo Akhir Bank)")
    print("   K: APPROVER (Admin)")
    print("🚫 B: DATE (NOT recorded - left empty)")
    print("🚫 C: ASSET (NOT recorded - left empty)")
    print("🚫 E: JENIS BANK (NOT recorded - left empty)")
    print("🚫 F: NAMA REK BANK (NOT recorded - left empty)")
    print("👑 Admin: @Vingeance @bangjoshh")
    print("=" * 60)
    
    # Jalankan Flask di thread terpisah
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Jalankan pinger di thread terpisah
    pinger_thread = threading.Thread(target=ping_self, daemon=True)
    pinger_thread.start()
    
    # Jalankan bot (main thread)
    run_bot()
