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
        web_app_url = "https://script.google.com/macros/s/AKfycbzkvryqKNNXntNMrXwmv-aoqAU8ZRGmid9TXHLlU4dVY7pgCd9CUh0dMgA7jagc83yweA/exec"
        
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
@bot.message_handler(commands=['format'])
def handle_format_command(message):
    """Command /format untuk tampilkan semua format"""
    format_text = """
📋 *(PILIH SALAH SATU KATEGORI - JANGAN TYPO)*

*REPORT CROSSBANK*
*REPORT MISTAKE*
*REPORT FEE*
*REPORT PENDINGAN*
*REPORT PROCESS PENDINGAN*
*REPORT REFUND*

*FORMAT:*
ASET: [BTC/ETH/dll]
USER ID: [123456]
BANK MEMBER: [BCA/BRI/dll]
BANK ASSET: [Binance/Triv/dll]
NO TICKET: [TKT001]
AMOUNT: [5000000]
CASE: [Keterangan]
OFFICER: [Nama Officer]

*Contoh:*
REPORT CROSSBANK
ASET: BTC
USER ID: 123456
BANK MEMBER: BCA
BANK ASSET: Binance
NO TICKET: TKT789
AMOUNT: 5000000
CASE: Fraud
OFFICER: John Doe
"""
    bot.reply_to(message, format_text, parse_mode='Markdown')

@bot.message_handler(commands=['report'])
def handle_report_command(message):
    """Command /report untuk pilih jenis report"""
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
        "📊 *PILIH JENIS REPORT:*",
        reply_markup=markup,
        parse_mode='Markdown'
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('report_'))
def handle_report_type(call):
    """Handle pemilihan jenis report"""
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
            error_msg = f"❌ *TYPOS DETECTED!*\nGunakan salah satu:\n"
            error_msg += "\n".join([f"• {t}" for t in valid_types])
            bot.reply_to(message, error_msg, parse_mode='Markdown')
            return
        
        # Parse data
        data = parse_report_text(text)
        
        # Validasi field wajib
        required = ['aset', 'bank_member', 'bank_asset', 'amount', 'case', 'officer']
        
        # Untuk CROSSBANK, USER ID wajib
        if report_type == 'CROSSBANK':
            required.append('user_id')
        
        missing = [field for field in required if not data.get(field)]
        
        if missing:
            bot.reply_to(message, f"❌ Data kurang: {', '.join(missing).replace('_', ' ').upper()}")
            return
        
        # Simpan ke Google Sheets
        success, result = save_crossbank_report(data)
        
        if success:
            # RESPONSE SIMPLE ✅
            bot.reply_to(message, "✅ REPORT BERHASIL DISIMPAN!")
        else:
            bot.reply_to(message, f"❌ Gagal simpan: {result}")
            
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

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
    """HANYA proses text message asli, BUKAN caption foto/forward"""
    try:
        text = message.text.strip()
        parts = text.split()
        
        if len(parts) < 3:
            bot.reply_to(message, "Format: /reset ID ASSET\nContoh: /reset MAGNIX XLY")
            return
        
        user_id = parts[1]
        asset = parts[2]
        
        print(f"📩 Reset TEXT: {user_id} {asset}")
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("✅ Reset", callback_data=f"ok_{message.from_user.id}_{user_id}_{asset}"),
            types.InlineKeyboardButton("❌ Tolak", callback_data=f"no_{message.from_user.id}")
        )
        
        bot.reply_to(
            message,
            f"🔔 *RESET REQUEST*\n\n"
            f"👤 CS: {message.from_user.full_name}\n"
            f"🆔 User: `{user_id}`\n"
            f"🎮 Asset: `{asset}`\n\n"
            f"**PILIH:**",
            reply_markup=markup,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        print(f"❌ Error: {e}")

@bot.message_handler(content_types=['photo', 'document', 'video', 'audio', 'voice'])
def ignore_all_media(message):
    pass

@bot.callback_query_handler(func=lambda call: call.data.startswith('ok_') or call.data.startswith('no_'))
def handle_reset_callback(call):
    try:
        if call.data.startswith('ok_'):
            _, cs_id, user_id, asset = call.data.split('_')
            cs_id = int(cs_id)
            
            password = buat_password()
            
            message_text = f"{user_id} - {asset}\nPassword baru : {password}"
            
            bot.send_message(
                call.message.chat.id,
                message_text,
                reply_to_message_id=call.message.reply_to_message.message_id
            )
            
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
            cs_id = int(call.data.split('_')[1])
            
            bot.send_message(
                call.message.chat.id,
                "❌ Permintaan ditolak Captain !!",
                reply_to_message_id=call.message.reply_to_message.message_id
            )
            
            bot.edit_message_text(
                f"❌ *REQUEST DITOLAK*",
                call.message.chat.id,
                call.message.message_id,
                parse_mode='Markdown'
            )
            
            bot.answer_callback_query(call.id, "❌ Ditolak")
            
    except Exception as e:
        print(f"❌ Callback error: {e}")
        bot.answer_callback_query(call.id, "❌ Error")

if __name__ == "__main__":
    print("🤖 X-SISTEM BOT STARTED")
    print("📱 /reset [ID] [ASSET] - Reset password")
    print("📊 /report - Pilih jenis report")
    print("📋 /format - Tampilkan semua format")
    print("⏳ REPORT PENDINGAN - Input pendingan deposit")
    print("🔄 REPORT PROCESS PENDINGAN - Proses pendingan")
    print("❌ REPORT MISTAKE - Kesalahan input")
    print("↩️ REPORT REFUND - Pengembalian dana")
    print("💰 REPORT FEE - Biaya admin/operasional")
    bot.polling(none_stop=True)
