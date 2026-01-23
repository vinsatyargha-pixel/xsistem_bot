import telebot
import random
import string
from telebot import types
import time
import requests
import os
import threading
from flask import Flask

TOKEN = "8087735462:AAGII-XvO3hJy3YgDd3b0vjiIHjnQCn4Ej4"
bot = telebot.TeleBot(TOKEN)

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

# ========== BOT FUNCTIONS (SAMA DENGAN KODE LAMA) ==========
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

# ========== COMMAND HANDLERS ==========
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

@bot.message_handler(content_types=['photo', 'document', 'video', 'audio', 'voice'])
def ignore_all_media(message):
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
    print("🤖 X-SISTEM BOT - HYBRID MODE (FREE TIER)")
    print("📱 /reset [ID] [ASSET] - Reset password")
    print("📊 /report - Pilih jenis report")
    print("🌐 Web server: http://0.0.0.0:${PORT}")
    print("=" * 50)
    
    # Jalankan Flask di thread terpisah
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Jalankan bot (main thread)
    run_bot()
