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
SPREADSHEET_ID = "1RJabYiQePFtWV4Y8zrjchQmmx7CRPIwjvl-3mFvyWyc"
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
        'no_rek': r"No Rek Bank\s*:\s*(.+)",           # Kolom D
        'jenis_bank': r"Jenis Bank\s*:\s*(.+)",       # Kolom E - TIDAK DIPAKAI
        'nama_bank': r"Nama Bank\s*:\s*(.+)",         # Kolom F - TIDAK DIPAKAI
        'nominal': r"Nominal Suntik\s*:\s*(.+)",      # Kolom G
        'saldo_akhir': r"Saldo Akhir Bank\s*:\s*(.+)", # Kolom H
        'asset': r"Asset\s*:\s*(.+)",                 # Kolom C - TIDAK DIPAKAI
        'wallet': r"Wallet Addres\s*:\s*(.+)",        # Info saja
        'officer': r"OFFICER\s*:\s*(.+)"              # Officer yang request
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
            logger.info(f"   {cell} -> {value[0][0]}")
            
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

# ========== FUNGSI REPORT ==========
def parse_report_text(text):
    """Parsing data dari teks report (baik text message maupun caption)"""
    try:
        data = {'original_text': text}
        
        # Split menjadi baris-baris
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        # Cari jenis report di baris pertama
        first_line = lines[0].upper() if lines else ""
        report_types = [
            'REPORT CROSSBANK', 'REPORT PENDINGAN', 'REPORT PROCESS PENDINGAN',
            'REPORT MISTAKE', 'REPORT REFUND', 'REPORT FEE'
        ]
        
        for report_type in report_types:
            if report_type in first_line:
                data['report_type'] = report_type
                break
        
        # Parse data dari baris-baris berikutnya
        for line in lines[1:]:  # Skip baris pertama (jenis report)
            if ':' in line:
                parts = line.split(':', 1)
                if len(parts) == 2:
                    key = parts[0].strip().lower().replace(' ', '_')
                    value = parts[1].strip()
                    data[key] = value
        
        logger.info(f"📋 Parsed report data: {data}")
        return data
        
    except Exception as e:
        logger.error(f"❌ Error parsing report text: {e}")
        return {'original_text': text}

def save_crossbank_report(data):
    """Save report data to Google Apps Script"""
    try:
        web_app_url = "https://script.google.com/macros/s/AKfycbwGpv7pgFrMRccC0y3IkkQxcehSX3D0nLMZYWkFtjywVF2AIpj4R1MEj5mtaYd-U_TLVw/exec"
        payload = {'message': {'text': data['original_text']}}
        response = requests.post(web_app_url, json=payload, timeout=10)
        return (True, "Data tersimpan") if response.status_code == 200 else (False, f"Error: {response.status_code}")
    except Exception as e:
        return False, str(e)

def handle_report_from_caption(caption_text, message):
    """Handle report yang dikirim sebagai caption foto"""
    try:
        logger.info(f"📝 Processing report from photo caption")
        
        # Parsing data dari caption
        data = parse_report_text(caption_text)
        
        # Tambahkan officer jika tidak ada
        if 'officer' not in data or not data['officer']:
            data['officer'] = message.from_user.username or message.from_user.first_name
        
        # Tambahkan original text untuk Google Apps Script
        data['original_text'] = caption_text
        
        # Simpan ke Google Sheets
        success, result = save_crossbank_report(data)
        
        if success:
            reply_text = "✅ REPORT BERHASIL DISIMPAN!"
            logger.info(f"✅ Report saved successfully from photo caption")
        else:
            reply_text = f"❌ Gagal menyimpan report: {result}"
            logger.error(f"❌ Failed to save report: {result}")
        
        bot.reply_to(message, reply_text)
        
    except Exception as e:
        logger.error(f"❌ Error handling report from caption: {e}", exc_info=True)
        bot.reply_to(message, "❌ Terjadi error saat memproses report")

