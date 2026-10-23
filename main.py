import os
import threading
import time
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask
from groq import Groq

# ═══════════════════════════════════════════════════════
# CONFIGURATION (Render ke Environment Variables se aayega)
# ═══════════════════════════════════════════════════════
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE") 
ADMIN_ID = int(os.getenv("ADMIN_ID", "123456789")) 
TRC20_WALLET = os.getenv("TRC20_WALLET", "T_YOUR_DEFAULT_ADDRESS_HERE")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "YOUR_GROQ_KEY_HERE")

bot = telebot.TeleBot(BOT_TOKEN)

try:
    ai_client = Groq(api_key=GROQ_API_KEY)
except Exception as e:
    ai_client = None

app = Flask(__name__)

try:
    bot.remove_webhook()
    print("✅ Webhook removed successfully.")
except Exception as e:
    pass

# 🆕 Storage (Admin ke message ko User se jodne ke liye)
user_plan = {}
admin_msg_map = {} # Ye map batayega ki Admin ne kis message ka reply kiya hai

PLAN_NAMES = {
    "plan_100": "1 Month ($100)",
    "plan_200": "3 Months ($200)",
    "plan_300": "6 Months ($300)",
    "plan_500": "1 Year ($500)"
}

SYSTEM_PROMPT = """
You are 'SuperBot Support AI', a helpful customer support assistant for a premium automated MetaTrader 5 (MT5) trading bot.
Pricing: 1M=$100, 3M=$200, 6M=$300, 1Y=$500.
Payment: USDT (TRC20 network).
Answer politely in English or Hinglish. Keep it short. Do not guarantee profits.
"""

# ═══════════════════════════════════════════════════════
# USER HANDLERS
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
        markup.add(InlineKeyboardButton("💳 Payment Details", callback_data="payment_info"))
        
        bot.send_message(
            chat_id, 
            f"👋 <b>Welcome!</b>\n\nAapne <b>{plan_name}</b> select kiya hai.\n\n"
            f"Kripya payment karein aur <b>Screenshot</b> bhejein.",
            reply_markup=markup, parse_mode="HTML"
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
            "Plan select karein ya koi sawal poochhein (Main AI hoon!):", 
            reply_markup=markup, parse_mode="HTML"
        )

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    chat_id = call.message.chat.id
    
    if call.data == "payment_info":
        bot.answer_callback_query(call.id, "Details bhej rahe hain...")
        bot.send_message(
            chat_id,
            f"💳 <b>Payment Details (USDT TRC20):</b>\n\n"
            f"🪙 Coin: <b>USDT</b>\n"
            f"🌐 Network: <b>TRC20</b>\n"
            f"👛 Address:\n<code>{TRC20_WALLET}</code>\n\n"
            f"Payment ke baad <b>Screenshot</b> bhejein!",
            parse_mode="HTML"
        )
        
    elif call.data.startswith("plan_"):
        plan_name = PLAN_NAMES.get(call.data, "Unknown")
        user_plan[chat_id] = plan_name
        bot.answer_callback_query(call.id, f"{plan_name} Selected!")
        
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("💳 Payment Details", callback_data="payment_info"))
        
        bot.edit_message_text(
            chat_id=chat_id, message_id=call.message.message_id,
            text=f"✅ Aapne <b>{plan_name}</b> select kiya hai.\n\nScreenshot bhejein.",
            reply_markup=markup, parse_mode="HTML"
        )

