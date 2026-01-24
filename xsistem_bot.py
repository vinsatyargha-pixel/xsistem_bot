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
    time.sleep(30)  # Tunggu Flask start dulu
    
    while True:
        try:
            url = "https://cek-rekening-fi8f.onrender.com"  # Ganti dengan URL Render Anda
            response = requests.get(url + "/ping", timeout=10)
            
            now = time.strftime("%H:%M:%S")
            if response.status_code == 200:
                logger.info(f"✅ [{now}] Ping successful - Bot alive")
            else:
                logger.warning(f"⚠️ [{now}] Ping failed: {response.status_code}")
        except Exception as e:
            now = time.strftime("%H:%M:%S")
            logger.error(f"❌ [{now}] Ping error: {e}")
        
        # Tunggu 8 menit
        time.sleep(480)

# ========== GOOGLE SHEETS UNTUK SHEET "X" ==========
def get_sheet():
    """Get the specific sheet named 'X'"""
    try:
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
        
        logger.info(f"🔧 Connecting to Google Sheets...")
        logger.info(f"   Spreadsheet ID: {SPREADSHEET_ID}")
        logger.info(f"   Target sheet: '{TARGET_SHEET_NAME}'")
        
        # Load credentials
        if os.getenv("GOOGLE_CREDENTIALS_JSON"):
            logger.info("✅ Using credentials from env var")
            import json
            creds_dict = json.loads(os.getenv("GOOGLE_CREDENTIALS_JSON"))
            creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        else:
            logger.info("✅ Using credentials from file")
            creds = Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
        
        # Authorize
        client = gspread.authorize(creds)
        logger.info("✅ Google Sheets authorized")
        
        # Buka spreadsheet
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        logger.info(f"✅ Spreadsheet opened: {spreadsheet.title}")
        
        # LIST SEMUA SHEET YANG ADA (untuk debug)
        all_sheets = spreadsheet.worksheets()
        logger.info(f"📋 Available sheets in spreadsheet:")
        for s in all_sheets:
            logger.info(f"   - '{s.title}' (id: {s.id})")
        
        # CARI SHEET DENGAN NAMA "X" (case insensitive)
        target_sheet = None
        for sheet in all_sheets:
            if sheet.title.strip().upper() == TARGET_SHEET_NAME.upper():
                target_sheet = sheet
                logger.info(f"✅ Found target sheet: '{sheet.title}'")
                break
        
        if not target_sheet:
            logger.error(f"❌ Sheet '{TARGET_SHEET_NAME}' not found!")
            logger.info("⚠️ Using first sheet as fallback")
            target_sheet = spreadsheet.sheet1
        
        # Test connection
        test_cell = target_sheet.acell('A1').value
        logger.info(f"📊 Test read A1: '{test_cell}'")
        
        return target_sheet
        
    except Exception as e:
        logger.error(f"❌ Google Sheets error: {e}", exc_info=True)
        return None

# ========== FUNGSI SUNIK BANK ==========
def parse_injection_text(text):
    patterns = {
        'no_rek': r"No Rek Bank\s*:\s*(.+)",
        'jenis_bank': r"Jenis Bank\s*:\s*(.+)",
        'nominal': r"Nominal Suntik\s*:\s*(.+)",
        'saldo_akhir': r"Saldo Akhir Bank\s*:\s*(.+)",
        'asset': r"Asset\s*:\s*(.+)"
    }
    
    extracted = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        extracted[key] = match.group(1).strip() if match else "N/A"
    
    return extracted

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
            
            # UPDATE SPREADSHEET SHEET "X"
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            approver_name = "Alvin" if call.from_user.username == "Vingeance" else "Joshua"
            
            logger.info(f"📊 Updating sheet '{TARGET_SHEET_NAME}'...")
            logger.info(f"   B3 → {current_time}")
            logger.info(f"   K3 → {approver_name}")
            
            sheet = get_sheet()
            if sheet:
                try:
                    # Update B3 di sheet "X"
                    sheet.update(range_name='B3', values=[[current_time]])
                    logger.info("✅ B3 updated in sheet 'X'")
                    
                    # Update K3 di sheet "X"
                    sheet.update(range_name='K3', values=[[approver_name]])
                    logger.info("✅ K3 updated in sheet 'X'")
                    
                    # Verifikasi
                    b3_value = sheet.acell('B3').value
                    k3_value = sheet.acell('K3').value
                    logger.info(f"✅ Verification - B3: '{b3_value}', K3: '{k3_value}'")
                    
                except Exception as e:
                    logger.error(f"❌ Failed to update sheet 'X': {e}", exc_info=True)
            else:
                logger.error("❌ Failed to connect to sheet 'X'")
            
            # Edit pesan di group
            new_text = (
                f"✅ **DISETUJUI** oleh @{call.from_user.username or 'admin'}\n"
                f"✍️ Approver: {approver_name}\n\n"
                f"Bank: {data['jenis_bank']}\n"
                f"Nominal: {data['nominal']}\n"
                f"Asset: {data['asset']}"
            )
            
            bot.edit_message_text(
                chat_id=GROUP_ID,
                message_id=call.message.message_id,
                text=new_text,
                parse_mode='Markdown'
            )
            
            bot.answer_callback_query(call.id, "✅ Disetujui & tercatat di spreadsheet (sheet X)")
            
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
    print("🤖 X-SISTEM BOT - COMPLETE VERSION")
    print(f"📊 Spreadsheet ID: {SPREADSHEET_ID}")
    print(f"📄 Target sheet: {TARGET_SHEET_NAME}")
    print("👑 Admin: @Vingeance @bangjoshh")
    print("🌐 Flask server: http://0.0.0.0:$PORT")
    print("⏰ Auto-pinger: Every 8 minutes")
    print("=" * 60)
    
    # Jalankan Flask di thread terpisah
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Jalankan pinger di thread terpisah
    pinger_thread = threading.Thread(target=ping_self, daemon=True)
    pinger_thread.start()
    
    # Jalankan bot (main thread)
    run_bot()