def handle_report_generic(message, report_type):
    """Handle semua jenis report"""
    try:
        text = message.text.strip() if message.text else ""
        
        if not text:
            return
            
        # Parsing data
        data = parse_report_text(text)
        
        # Tambahkan officer jika tidak ada
        if 'officer' not in data or not data['officer']:
            data['officer'] = message.from_user.username or message.from_user.first_name
        
        # Tambahkan original text
        data['original_text'] = text
        
        # Save to Google Sheets
        success, result = save_crossbank_report(data)
        
        if success:
            bot.reply_to(message, "✅ REPORT BERHASIL DISIMPAN!")
            logger.info(f"✅ {report_type} report saved successfully")
        else:
            bot.reply_to(message, f"❌ Gagal menyimpan report: {result}")
            logger.error(f"❌ Failed to save {report_type} report: {result}")
            
    except Exception as e:
        logger.error(f"❌ Error handling {report_type} report: {e}")
        bot.reply_to(message, "❌ Terjadi error saat memproses report")

# ========== HANDLER SUNIK BANK ==========
@bot.message_handler(content_types=['photo'])
def handle_photo_with_caption(message):
    """Handler untuk foto dengan caption (menangani BOTH suntik bank DAN report)"""
    caption = message.caption or ""
    logger.info(f"📸 Received photo with caption from {message.from_user.username}")
    
    # PRIORITY 1: Check for SUNIK BANK in caption
    if "Tolong suntik dari rek Tampungan KPS" in caption:
        logger.info(f"📸 Photo with injection request from {message.from_user.username}")
        msg_text = caption
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
    
    # PRIORITY 2: Check for REPORT in caption
    if caption:
        caption_upper = caption.upper()
        report_keywords = [
            'REPORT CROSSBANK', 'REPORT PENDINGAN', 'REPORT PROCESS PENDINGAN',
            'REPORT MISTAKE', 'REPORT REFUND', 'REPORT FEE'
        ]
        
        for keyword in report_keywords:
            if keyword in caption_upper:
                logger.info(f"📸 Photo with REPORT in caption from {message.from_user.username}")
                handle_report_from_caption(caption, message)
                return
    
    # Jika bukan suntik bank atau report, abaikan
    logger.info(f"📸 Photo ignored (not suntik bank or report)")

@bot.message_handler(func=lambda m: "Tolong suntik dari rek Tampungan KPS" in m.text)
def handle_injection_request(message):
    """Handler untuk suntik bank via text"""
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

