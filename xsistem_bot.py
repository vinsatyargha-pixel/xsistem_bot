import telebot
import random
import string
from telebot import types
import time
import requests

TOKEN = "8087735462:AAGII-XvO3hJy3YgDd3b0vjiIHjnQCn4Ej4"
bot = telebot.TeleBot(TOKEN)

def buat_password():
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(10))

# ========== GOOGLE SHEETS VIA APPS SCRIPT ==========
def save_crossbank_report(data):
    """Simpan report ke Google Sheets via Apps Script"""
    try:
        web_app_url = "https://script.google.com/macros/s/AKfycbwGpv7pgFrMRccC0y3IkkQxcehSX3D0nLMZYWkFtjywVF2AIpj4R1MEj5mtaYd-U_TLVw/exec"
        
        payload = {
            'message': {
                'text': data['original_text']
            }
        }
        
        response = requests.post(web_app_url, json=payload, timeout=10)
        
        if response.status_code == 200:
            return True, "Data tersimpan"
        else:
            return False, f"Error: {response.status_code}"
            
    except Exception as e:
        return False, str(e)

def parse_report_text(text):
    """Parse text report menjadi dictionary"""
    data = {'original_text': text}
    lines = text.split('\n')
    
    for line in lines:
        if ':' in line:
            parts = line.split(':', 1)
            key = parts[0].strip().lower().replace(' ', '_')
            value = parts[1].strip()
            data[key] = value
    
    return data

# ========== COMMAND HANDLERS ==========
@bot.message_handler(commands=['formatreset'])
def handle_format_reset(message):
    """Command /formatreset untuk format reset password"""
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
    """Command /formatreport untuk tampilkan semua format report"""
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
    """Command /report untuk pilih jenis report"""
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
            "📊 *PILIH JENIS REPORT:*\n\n"
            "Atau ketik langsung:\n"
            "• REPORT CROSSBANK\n"
            "• REPORT PENDINGAN\n"
            "• REPORT MISTAKE\n"
            "• dll...\n\n"
            "Untuk format lengkap: /formatreport",
            reply_markup=markup,
            parse_mode='Markdown'
        )
    except:
        pass

@bot.callback_query_handler(func=lambda call: call.data.startswith('report_'))
def handle_report_type(call):
    """Handle pemilihan jenis report"""
    try:
        report_type = call.data.replace('report_', '')
        
        formats = {
            'crossbank': """
📋 *FORMAT REPORT CROSSBANK*

REPORT CROSSBANK
ASET: BTC
USER ID: 123456
BANK MEMBER: BCA
BANK ASSET: Binance
NO TICKET: TKT789
AMOUNT: 5000000
CASE: Fraud
OFFICER: John Doe""",
            
            'pendingan': """
⏳ *FORMAT REPORT PENDINGAN*

REPORT PENDINGAN
ASET: BTC
USER ID: 123456
BANK MEMBER: BCA
BANK ASSET: Binance
NO TICKET: TKT789
AMOUNT: 5000000
CASE: Input Pendingan Deposit
OFFICER: John Doe""",
            
            'process_pendingan': """
🔄 *FORMAT REPORT PROCESS PENDINGAN*

REPORT PROCESS PENDINGAN
ASET: BTC
USER ID: 123456
BANK MEMBER: BCA
BANK ASSET: Binance
NO TICKET: TKT789
AMOUNT: 5000000
CASE: Proses Pendingan Deposit
OFFICER: John Doe""",
            
            'mistake': """
❌ *FORMAT REPORT MISTAKE*

REPORT MISTAKE
ASET: BTC
USER ID: 123456
BANK MEMBER: BCA
BANK ASSET: Binance
NO TICKET: TKT789
AMOUNT: 5000000
CASE: Kesalahan Input Data
OFFICER: John Doe""",
            
            'refund': """
↩️ *FORMAT REPORT REFUND*

REPORT REFUND
ASET: BTC
USER ID: 123456
BANK MEMBER: BCA
BANK ASSET: Binance
NO TICKET: TKT789
AMOUNT: 5000000
CASE: Pengembalian Dana
OFFICER: John Doe""",
            
            'fee': """
💰 *FORMAT REPORT FEE*

REPORT FEE
ASET: BTC
USER ID: 123456
BANK MEMBER: BCA
BANK ASSET: Binance
NO TICKET: TKT789
AMOUNT: 5000000
CASE: Biaya Admin/Operasional
OFFICER: John Doe"""
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

# ========== UNIVERSAL REPORT HANDLER ==========
def handle_report_generic(message, report_type):
    """Handle semua jenis report"""
    try:
        text = message.text.strip()
        
        # Validasi JANGAN TYPO
        valid_types = [
            'REPORT CROSSBANK',
            'REPORT PENDINGAN', 
            'REPORT PROCESS PENDINGAN',
            'REPORT MISTAKE',
            'REPORT REFUND',
            'REPORT FEE'
        ]
        
        if not any(text.startswith(t) for t in valid_types):
            return  # Abaikan typo, biarkan agent edit sendiri
        
        # Parse data
        data = parse_report_text(text)
        
        # Validasi field wajib
        required = ['aset', 'bank_member', 'bank_asset', 'amount', 'case', 'officer']
        
        # Untuk CROSSBANK, USER ID wajib
        if report_type == 'CROSSBANK':
            required.append('user_id')
        
        missing = [field for field in required if not data.get(field)]
        
        if missing:
            # Tidak perlu reply, biarkan agent lengkapi sendiri
            return
        
        # Simpan ke Google Sheets
        success, result = save_crossbank_report(data)
        
        if success:
            bot.reply_to(message, "✅ REPORT BERHASIL DISIMPAN!")
        # Tidak perlu else, biarkan fail silent
    except:
        pass  # ABORT SEMUA ERROR, BIARKAN FLOW LANGSUNG

# ========== SPECIFIC REPORT HANDLERS ==========
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

# ========== RESET PASSWORD HANDLERS ==========
@bot.message_handler(func=lambda m: m.text and not m.forward_from and any(
    cmd in m.text.lower() for cmd in ['/reset', '/repass', '/repas']
))
def handle_reset_only_text(message):
    """Handle reset command dengan format multi-line"""
    try:
        text = message.text.strip()
        
        # Ambil hanya baris pertama untuk parsing
        first_line = text.split('\n')[0]
        parts = first_line.split()
        
        if len(parts) < 3:
            return  # Format salah, silent abort
        
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
            f"🔔 *RESET REQUEST*\n\n"
            f"👤 CS: {message.from_user.first_name}\n"
            f"🆔 User: `{user_id}`\n"
            f"🎮 Asset: `{asset}`\n\n"
            f"**PILIH:**",
            reply_markup=markup,
            parse_mode='Markdown'
        )
    except:
        pass  # Abaikan error

