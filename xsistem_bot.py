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

# ================= CONFIG =================
TOKEN = "8087735462:AAGII-XvO3hJy3YgDd3b0vjiIHjnQCn4Ej4"
bot = telebot.TeleBot(TOKEN)

# Config untuk suntik bank
ADMIN_USERNAMES = ["Vingeance", "bangjoshh"]  # Alvin & Joshua - sesuaikan jika berbeda
GROUP_ID = -1003855148883  # ID grup X - INTERNAL WD
SPREADSHEET_ID = "1_ix7oF2_KPXVnkQP9ScFa98zSBBf6-eLPC9Xzprm7bE"

# Storage untuk screenshot
screenshot_storage = {}  # {message_id: {"file_path": "...", "user_id": "...", "timestamp": "..."}}
pending_injections = {}  # {message_id: injection_data}

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

# ========== HANDLER UNTUK SCREENSHOT SUNIK BANK ==========
@bot.message_handler(content_types=['photo'])
def handle_screenshot_photo(message):
    """Handle screenshot khusus untuk suntik bank"""
    user_id = message.from_user.id
    officer = message.from_user.username or message.from_user.first_name
    
    try:
        # Download photo
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        # Simpan sementara
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
        temp_file.write(downloaded_file)
        temp_file.close()
        
        # Simpan di storage
        screenshot_storage[message.message_id] = {
            'file_path': temp_file.name,
            'user_id': user_id,
            'timestamp': datetime.now(),
            'officer': officer
        }
        
        # Cleanup old screenshots (lebih dari 10 menit)
        current_time = datetime.now()
        for msg_id in list(screenshot_storage.keys()):
            storage_time = screenshot_storage[msg_id]['timestamp']
            if (current_time - storage_time).seconds > 600:  # 10 menit
                try:
                    os.remove(screenshot_storage[msg_id]['file_path'])
                    del screenshot_storage[msg_id]
                except:
                    pass
        
        print(f"📸 Screenshot saved for {officer} (user_id: {user_id})")
        
        # Reply instruksi
        bot.reply_to(
            message,
            "📸 **Screenshot saldo diterima!**\n"
            "✅ Sekarang kirim **format teks suntik bank**."
        )
        
    except Exception as e:
        print(f"❌ Error processing screenshot: {e}")
        bot.reply_to(message, "❌ Gagal menyimpan screenshot. Coba kirim ulang gambar.")