# ========== CALLBACK HANDLER UNTUK SUNIK ==========
@bot.callback_query_handler(func=lambda call: call.data.startswith('inj_'))
def handle_injection_callback(call):
    try:
        logger.info(f"🔄 CALLBACK RECEIVED: {call.data}")
        logger.info(f"   From: @{call.from_user.username} (ID: {call.from_user.id})")
        
        # Parse callback data
        parts = call.data.split('_')
        if len(parts) < 3:
            bot.answer_callback_query(call.id, "❌ Format tidak valid")
            return
            
        action = parts[1]  # 'approve' atau 'decline'
        msg_id = int(parts[2])  # message_id
        
        logger.info(f"   Action: {action}, Msg ID: {msg_id}")
        
        # Cek apakah user adalah admin yang berwenang
        caller_username = call.from_user.username
        if caller_username not in ADMIN_USERNAMES:
            logger.warning(f"⛔ Unauthorized attempt by @{caller_username}")
            bot.answer_callback_query(call.id, "❌ Anda tidak memiliki akses untuk approve/reject!")
            return
        
        # Ambil data injection
        data = pending_injections.get(msg_id)
        if not data:
            logger.error(f"❌ Data not found for msg_id: {msg_id}")
            bot.answer_callback_query(call.id, "❌ Data tidak ditemukan atau sudah kadaluarsa.")
            
            # Update pesan di group
            try:
                bot.edit_message_text(
                    chat_id=GROUP_ID,
                    message_id=call.message.message_id,
                    text="⚠️ **DATA SUDAH KADALUARSA**\n\nPermintaan ini sudah tidak valid.",
                    parse_mode='Markdown'
                )
            except:
                pass
            return
        
        logger.info(f"✅ Data found for injection: {data}")
        
        if action == "approve":
            logger.info("🔄 Processing APPROVE...")
            
            # Tentukan approver name berdasarkan username
            if caller_username == "Vingeance":
                approver_name = "Alvin"
            elif caller_username == "bangjoshh":
                approver_name = "Joshua"
            else:
                approver_name = caller_username or "Admin"
            
            # UPDATE SEMUA DATA KE SPREADSHEET
            logger.info(f"📊 Updating ALL data to sheet '{TARGET_SHEET_NAME}'...")
            success = update_spreadsheet_all_data(data, approver_name)
            
            if success:
                logger.info("✅ ALL data recorded to spreadsheet")
                response_text = "✅ Disetujui & SEMUA data tercatat di sheet X"
            else:
                logger.error("❌ Failed to record data to spreadsheet")
                response_text = "⚠️ Disetujui TAPI GAGAL mencatat ke spreadsheet"
            
            # Edit pesan di group
            new_text = (
                f"✅ **DISETUJUI** oleh @{caller_username}\n"
                f"✍️ Approver: {approver_name}\n\n"
                f"🏦 Bank: {data.get('jenis_bank', 'N/A')} ({data.get('nama_bank', 'N/A')})\n"
                f"💳 Rekening: {data.get('no_rek', 'N/A')}\n"
                f"💰 Nominal: {data.get('nominal', 'N/A')}\n"
                f"📊 Saldo: {data.get('saldo_akhir', 'N/A')}\n"
                f"📌 Asset: {data.get('asset', 'N/A')}\n"
                f"👤 Officer: {data.get('officer', 'N/A')}"
            )
            
            try:
                bot.edit_message_text(
                    chat_id=GROUP_ID,
                    message_id=call.message.message_id,
                    text=new_text,
                    parse_mode='Markdown'
                )
                logger.info(f"✅ Group message updated for approval")
            except Exception as e:
                logger.error(f"❌ Failed to edit group message: {e}")
            
            bot.answer_callback_query(call.id, response_text)
            
        elif action == "decline":
            logger.info("🔄 Processing DECLINE...")
            
            try:
                bot.edit_message_text(
                    chat_id=GROUP_ID,
                    message_id=call.message.message_id,
                    text=f"❌ **DITOLAK** oleh @{caller_username}",
                    parse_mode='Markdown'
                )
                logger.info(f"✅ Group message updated for decline")
            except Exception as e:
                logger.error(f"❌ Failed to edit group message: {e}")
            
            bot.answer_callback_query(call.id, "❌ Ditolak")
        
        # Cleanup - hapus dari pending setelah diproses
        if msg_id in pending_injections:
            del pending_injections[msg_id]
            logger.info(f"🗑️ Cleared pending injection: {msg_id}")
            
    except Exception as e:
        logger.error(f"❌ CRITICAL ERROR in callback: {e}", exc_info=True)
        try:
            bot.answer_callback_query(call.id, "❌ Error processing request")
        except:
            pass

# ========== FUNGSI RESET PASSWORD ==========
def buat_password():
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(10))

# ========== COMMAND HANDLERS UNTUK RESET & REPORT ==========
@bot.message_handler(commands=['formatreset'])
def handle_format_reset(message):
    try:
        format_text = """📋 CONTOH FORMAT YANG BENAR:

/repas ID ASSET
BANK MEMBER
BANK TUJUAN
WALLET :
OFFICER :

───────────────
Contoh lengkap:
/repas GGWP123 XLY
BRI TRALALA 123456789101112
BCA BLABLABLA 9876543210
WALLET : 
OFFICER : kamu

───────────────
Trigger alternatif juga bisa:
/reset GGWP123 XLY
/repass GGWP123-XLY
/reset GGWP123 XLY DANA BCA

Note: Bot akan ambil 2 kata pertama setelah command."""
        bot.reply_to(message, format_text, parse_mode=None)
    except:
        pass

