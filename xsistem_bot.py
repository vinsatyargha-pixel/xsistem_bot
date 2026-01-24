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
        
        # CARI SHEET DENGAN NAMA "X"
        target_sheet = None
        for sheet in spreadsheet.worksheets():
            if sheet.title.strip().upper() == TARGET_SHEET_NAME.upper():
                target_sheet = sheet
                break
        
        if not target_sheet:
            target_sheet = spreadsheet.sheet1
        
        return target_sheet
        
    except Exception as e:
        logger.error(f"❌ Google Sheets error: {e}")
        return None

# ========== FUNGSI SUNIK BANK ==========
def parse_injection_text(text):
    """Parsing SEMUA data dari format suntik bank"""
    patterns = {
        'no_rek': r"No Rek Bank\s*:\s*(.+)",           # → D3
        'jenis_bank': r"Jenis Bank\s*:\s*(.+)",       # → E3
        'nama_bank': r"Nama Bank\s*:\s*(.+)",         # → F3
        'nominal': r"Nominal Suntik\s*:\s*(.+)",      # → G3
        'saldo_akhir': r"Saldo Akhir Bank\s*:\s*(.+)", # → H3
        'asset': r"Asset\s*:\s*(.+)",                 # → (info saja)
        'wallet': r"Wallet Addres\s*:\s*(.+)",        # → (info saja)
        'officer': r"OFFICER\s*:\s*(.+)"              # → Officer yang request
    }
    
    extracted = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        extracted[key] = match.group(1).strip() if match else "N/A"
    
    return extracted

def update_spreadsheet_all_data(data, approver_name):
    """Update SEMUA kolom di sheet X"""
    try:
        sheet = get_sheet()
        if not sheet:
            logger.error("❌ Sheet not found")
            return False
        
        
        # MAPPING DATA KE KOLOM:
        # D3: No Rek Bank
        # E3: Jenis Bank  
        # F3: Nama Bank
        # G3: Nominal Suntik
        # H3: Saldo Akhir Bank
        # K3: Approver (Admin)
        
        updates = [
            ('D3', [[data['no_rek']]]),        # No Rek Bank
            ('E3', [[data['jenis_bank']]]),    # Jenis Bank
            ('F3', [[data['nama_bank']]]),     # Nama Bank
            ('G3', [[data['nominal']]]),       # Nominal Suntik
            ('H3', [[data['saldo_akhir']]]),   # Saldo Akhir Bank
            ('K3', [[approver_name]])          # Approver
        ]
        
        logger.info("📊 Updating ALL columns in sheet X:")
        for cell, value in updates:
            logger.info(f"   {cell} → {value[0][0]}")
            sheet.update(range_name=cell, values=value)
        
        logger.info("✅ ALL data recorded to spreadsheet")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to update spreadsheet: {e}")
        return False

def send_admin_confirmation(data, original_message):
    text_data = data['text_data']
    
    approval_msg = (
        "💉 **PERMINTAAN SUNTIK BANK**\n\n"
        f"JENIS BANK : {text_data['jenis_bank']}\n"
        f"📊 Saldo Akhir: {text_data['saldo_akhir']}\n"
        f"No Rek Bank : {text_data['no_rek']}\n"
        f"📌 Asset: {text_data['asset']}\n\n"
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
    
    logger.info(f"✅ Confirmation sent. Pending injections: {len(pending_injections)}")

# ========== HANDLER SUNIK BANK ==========
@bot.message_handler(content_types=['photo'])
def handle_photo_with_caption(message):
    if message.caption and "Tolong suntik dari rek Tampungan KPS" in message.caption:
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
            approver_name = "Alvin" if call.from_user.username == "Vingeance" else "Joshua"
            
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
    print("📝 Recording ALL data to columns:")
    print("   B3: Timestamp")
    print("   D3: No Rek Bank")
    print("   E3: Jenis Bank")
    print("   F3: Nama Bank")
    print("   G3: Nominal Suntik")
    print("   H3: Saldo Akhir Bank")
    print("   K3: Approver (Admin)")
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