# ========== FITUR BARU: SUNIK BANK DENGAN SCREENSHOT ==========
@bot.message_handler(func=lambda m: "Tolong suntik dari rek Tampungan KPS" in m.text)
def handle_injection_request(message):
    """Handle permintaan suntik bank dengan/tanpa screenshot"""
    user_id = message.from_user.id
    officer = message.from_user.username or message.from_user.first_name
    msg_text = message.text
    
    # Parse SEMUA data dari officer (bukan dari spreadsheet)
    # Format yang officer kirim:
    # Wallet Addres : 
    # No Rek Bank : 
    # Jenis Bank : 
    # Nama Bank : 
    # Nominal Suntik : 
    # Saldo Akhir Bank : 
    # Asset :
    
    patterns = {
        'wallet': r"Wallet Addres :\s*(.+)",
        'no_rek': r"No Rek Bank :\s*(.+)",
        'jenis_bank': r"Jenis Bank :\s*(.+)",
        'nama_bank': r"Nama Bank :\s*(.+)",
        'nominal': r"Nominal Suntik :\s*(.+)",
        'saldo_akhir': r"Saldo Akhir Bank :\s*(.+)",
        'asset': r"Asset :\s*(.+)"
    }
    
    extracted_data = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, msg_text, re.IGNORECASE)
        extracted_data[key] = match.group(1).strip() if match else "N/A"
    
    # Cek apakah ada screenshot dari user ini (5 menit terakhir)
    screenshot_data = None
    screenshot_msg_id = None
    
    for msg_id, data in list(screenshot_storage.items()):
        if data['user_id'] == user_id:
            time_diff = (datetime.now() - data['timestamp']).seconds
            if time_diff < 300:  # 5 menit
                screenshot_data = data
                screenshot_msg_id = msg_id
                break
    
    # Simpan data sementara
    pending_injections[message.message_id] = {
        'wallet': extracted_data['wallet'],
        'asset': extracted_data['asset'],
        'officer': officer,
        'no_rek': extracted_data['no_rek'],
        'jenis_bank': extracted_data['jenis_bank'],
        'nama_bank': extracted_data['nama_bank'],
        'nominal': extracted_data['nominal'],
        'saldo_akhir': extracted_data['saldo_akhir'],
        'original_msg_id': message.message_id,
        'has_screenshot': screenshot_data is not None,
        'screenshot_path': screenshot_data['file_path'] if screenshot_data else None,
        'screenshot_msg_id': screenshot_msg_id
    }
    
    # Buat pesan approval sesuai format yang diminta
    approval_msg = (
        "💉 **PERMINTAAN SUNTIK BANK**\n\n"
        f"JENIS BANK : {extracted_data['jenis_bank']}\n"
        f"📊 Saldo Akhir: {extracted_data['saldo_akhir']}\n"
        f"No Rek Bank : {extracted_data['no_rek']}\n"
        f"📌 Asset: {extracted_data['asset']}\n\n"
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
    
    reply_text = "✅ Permintaan telah dikirim ke admin."
    if screenshot_data:
        reply_text += "\n📸 Screenshot telah dilampirkan."
    
    bot.reply_to(message, reply_text)

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
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            approver_name = "Alvin" if admin == "Vingeance" else "Joshua"
            
            try:
                sheet = get_sheet()
                # Update B3 dengan timestamp
                sheet.update('B3', [[current_time]])
                # Update K3 dengan nama approver
                sheet.update('K3', [[approver_name]])
                print(f"✅ Spreadsheet updated: B3={current_time}, K3={approver_name}")
            except Exception as e:
                print(f"❌ Spreadsheet error: {e}")
            # ========== END UPDATE ==========
            
            # Format pesan setelah approve sesuai permintaan
            bot.edit_message_text(
                f"✅ DISETUJUI oleh @{admin}\n"
                f"✍️ Approver: {approver_name}\n\n"
                f"Bank: {data['jenis_bank']}\n"
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
        
        # Cleanup: Hapus screenshot file dan data
        if data.get('has_screenshot') and data.get('screenshot_path'):
            try:
                if os.path.exists(data['screenshot_path']):
                    os.remove(data['screenshot_path'])
                    print(f"🗑️ Deleted screenshot: {data['screenshot_path']}")
            except Exception as e:
                print(f"❌ Error deleting screenshot: {e}")
        
        # Hapus dari storage
        if data.get('screenshot_msg_id') in screenshot_storage:
            del screenshot_storage[data['screenshot_msg_id']]
        
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

def handle_report_generic(message, report_type):
    try:
        text = message.text.strip()
        valid_types = [
            'REPORT CROSSBANK', 'REPORT PENDINGAN', 'REPORT PROCESS PENDINGAN',
            'REPORT MISTAKE', 'REPORT REFUND', 'REPORT FEE'
        ]
        if not any(text.startswith(t) for t in valid_types):
            return
        data = parse_report_text(text)
        required = ['aset', 'bank_member', 'bank_asset', 'amount', 'case', 'officer']
        if report_type == 'CROSSBANK':
            required.append('user_id')
        missing = [field for field in required if not data.get(field)]
        if missing:
            return
        success, result = save_crossbank_report(data)
        if success:
            bot.reply_to(message, "✅ REPORT BERHASIL DISIMPAN!")
    except:
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
    try:
        text = message.text.strip()
        first_line = text.split('\n')[0]
        parts = first_line.split()
        if len(parts) < 3:
            return
        user_id = parts[1]
        asset = parts[2]
        print(f"📩 Reset: {user_id} {asset}")
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

# Handler untuk abaikan media lain (untuk reset password tetap ignore)
@bot.message_handler(content_types=['document', 'video', 'audio', 'voice', 'sticker'])
def ignore_other_media(message):
    """Abaikan media lain (bukan photo)"""
    pass

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

# ========== BOT RUNNER ==========
def run_bot():
    """Jalankan Telegram bot"""
    print("🤖 Starting Telegram Bot...")
    bot.polling(
        none_stop=True,
        timeout=30,
        skip_pending=False  # Biarkan False untuk hindari conflict
    )

if __name__ == "__main__":
    print("=" * 50)
    print("🤖 X-SISTEM BOT - MULTI FUNCTIONS")
    print("📱 /reset [ID] [ASSET] - Reset password")
    print("📊 /report - Pilih jenis report")
    print("💉 Suntik Bank - Kirim format suntik (dengan screenshot)")
    print("📸 Screenshot disimpan untuk forward ke WhatsApp")
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