@bot.message_handler(commands=['formatreport'])
def handle_format_report(message):
    try:
        format_text = """📋 (PILIH SALAH SATU KATEGORI - JANGAN TYPO)

REPORT CROSSBANK
REPORT MISTAKE
REPORT FEE
REPORT PENDINGAN
REPORT PROCESS PENDINGAN
REPORT REFUND

FORMAT:
ASET: BTC (sesuaikan)
USER ID: LAPARBANG123 (sesuaikan)
BANK MEMBER: BCA DONALD BEBEK 123456789 (sesuaikan)
BANK ASSET: BCA MICKEY MOUSE 987654321 (sesuaikan)
NO TICKET: D123456/W123456 (sesuaikan)
AMOUNT: 50.000 (sesuaikan)
CASE: Keterangan (sesuaikan)
OFFICER: USER ID (punya kamu)

Contoh:
REPORT CROSSBANK
ASET: BTC (sesuaikan)
USER ID: LAPARBANG123 (sesuaikan)
BANK MEMBER: BCA DONALD BEBEK 123456789 (sesuaikan)
BANK ASSET: BCA MICKEY MOUSE 987654321 (sesuaikan)
NO TICKET: D123456/W123456 (sesuaikan)
AMOUNT: 50.000 (sesuaikan)
CASE: KHILAF
OFFICER: USER ID (punya kamu)"""
        bot.reply_to(message, format_text, parse_mode=None)
    except:
        pass

@bot.message_handler(commands=['report'])
def handle_report_command(message):
    try:
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("📋 CROSSBANK", callback_data="report_crossbank"),
            types.InlineKeyboardButton("⏳ PENDINGAN", callback_data="report_pendingan"),
            types.InlineKeyboardButton("🔄 PROCESS PENDINGAN", callback_data="report_process_pendingan"),
            types.InlineKeyboardButton("❌ MISTAKE", callback_data="report_mistake"),
            types.InlineKeyboardButton("↩️ REFUND", callback_data="report_refund"),
            types.InlineKeyboardButton("💰 FEE", callback_data="report_fee")
        )
        bot.reply_to(
            message,
            "📊 *PILIH JENIS REPORT:*\n\nAtau ketik langsung:\n• REPORT CROSSBANK\n• REPORT PENDINGAN\n• REPORT MISTAKE\n• dll...\n\nUntuk format lengkap: /formatreport",
            reply_markup=markup,
            parse_mode='Markdown'
        )
    except:
        pass

