import telebot
import random
import string
from telebot import types
import time
import requests
import os
import threading
from flask import Flask
import re
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# ================= CONFIG =================
TOKEN = "8087735462:AAGII-XvO3hJy3YgDd3b0vjiIHjnQCn4Ej4"
bot = telebot.TeleBot(TOKEN)

# Config untuk suntik bank
ADMIN_USERNAMES = ["Vingeance", "bangjoshh"]  # Alvin & Joshua
GROUP_ID = -1003855148883  # ID grup X - INTERNAL WD
SPREADSHEET_ID = "1_ix7oF2_KPXVnkQP9ScFa98zSBBf6-eLPC9Xzprm7bE"

# ========== WEB SERVER FOR RENDER ==========
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "🤖 X-SISTEM BOT IS RUNNING", 200

@web_app.route('/health')
def health():
    return "✅ OK", 200

def run_flask():
    """Jalankan Flask di port yang ditentukan Render"""
    port = int(os.environ.get("PORT", 5000))
    print(f"🌐 Starting Flask server on port {port}")
    web_app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# ========== AUTO PINGER ==========
def ping_self():
    """Ping dari DALAM server ke URL PUBLIC"""
    print("⏰ Starting REAL pinger")
    time.sleep(30)  # Tunggu Flask start
    
    while True:
        try:
            # PING KE URL PUBLIC, bukan localhost!
            url = "https://cek-rekening-fi8f.onrender.com"  # Ganti dengan URL Render Anda
            response = requests.get(url, timeout=10)
            
            now = time.strftime("%H:%M:%S")
            if response.status_code == 200:
                print(f"✅ [{now}] Ping successful - Bot alive")
            else:
                print(f"⚠️ [{now}] Ping failed")
        except Exception as e:
            now = time.strftime("%H:%M:%S")
            print(f"❌ [{now}] Ping error")
        
        # Tunggu 8 menit
        time.sleep(480)

# ========== GOOGLE SHEETS UNTUK SUNIK BANK ==========
def get_sheet():
    """Setup connection ke Google Sheets"""
    try:
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
        
        # Untuk Render: gunakan env var
        if os.getenv("GOOGLE_CREDENTIALS_JSON"):
            import json
            creds_dict = json.loads(os.getenv("GOOGLE_CREDENTIALS_JSON"))
            creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        else:
            # Untuk local development
            creds = Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
        
        client = gspread.authorize(creds)
        return client.open_by_key(SPREADSHEET_ID).sheet1
    except Exception as e:
        print(f"❌ Google Sheets error: {e}")
        return None

# ========== BOT FUNCTIONS EXISTING ==========
def buat_password():
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(10))

def save_crossbank_report(data):
    try:
        web_app_url = "https://script.google.com/macros/s/AKfycbwGpv7pgFrMRccC0y3IkkQxcehSX3D0nLMZYWkFtjywVF2AIpj4R1MEj5mtaYd-U_TLVw/exec"
        payload = {'message': {'text': data['original_text']}}
        response = requests.post(web_app_url, json=payload, timeout=10)
        return (True, "Data tersimpan") if response.status_code == 200 else (False, f"Error: {response.status_code}")
    except Exception as e:
        return False, str(e)

def parse_report_text(text):
    data = {'original_text': text}
    lines = text.split('\n')
    for line in lines:
        if ':' in line:
            parts = line.split(':', 1)
            key = parts[0].strip().lower().replace(' ', '_')
            value = parts[1].strip()
            data[key] = value
    return data

# ========== FITUR BARU: SUNIK BANK ==========
pending_injections = {}  # Simpan data sementara

@bot.message_handler(func=lambda m: "Tolong suntik dari rek Tampungan KPS" in m.text)
def handle_injection_request(message):
    """Handle permintaan suntik bank"""
    officer = message.from_user.username or message.from_user.first_name
    msg_text = message.text
    
    # Parse wallet dan asset
    wallet_match = re.search(r"Wallet Addres :\s*(.+)", msg_text)
    asset_match = re.search(r"Asset :\s*(.+)", msg_text)
    
    if not wallet_match or not asset_match:
        bot.reply_to(message, "❌ Format salah! Pastikan ada Wallet Address dan Asset.")
        return
    
    wallet = wallet_match.group(1).strip()
    asset = asset_match.group(1).strip()
    
    # Ambil data dari spreadsheet
    sheet = get_sheet()
    if not sheet:
        bot.reply_to(message, "❌ Gagal konek ke spreadsheet.")
        return
    
    try:
        rek = sheet.acell('D3').value or "N/A"
        nama_bank = sheet.acell('E3').value or "N/A"
        jenis_bank = sheet.acell('F3').value or "N/A"
        nominal = sheet.acell('G3').value or "N/A"
        saldo_akhir = sheet.acell('H3').value or "N/A"
    except Exception as e:
        print(f"Spreadsheet error: {e}")
        bot.reply_to(message, "❌ Gagal baca data spreadsheet.")
        return
    
    # Simpan data sementara
    pending_injections[message.message_id] = {
        'wallet': wallet,
        'asset': asset,
        'officer': officer,
        'rek': rek,
        'nama_bank': nama_bank,
        'jenis_bank': jenis_bank,
        'nominal': nominal,
        'saldo_akhir': saldo_akhir,
        'original_msg_id': message.message_id
    }
    
    # Buat pesan approval
    approval_msg = (
        "💉 **PERMINTAAN SUNTIK BANK**\n"
        f"👤 Officer: {officer}\n"
        f"🏦 Bank: {nama_bank} ({jenis_bank})\n"
        f"🔢 Rekening: {rek}\n"
        f"💰 Nominal: {nominal}\n"
        f"📊 Saldo Akhir: {saldo_akhir}\n"
        f"👛 Wallet: {wallet}\n"
        f"📌 Asset: {asset}\n\n"
        "Konfirmasi Admin:"
    )
    
    # Tombol Approve/Decline
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ APPROVE", callback_data=f"inj_approve_{message.message_id}"),
        types.InlineKeyboardButton("❌ DECLINE", callback_data=f"inj_decline_{message.message_id}")
    )
    
    # Kirim ke grup
    bot.send_message(
        GROUP_ID,
        approval_msg,
        reply_markup=markup,
        parse_mode='Markdown'
    )
    
    bot.reply_to(message, "✅ Permintaan telah dikirim ke admin.")

