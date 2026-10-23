import os
import threading
import time
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask

# ═══════════════════════════════════════════════════════
# CONFIGURATION (Render ke Environment Variables se aayega)
# ═══════════════════════════════════════════════════════
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE") 
ADMIN_ID = int(os.getenv("ADMIN_ID", "123456789")) 
TRC20_WALLET = os.getenv("TRC20_WALLET", "T_YOUR_DEFAULT_ADDRESS_HERE")

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# 🔥 AUTO FIX: Purana webhook delete karo taaki naya bot polling me atak na jaye
try:
    bot.remove_webhook()
    print("✅ Webhook removed successfully.")
except Exception as e:
    print(f"⚠️ Webhook removal error: {e}")

# Temp Storage
user_plan = {}

# ═══════════════════════════════════════════════════════
# PLAN MAP
# ═══════════════════════════════════════════════════════
PLAN_NAMES = {
    "plan_100": "1 Month ($100)",
    "plan_200": "3 Months ($200)",
    "plan_300": "6 Months ($300)",
    "plan_500": "1 Year ($500)"
}

# ═══════════════════════════════════════════════════════
# HANDLERS
# ═══════════════════════════════════════════════════════

@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    args = message.text.split()

    if len(args) > 1:
        plan_code = args[1]
        plan_name = PLAN_NAMES.get(plan_code, "Unknown Plan")
        user_plan[chat_id] = plan_name
        
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("💳 Payment Details (USDT TRC20)", callback_data="payment_info"))
        
        bot.send_message(
            chat_id, 
            f"👋 <b>Welcome to SuperBot!</b>\n\n"
            f"Aapne <b>{plan_name}</b> plan select kiya hai.\n\n"
            f"Kripya payment details dekhein aur payment ke baad <b>Screenshot</b> yahan bhejein.",
            reply_markup=markup,
            parse_mode="HTML"
        )
    else:
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("1 Month ($100)", callback_data="plan_100"),
            InlineKeyboardButton("3 Months ($200)", callback_data="plan_200"),
            InlineKeyboardButton("6 Months ($300) 🔥", callback_data="plan_300"),
            InlineKeyboardButton("1 Year ($500) ⭐", callback_data="plan_500")
        )
        bot.send_message(
            chat_id, 
            "👋 <b>Welcome to SuperBot!</b>\n\n"
            "Kripya apna plan select karein:", 
            reply_markup=markup, 
            parse_mode="HTML"
        )

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    chat_id = call.message.chat.id
    
    if call.data == "payment_info":
        bot.answer_callback_query(call.id, "Payment details bhej rahe hain...")
        
        bot.send_message(
            chat_id,
            f"💳 <b>Payment Details (USDT TRC20):</b>\n\n"
            f"🪙 Coin: <b>USDT</b>\n"
            f"🌐 Network: <b>TRC20 (Tron)</b>\n"
            f"👛 Wallet Address:\n"
            f"<code>{TRC20_WALLET}</code>\n\n"
            f"⚠️ <b>Important:</b> Sirf TRC20 network par hi payment karein.\n\n"
            f"Payment ke baad <b>Screenshot</b> ya <b>Transaction Hash (TxID)</b> yahan bhejein!",
            parse_mode="HTML"
        )
        
    elif call.data.startswith("plan_"):
        plan_name = PLAN_NAMES.get(call.data, "Unknown Plan")
        user_plan[chat_id] = plan_name
        
        bot.answer_callback_query(call.id, f"{plan_name} Selected!")
        
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("💳 Payment Details (USDT TRC20)", callback_data="payment_info"))
        
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text=f"✅ Aapne <b>{plan_name}</b> select kiya hai.\n\n"
                 f"Kripya payment details dekhein aur screenshot bhejein.",
            reply_markup=markup,
            parse_mode="HTML"
        )

@bot.message_handler(content_types=['photo', 'document'])
def handle_proof(message):
    chat_id = message.chat.id
    
    if chat_id not in user_plan:
        bot.reply_to(message, "⚠️ Kripya pehle /start karke apna plan select karein!")
        return

    plan_name = user_plan[chat_id]
    username = message.from_user.username or "No Username"
    
    bot.reply_to(message, "⏳ <b>Proof Received!</b>\n\nAdmin aapka payment verify kar raha hai. 1-2 ghante me bot access mil jayega.", parse_mode="HTML")
    
    alert_text = (
        f"🚨 <b>NAYA PAYMENT PROOF</b> 🚨\n\n"
        f"👤 Username: @{username}\n"
        f"🆔 User ID: <code>{chat_id}</code>\n"
        f"📦 Plan: <b>{plan_name}</b>\n\n"
        f"⚠️ Niche forward ki hui photo check karein."
    )
    bot.send_message(ADMIN_ID, alert_text, parse_mode="HTML")
    bot.forward_message(ADMIN_ID, chat_id, message.message_id)

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    bot.reply_to(message, "📸 Kripya payment ka screenshot (photo) bhejein. Ya /start karke plan select karein.")

# ═══════════════════════════════════════════════════════
# FLASK SERVER & BOT START
# ═══════════════════════════════════════════════════════
@app.route('/')
def home():
    return "SuperBot Telegram Server is Alive!"

def run_bot():
    print("🚀 Bot is starting (Polling Mode)...")
    while True:
        try:
            bot.infinity_polling(skip_pending=True, timeout=20, long_polling_timeout=10)
        except Exception as e:
            print(f"⚠️ Polling error: {e}")
            time.sleep(5) # Agar error aaye toh 5 second baad wapas start hoga

if __name__ == '__main__':
    threading.Thread(target=run_bot, daemon=True).start()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