@bot.callback_query_handler(func=lambda call: call.data.startswith('report_'))
def handle_report_type(call):
    try:
        report_type = call.data.replace('report_', '')
        formats = {
            'crossbank': "\n📋 *FORMAT REPORT CROSSBANK*\n\nREPORT CROSSBANK\nASET: BTC\nUSER ID: 123456\nBANK MEMBER: BCA\nBANK ASSET: Binance\nNO TICKET: TKT789\nAMOUNT: 5000000\nCASE: Fraud\nOFFICER: John Doe",
            'pendingan': "\n⏳ *FORMAT REPORT PENDINGAN*\n\nREPORT PENDINGAN\nASET: BTC\nUSER ID: 123456\nBANK MEMBER: BCA\nBANK ASSET: Binance\nNO TICKET: TKT789\nAMOUNT: 5000000\nCASE: Input Pendingan Deposit\nOFFICER: John Doe",
            'process_pendingan': "\n🔄 *FORMAT REPORT PROCESS PENDINGAN*\n\nREPORT PROCESS PENDINGAN\nASET: BTC\nUSER ID: 123456\nBANK MEMBER: BCA\nBANK ASSET: Binance\nNO TICKET: TKT789\nAMOUNT: 5000000\nCASE: Proses Pendingan Deposit\nOFFICER: John Doe",
            'mistake': "\n❌ *FORMAT REPORT MISTAKE*\n\nREPORT MISTAKE\nASET: BTC\nUSER ID: 123456\nBANK MEMBER: BCA\nBANK ASSET: Binance\nNO TICKET: TKT789\nAMOUNT: 5000000\nCASE: Kesalahan Input Data\nOFFICER: John Doe",
            'refund': "\n↩️ *FORMAT REPORT REFUND*\n\nREPORT REFUND\nASET: BTC\nUSER ID: 123456\nBANK MEMBER: BCA\nBANK ASSET: Binance\nNO TICKET: TKT789\nAMOUNT: 5000000\nCASE: Pengembalian Dana\nOFFICER: John Doe",
            'fee': "\n💰 *FORMAT REPORT FEE*\n\nREPORT FEE\nASET: BTC\nUSER ID: 123456\nBANK MEMBER: BCA\nBANK ASSET: Binance\nNO TICKET: TKT789\nAMOUNT: 5000000\nCASE: Biaya Admin/Operasional\nOFFICER: John Doe"
        }
        bot.edit_message_text(
            formats[report_type] + "\n\n*Kirim pesan dengan format di atas*",
            call.message.chat.id,
            call.message.message_id,
            parse_mode='Markdown'
        )
        bot.answer_callback_query(call.id, f"Format {report_type.upper()}")
    except:
        try:
            bot.answer_callback_query(call.id, "⚠️ Message sudah dihapus")
        except:
            pass

# ========== HANDLER REPORT BERBAGAI JENIS ==========
@bot.message_handler(func=lambda m: m.text and m.text.strip().startswith('REPORT CROSSBANK'))
def handle_crossbank_message(message):
    handle_report_generic(message, 'CROSSBANK')

@bot.message_handler(func=lambda m: m.text and m.text.strip().startswith('REPORT PENDINGAN'))
def handle_pendingan_message(message):
    handle_report_generic(message, 'PENDINGAN')

@bot.message_handler(func=lambda m: m.text and m.text.strip().startswith('REPORT PROCESS PENDINGAN'))
def handle_process_pendingan_message(message):
    handle_report_generic(message, 'PROCESS PENDINGAN')

@bot.message_handler(func=lambda m: m.text and m.text.strip().startswith('REPORT MISTAKE'))
def handle_mistake_message(message):
    handle_report_generic(message, 'MISTAKE')

@bot.message_handler(func=lambda m: m.text and m.text.strip().startswith('REPORT REFUND'))
def handle_refund_message(message):
    handle_report_generic(message, 'REFUND')

@bot.message_handler(func=lambda m: m.text and m.text.strip().startswith('REPORT FEE'))
def handle_fee_message(message):
    handle_report_generic(message, 'FEE')

# ========== HANDLER RESET PASSWORD ==========
@bot.message_handler(func=lambda m: m.text and not m.forward_from and any(
    cmd in m.text.lower() for cmd in ['/reset', '/repass', '/repas']
))
def handle_reset_only_text(message):
    try:
        text = message.text.strip()
        first_line = text.split('\n')[0]
        parts = first_line.split()
        if len(parts) < 3:
            return
        user_id = parts[1]
        asset = parts[2]
        logger.info(f"📩 Reset request: {user_id} {asset}")
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("✅ Reset", callback_data=f"ok_{message.from_user.id}_{user_id}_{asset}"),
            types.InlineKeyboardButton("❌ Tolak", callback_data=f"no_{message.from_user.id}")
        )
        bot.reply_to(
            message,
            f"🔔 *RESET REQUEST*\n\n👤 CS: {message.from_user.first_name}\n🆔 User: `{user_id}`\n🎮 Asset: `{asset}`\n\n**PILIH:**",
            reply_markup=markup,
            parse_mode='Markdown'
        )
    except:
        pass