@bot.message_handler(content_types=['photo', 'document'])
def handle_proof(message):
    chat_id = message.chat.id
    
    if chat_id not in user_plan:
        bot.reply_to(message, "⚠️ Kripya pehle /start karke plan select karein!")
        return

    plan_name = user_plan[chat_id]
    username = message.from_user.username or "No Username"
    
    bot.reply_to(message, "⏳ <b>Proof Received!</b>\n\nAdmin verify kar raha hai. 1-2 ghante me key mil jayegi.", parse_mode="HTML")
    
    # Admin ko alert
    alert_text = (
        f"🚨 <b>NEW PAYMENT PROOF</b>\n\n"
        f"👤 User: @{username}\n"
        f"🆔 ID: <code>{chat_id}</code>\n"
        f"📦 Plan: <b>{plan_name}</b>\n\n"
        f"👉 <b>Reply to this message with:</b> <code>OK YOUR_KEY</code>"
    )
    admin_msg = bot.send_message(ADMIN_ID, alert_text, parse_mode="HTML")
    
    # Photo forward karein aur map save karein
    forwarded = bot.forward_message(ADMIN_ID, chat_id, message.message_id)
    admin_msg_map[forwarded.message_id] = chat_id 

# ═══════════════════════════════════════════════════════
# 🆕 ADMIN REPLY HANDLER (Auto Delivery System)
# ═══════════════════════════════════════════════════════
@bot.message_handler(func=lambda message: message.chat.id == ADMIN_ID and message.reply_to_message, content_types=['text'])
def handle_admin_reply(message):
    text = message.text.strip()
    
    # Check karein ki admin ne "OK" se start kiya hai ya nahi
    if text.upper().startswith("OK "):
        license_key = text[3:].strip() # "OK " ke baad ki key nikaalein
        
        # Pata lagayein ki ye kis user ka screenshot tha
        user_chat_id = admin_msg_map.get(message.reply_to_message.message_id)
        
        if user_chat_id:
            # User ko key bhejein
            bot.send_message(
                user_chat_id,
                f"🎉 <b>Payment Verified Successfully!</b>\n\n"
                f"🔑 <b>Your License Key:</b>\n<code>{license_key}</code>\n\n"
                f"✅ <b>How to Activate:</b>\n"
                f"1. Open the bot software.\n"
                f"2. Enter this key when prompted.\n"
                f"3. Enjoy automated trading!\n\n"
                f"Agar koi dikkat aaye, toh yahin message karein.",
                parse_mode="HTML"
            )
            
            # Admin ko confirm karein
            bot.reply_to(message, f"✅ Key successfully sent to User ID: {user_chat_id}!")
            
            # Clean up memory
            del admin_msg_map[message.reply_to_message.message_id]
            if user_chat_id in user_plan: del user_plan[user_chat_id]
        else:
            bot.reply_to(message, "⚠️ User ID not found. Make sure you replied to the forwarded photo.")
    else:
        bot.reply_to(message, "⚠️ Invalid format. Reply with: OK YOUR_KEY")

# ═══════════════════════════════════════════════════════
# AI CHAT HANDLER (Only for normal users, not admin replies)
# ═══════════════════════════════════════════════════════
@bot.message_handler(func=lambda message: message.text and not message.text.startswith('/') and message.chat.id != ADMIN_ID)
def handle_ai_chat(message):
    chat_id = message.chat.id
    user_text = message.text

    if not ai_client:
        bot.reply_to(message, "⚠️ AI service is down. Kripya /start dabayein.")
        return

    bot.send_chat_action(chat_id, 'typing')
    try:
        response = ai_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_text}
            ],
            temperature=0.5, max_tokens=250
        )
        bot.reply_to(message, response.choices[0].message.content)
    except Exception as e:
        bot.reply_to(message, "⚠️ Sorry, main busy hoon. /start dabayein.")

# ═══════════════════════════════════════════════════════
# SERVER START
# ═══════════════════════════════════════════════════════
@app.route('/')
def home(): return "SuperBot Server is Alive!"

def run_bot():
    print("🚀 Bot is starting...")
    while True:
        try:
            bot.infinity_polling(skip_pending=True, timeout=20, long_polling_timeout=10)
        except Exception as e:
            time.sleep(5)

if __name__ == '__main__':
    threading.Thread(target=run_bot, daemon=True).start()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