@bot.callback_query_handler(func=lambda call: call.data.startswith('inj_'))
def handle_injection_callback(call):
    """Handle tombol approve/decline suntik bank"""
    try:
        action, msg_id = call.data.split('_')[1], int(call.data.split('_')[2])
        admin = call.from_user.username
        
        # Cek admin
        if admin not in ADMIN_USERNAMES:
            bot.answer_callback_query(call.id, "❌ Hanya admin yang bisa approve.")
            return
        
        data = pending_injections.get(msg_id)
        if not data:
            bot.answer_callback_query(call.id, "❌ Data tidak ditemukan.")
            return
        
        sheet = get_sheet()
        if not sheet:
            bot.answer_callback_query(call.id, "❌ Gagal konek spreadsheet.")
            return
        
        if action == "approve":
    # ========== UPDATE SPREADSHEET ==========
    try:
        sheet = get_sheet()
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        approver_name = "Alvin" if admin == "Vingeance" else "Joshua"
        
        # Update B3 dengan timestamp
        sheet.update('B3', [[current_time]])
        # Update K3 dengan nama approver
        sheet.update('K3', [[approver_name]])
        
        print(f"✅ Spreadsheet updated: B3={current_time}, K3={approver_name}")
    except Exception as e:
        print(f"❌ Spreadsheet error: {e}")
    # ========== END UPDATE ==========
            
            # Edit pesan di grup
            bot.edit_message_text(
                f"✅ **DISETUJUI** oleh @{admin}\n"
                f"⏰ Timestamp: {current_time}\n"
                f"✍️ Approver: {approver_name}\n\n"
                f"Bank: {data['nama_bank']}\n"
                f"Nominal: {data['nominal']}",
                GROUP_ID,
                call.message.message_id,
                parse_mode='Markdown'
            )
            
            bot.answer_callback_query(call.id, "✅ Disetujui & tercatat di spreadsheet")
            
        elif action == "decline":
            bot.edit_message_text(
                f"❌ **DITOLAK** oleh @{admin}",
                GROUP_ID,
                call.message.message_id,
                parse_mode='Markdown'
            )
            bot.answer_callback_query(call.id, "❌ Ditolak")
        
        # Hapus dari pending
        if msg_id in pending_injections:
            del pending_injections[msg_id]
            
    except Exception as e:
        print(f"Injection callback error: {e}")
        try:
            bot.answer_callback_query(call.id, "❌ Error processing")
        except:
            pass

# ========== COMMAND HANDLERS EXISTING (TETAP) ==========
@bot.message_handler(commands=['formatreset'])
def handle_format_reset(message):
    # ... (sama seperti sebelumnya)
    pass

@bot.message_handler(commands=['formatreport'])
def handle_format_report(message):
    # ... (sama seperti sebelumnya)
    pass

@bot.message_handler(commands=['report'])
def handle_report_command(message):
    # ... (sama seperti sebelumnya)
    pass

@bot.callback_query_handler(func=lambda call: call.data.startswith('report_'))
def handle_report_type(call):
    # ... (sama seperti sebelumnya)
    pass

def handle_report_generic(message, report_type):
    # ... (sama seperti sebelumnya)
    pass

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

@bot.message_handler(func=lambda m: m.text and not m.forward_from and any(
    cmd in m.text.lower() for cmd in ['/reset', '/repass', '/repas']
))
def handle_reset_only_text(message):
    # ... (sama seperti sebelumnya)
    pass

@bot.message_handler(content_types=['photo', 'document', 'video', 'audio', 'voice'])
def ignore_all_media(message):
    pass

@bot.callback_query_handler(func=lambda call: call.data.startswith('ok_') or call.data.startswith('no_'))
def handle_reset_callback(call):
    # ... (sama seperti sebelumnya)
    pass

# ========== BOT RUNNER ==========
def run_bot():
    """Jalankan Telegram bot"""
    print("🤖 Starting Telegram Bot...")
    bot.polling(
        none_stop=True,
        timeout=30,
        skip_pending=True
    )

if __name__ == "__main__":
    print("=" * 50)
    print("🤖 X-SISTEM BOT - MULTI FUNCTIONS")
    print("📱 /reset [ID] [ASSET] - Reset password")
    print("📊 /report - Pilih jenis report")
    print("💉 Suntik Bank - Kirim format suntik")
    print("🌐 Web server: http://0.0.0.0:${PORT}")
    print("⏰ Auto-pinger: Every 8 minutes")
    print("=" * 50)
    
    # Jalankan Flask di thread terpisah
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Jalankan pinger di thread terpisah
    pinger_thread = threading.Thread(target=ping_self, daemon=True)
    pinger_thread.start()
    
    # Jalankan bot (main thread)
    run_bot()