# ========== CALLBACK HANDLER UNTUK RESET ==========
@bot.callback_query_handler(func=lambda call: call.data.startswith('ok_') or call.data.startswith('no_'))
def handle_reset_callback(call):
    try:
        if call.data.startswith('ok_'):
            _, cs_id, user_id, asset = call.data.split('_')
            password = buat_password()
            bot.send_message(call.message.chat.id, f"{user_id} - {asset}\nPassword baru : {password}")
            bot.edit_message_text(
                f"✅ *RESET DISETUJUI*\n\nUser: `{user_id}`\nAsset: `{asset}`\nPassword: `{password}`",
                call.message.chat.id,
                call.message.message_id,
                parse_mode='Markdown'
            )
            bot.answer_callback_query(call.id, "✅ Password dikirim")
        elif call.data.startswith('no_'):
            bot.send_message(call.message.chat.id, "❌ Permintaan ditolak Captain !!")
            bot.edit_message_text("❌ *REQUEST DITOLAK*", call.message.chat.id, call.message.message_id, parse_mode='Markdown')
            bot.answer_callback_query(call.id, "❌ Ditolak")
    except:
        try:
            bot.answer_callback_query(call.id, "⚠️ Action gagal")
        except:
            pass

# ========== HANDLER MEDIA LAINNYA (untuk diabaikan) ==========
@bot.message_handler(content_types=['document', 'video', 'audio', 'voice', 'sticker', 'location', 'contact', 'poll'])
def ignore_all_media(message):
    """Ignore semua media yang tidak relevan"""
    pass

# ========== BOT RUNNER ==========
def run_bot():
    logger.info("Starting Telegram Bot...")
    
    # Test Google Sheets connection saat startup
    logger.info("Testing Google Sheets connection on startup...")
    sheet = get_sheet()
    if sheet:
        logger.info(f"✅ Connected to sheet: '{sheet.title}'")
        
        # Test membaca data
        try:
            data = sheet.get_all_values()
            logger.info(f"📊 Sheet contains {len(data)} rows")
            if len(data) > 0:
                logger.info(f"📋 First row (header): {data[0]}")
        except Exception as e:
            logger.warning(f"⚠️ Could not read sheet data: {e}")
    else:
        logger.error("❌ Google Sheets connection FAILED")
    
    logger.info("🤖 Bot is now running...")
    bot.polling(none_stop=True, timeout=30)

if __name__ == "__main__":
    print("=" * 60)
    print("🤖 X-SISTEM BOT - COMPLETE FEATURES")
    print("=" * 60)
    print(f"📊 Spreadsheet ID: {SPREADSHEET_ID}")
    print(f"📋 Target sheet: {TARGET_SHEET_NAME}")
    print("=" * 60)
    print("💉 Suntik Bank Features:")
    print("   ✅ D: NO REK BANK (No Rek Bank)")
    print("   ✅ G: NOMINAL SUNTIK (Nominal Suntik)")
    print("   ✅ H: SALDO AKHIR BANK (Saldo Akhir Bank)")
    print("   ✅ K: APPROVER (Admin)")
    print("=" * 60)
    print("🔄 Reset Password Features:")
    print("   ✅ /reset [ID] [ASSET] - Reset password")
    print("=" * 60)
    print("📊 Report Features:")
    print("   ✅ /report - Pilih jenis report")
    print("   ✅ Report via TEXT message")
    print("   ✅ Report via PHOTO caption")
    print("   ✅ Support: CROSSBANK, PENDINGAN, MISTAKE, REFUND, FEE")
    print("=" * 60)
    print("👑 Admin: @Vingeance @bangjoshh")
    print("🌐 Render URL: https://cek-rekening-fi8f.onrender.com")
    print("=" * 60)
    
    # Jalankan Flask di thread terpisah
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Jalankan pinger di thread terpisah
    pinger_thread = threading.Thread(target=ping_self, daemon=True)
    pinger_thread.start()
    
    # Jalankan bot (main thread)
    try:
        run_bot()
    except Exception as e:
        logger.error(f"❌ Bot crashed: {e}", exc_info=True)
        print(f"❌ Bot stopped: {e}")


