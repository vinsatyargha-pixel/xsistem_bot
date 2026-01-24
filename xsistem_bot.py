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

# ========== GOOGLE SHEETS DEBUG ==========
def get_sheet():
    """Debug Google Sheets connection"""
    try:
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
        
        logger.info("=" * 50)
        logger.info("🔧 GOOGLE SHEETS DEBUG START")
        
        # Cek file credentials
        if not os.path.exists('credentials.json'):
            logger.warning("⚠️ credentials.json file NOT FOUND locally")
            
            # Cek env var di Render
            if os.getenv("GOOGLE_CREDENTIALS_JSON"):
                logger.info("✅ GOOGLE_CREDENTIALS_JSON env var found")
                try:
                    import json
                    creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
                    creds_dict = json.loads(creds_json)
                    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
                    logger.info("✅ Credentials loaded from env var")
                except Exception as e:
                    logger.error(f"❌ Failed to parse env var credentials: {e}")
                    return None
            else:
                logger.error("❌ No credentials found anywhere")
                logger.info("Please add GOOGLE_CREDENTIALS_JSON to Render environment variables")
                return None
        else:
            logger.info("✅ credentials.json file found locally")
            creds = Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
        
        # Authorize
        client = gspread.authorize(creds)
        logger.info("✅ Google Sheets client authorized")
        
        # Buka spreadsheet
        try:
            spreadsheet = client.open_by_key(SPREADSHEET_ID)
            logger.info(f"✅ Spreadsheet opened: {spreadsheet.title}")
        except Exception as e:
            logger.error(f"❌ Failed to open spreadsheet: {e}")
            logger.info("Possible issues:")
            logger.info("1. Wrong SPREADSHEET_ID")
            logger.info("2. Service account doesn't have access")
            logger.info(f"3. Current SPREADSHEET_ID: {SPREADSHEET_ID}")
            return None
        
        # Ambil sheet pertama (atau sheet tertentu)
        try:
            sheet = spreadsheet.sheet1  # Sheet pertama (default)
            logger.info(f"✅ Sheet accessed: {sheet.title}")
            
            # Test read
            test_value = sheet.acell('A1').value
            logger.info(f"📊 Test read cell A1: '{test_value}'")
            
            # Cek apakah B3 dan K3 ada
            b3_before = sheet.acell('B3').value
            k3_before = sheet.acell('K3').value
            logger.info(f"📊 B3 before: '{b3_before}', K3 before: '{k3_before}'")
            
        except Exception as e:
            logger.error(f"❌ Failed to access sheet: {e}")
            return None
        
        logger.info("🔧 GOOGLE SHEETS DEBUG END")
        logger.info("=" * 50)
        
        return sheet
        
    except Exception as e:
        logger.error(f"❌ Google Sheets setup error: {e}", exc_info=True)
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

# ========== CALLBACK HANDLER DENGAN SPREADSHEET DEBUG ==========
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
            
            # UPDATE SPREADSHEET
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            approver_name = "Alvin" if call.from_user.username == "Vingeance" else "Joshua"
            
            logger.info(f"📊 Attempting to update spreadsheet...")
            logger.info(f"   Time: {current_time}")
            logger.info(f"   Approver: {approver_name}")
            
            sheet = get_sheet()
            if sheet:
                try:
                    # Update B3
                    logger.info(f"📝 Updating B3 to: {current_time}")
                    sheet.update(range_name='B3', values=[[current_time]])
                    logger.info("✅ B3 updated")
                    
                    # Update K3
                    logger.info(f"📝 Updating K3 to: {approver_name}")
                    sheet.update(range_name='K3', values=[[approver_name]])
                    logger.info("✅ K3 updated")
                    
                    # Verifikasi
                    b3_after = sheet.acell('B3').value
                    k3_after = sheet.acell('K3').value
                    logger.info(f"✅ Verification - B3: '{b3_after}', K3: '{k3_after}'")
                    
                except Exception as e:
                    logger.error(f"❌ Failed to update spreadsheet: {e}", exc_info=True)
            else:
                logger.error("❌ Failed to connect to Google Sheets")
            
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

# ========== BOT RUNNER ==========
def run_bot():
    logger.info("🤖 Starting Telegram Bot...")
    
    # Test Google Sheets connection saat startup
    logger.info("🔧 Testing Google Sheets connection on startup...")
    sheet = get_sheet()
    if sheet:
        logger.info("✅ Google Sheets connection OK")
    else:
        logger.error("❌ Google Sheets connection FAILED")
    
    bot.polling(none_stop=True, timeout=30)

if __name__ == "__main__":
    print("=" * 50)
    print("🤖 X-SISTEM BOT - SPREADSHEET DEBUG VERSION")
    print(f"📊 Spreadsheet ID: {SPREADSHEET_ID}")
    print("👑 Admin: @Vingeance @bangjoshh")
    print("=" * 50)
    
    run_bot()
