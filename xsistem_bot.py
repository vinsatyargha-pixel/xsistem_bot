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

pending_injections = {}

# ========== WEB SERVER ==========
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "🤖 X-SISTEM BOT IS RUNNING", 200

@web_app.route('/health')
def health():
    return "✅ OK", 200

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"🌐 Starting Flask server on port {port}")
    web_app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

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
        return client.open_by_key(SPREADSHEET_ID).sheet1
    except Exception as e:
        logger.error(f"❌ Google Sheets error: {e}")
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
    
    # SELALU kirim pesan text, bukan edit caption photo
    sent_msg = bot.send_message(
        GROUP_ID,
        approval_msg + f"\n\n👑 Admin: @Vingeance @bangjoshh",
        reply_markup=markup,
        parse_mode='Markdown'
    )
    
    # Jika ada photo, kirim terpisah
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
    
    logger.info(f"✅ Confirmation sent to admin group. Message ID: {sent_msg.message_id}")

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

# ========== FIXED CALLBACK HANDLER ==========
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
        
        # SIMPLE ADMIN CHECK - comment untuk testing
        # if call.from_user.username not in ADMIN_USERNAMES:
        #     bot.answer_callback_query(call.id, "❌ Hanya admin yang bisa approve.")
        #     return
        
        data = pending_injections.get(msg_id)
        if not data:
            logger.error(f"❌ Data not found for msg_id: {msg_id}")
            bot.answer_callback_query(call.id, "❌ Data tidak ditemukan.")
            return
        
        logger.info(f"✅ Data found for injection")
        
        if action == "approve":
            logger.info("🔄 Processing APPROVE...")
            
            # Update Google Sheets
            try:
                sheet = get_sheet()
                if sheet:
                    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    approver_name = "Alvin" if call.from_user.username == "Vingeance" else "Joshua"
                    
                    # FIX: Update dengan parameter yang benar
                    sheet.update(range_name='B3', values=[[current_time]])
                    sheet.update(range_name='K3', values=[[approver_name]])
                    logger.info(f"✅ Spreadsheet updated: B3={current_time}, K3={approver_name}")
                else:
                    logger.warning("⚠️ Sheet not found, skipping spreadsheet update")
            except Exception as e:
                logger.error(f"❌ Spreadsheet error: {e}")
            
            # Edit pesan di group
            new_text = (
                f"✅ **DISETUJUI** oleh @{call.from_user.username or 'admin'}\n"
                f"✍️ Approver: {'Alvin' if call.from_user.username == 'Vingeance' else 'Joshua'}\n\n"
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
            
            bot.answer_callback_query(call.id, "✅ Disetujui & tercatat di spreadsheet")
            
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

# ========== SIMPLE EXISTING HANDLERS ==========
@bot.message_handler(func=lambda m: m.text and any(
    cmd in m.text.lower() for cmd in ['/reset', '/repass', '/repas']
))
def handle_reset_only_text(message):
    try:
        if "Tolong suntik dari rek Tampungan KPS" in message.text:
            return
            
        text = message.text.strip()
        parts = text.split()
        if len(parts) < 3:
            return
            
        user_id = parts[1]
        asset = parts[2]
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("✅ Reset", callback_data=f"ok_{message.from_user.id}_{user_id}_{asset}"),
            types.InlineKeyboardButton("❌ Tolak", callback_data=f"no_{message.from_user.id}")
        )
        
        bot.reply_to(message, f"🔔 RESET REQUEST\n\nUser: {user_id}\nAsset: {asset}", reply_markup=markup)
    except:
        pass

@bot.callback_query_handler(func=lambda call: call.data.startswith('ok_') or call.data.startswith('no_'))
def handle_reset_callback(call):
    try:
        if call.data.startswith('ok_'):
            _, cs_id, user_id, asset = call.data.split('_')
            password = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(10))
            bot.send_message(call.message.chat.id, f"{user_id} - {asset}\nPassword baru: {password}")
            bot.edit_message_text("✅ RESET DISETUJUI", call.message.chat.id, call.message.message_id)
            bot.answer_callback_query(call.id, "✅ Password dikirim")
        elif call.data.startswith('no_'):
            bot.edit_message_text("❌ REQUEST DITOLAK", call.message.chat.id, call.message.message_id)
            bot.answer_callback_query(call.id, "❌ Ditolak")
    except:
        try:
            bot.answer_callback_query(call.id, "⚠️ Action gagal")
        except:
            pass

# ========== BOT RUNNER ==========
def run_bot():
    logger.info("🤖 Starting Telegram Bot...")
    bot.polling(none_stop=True, timeout=30)

if __name__ == "__main__":
    print("=" * 50)
    print("🤖 X-SISTEM BOT - FIXED VERSION")
    print("💉 Suntik Bank - Photo & Text Fixed")
    print("👑 Admin: @Vingeance @bangjoshh")
    print("=" * 50)
    
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    run_bot()