@bot.message_handler(content_types=['photo', 'document', 'video', 'audio', 'voice'])
def ignore_all_media(message):
    """ABAIKAN SEMUA MEDIA"""
    pass

@bot.callback_query_handler(func=lambda call: call.data.startswith('ok_') or call.data.startswith('no_'))
def handle_reset_callback(call):
    """Handle reset callback - TANPA REPLY TO MESSAGE"""
    try:
        if call.data.startswith('ok_'):
            _, cs_id, user_id, asset = call.data.split('_')
            
            password = buat_password()
            
            # KIRIM PASSWORD (TANPA REPLY)
            bot.send_message(
                call.message.chat.id,
                f"{user_id} - {asset}\nPassword baru : {password}"
            )
            
            # UPDATE TOMBOL
            bot.edit_message_text(
                f"✅ *RESET DISETUJUI*\n\n"
                f"User: `{user_id}`\n"
                f"Asset: `{asset}`\n"
                f"Password: `{password}`",
                call.message.chat.id,
                call.message.message_id,
                parse_mode='Markdown'
            )
            
            bot.answer_callback_query(call.id, "✅ Password dikirim")
            
        elif call.data.startswith('no_'):
            # KIRIM PESAN TOLAK (TANPA REPLY)
            bot.send_message(
                call.message.chat.id,
                "❌ Permintaan ditolak Captain !!"
            )
            
            bot.edit_message_text(
                "❌ *REQUEST DITOLAK*",
                call.message.chat.id,
                call.message.message_id,
                parse_mode='Markdown'
            )
            
            bot.answer_callback_query(call.id, "❌ Ditolak")
    except:
        try:
            bot.answer_callback_query(call.id, "⚠️ Action gagal")
        except:
            pass

if __name__ == "__main__":
    print("🤖 X-SISTEM BOT - SILENT MODE")
    print("📱 /reset [ID] [ASSET] - Reset password")
    print("📱 /formatreset - Format reset password")
    print("📊 /report - Pilih jenis report")
    print("📋 /formatreport - Format semua report")
    print("🚫 Auto abort jika error")
    
    # Start polling dengan skip pending
    bot.polling(
        none_stop=True,
        timeout=30,
        skip_pending=True  # Skip old messages
    )

