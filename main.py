import os
import threading
import time
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask
from groq import Groq

# ═══════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE") 
ADMIN_ID = int(os.getenv("ADMIN_ID", "0")) 
TRC20_WALLET = os.getenv("TRC20_WALLET", "T_YOUR_DEFAULT_ADDRESS_HERE")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

bot = telebot.TeleBot(BOT_TOKEN)

try:
    ai_client = Groq(api_key=GROQ_API_KEY)
except Exception:
    ai_client = None

app = Flask(__name__)

try:
    bot.remove_webhook()
except Exception:
    pass

user_plan = {}
admin_msg_map = {}

PLAN_NAMES = {
    "plan_100": "1 Month ($100)",
    "plan_200": "3 Months ($200)",
    "plan_300": "6 Months ($300)",
    "plan_500": "1 Year ($500)"
}

# 🆕 STRICT PROMPT: AI ko chhota aur seedha jawab dene ko kaha gaya hai
SYSTEM_PROMPT = """
You are 'SuperBot AI', a professional sales agent for the 'SuperBot v2.1.1' automated MT5 trading bot.
Your ONLY goal is to answer the user's question briefly and encourage them to buy a plan.

FACTS:
- Automated MT5 bot (EURUSD & XAUUSD).
- 33+ Strategies, Anti-Blowup protection.
- Payment: USDT TRC20 ONLY.

RULES:
1. Reply in Hindi (Hinglish) or English based on the user.
2. MAXIMUM 2 SENTENCES. Do not write long paragraphs.
3. DO NOT talk about unrelated topics. Keep it strictly about the bot and payment.
4. Always end with: "Neeche diye gaye buttons se plan select karein ya payment details dekhein."
"""

# ═══════════════════════════════════════════════════════
# START COMMAND
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
        markup.add(InlineKeyboardButton("💳 Payment Details (USDT)", callback_data="payment_info"))
        
        bot.send_message(
            chat_id, 
            f"👋 <b>Welcome!</b>\n\nAapne <b>{plan_name}</b> select kiya hai.\n\n"
            f"Kripya payment karein aur <b>Screenshot</b> bhejein.",
            reply_markup=markup, parse_mode="HTML"
        )
    else:
        # Buttons for plans + payment
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("1 Month ($100)", callback_data="plan_100"),
            InlineKeyboardButton("3 Months ($200)", callback_data="plan_200"),
            InlineKeyboardButton("6 Months ($300) 🔥", callback_data="plan_300"),
            InlineKeyboardButton("1 Year ($500) ⭐", callback_data="plan_500"),
            InlineKeyboardButton("💳 Payment Info (USDT)", callback_data="payment_info")
        )
        bot.send_message(
            chat_id, 
            "👋 <b>Hello! Main SuperBot ka AI Assistant hoon.</b>\n\n"
            "Ye ek fully automated MT5 bot hai jo Gold & Euro trade karta hai.\n\n"
            "<b>Plans:</b>\n1M - $100\n3M - $200\n6M - $300\n1Y - $500\n\n"
            "Neeche se plan select karein ya koi sawal poochhein!", 
            reply_markup=markup, parse_mode="HTML"
        )

# ═══════════════════════════════════════════════════════
# CALLBACK HANDLER (Buttons)
# ═══════════════════════════════════════════════════════
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    chat_id = call.message.chat.id
    
    if call.data == "payment_info":
        bot.answer_callback_query(call.id, "Details bhej rahe hain...")
        bot.send_message(
            chat_id,
            f"💳 <b>Payment Details (USDT TRC20 ONLY):</b>\n\n"
            f"🪙 Coin: <b>USDT</b>\n🌐 Network: <b>TRC20 (Tron)</b>\n"
            f"👛 Address:\n<code>{TRC20_WALLET}</code>\n\n"
            f"⚠️ <b>Warning:</b> Sirf TRC20 par payment karein. UPI accept nahi karte.\n\n"
            f"Payment ke baad <b>Screenshot</b> bhejein!",
            parse_mode="HTML"
        )
        
    elif call.data.startswith("plan_"):
        plan_name = PLAN_NAMES.get(call.data, "Unknown")
        user_plan[chat_id] = plan_name
        bot.answer_callback_query(call.id, f"{plan_name} Selected!")
        
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("💳 Payment Details (USDT)", callback_data="payment_info"))
        bot.edit_message_text(
            chat_id=chat_id, message_id=call.message.message_id,
            text=f"✅ Aapne <b>{plan_name}</b> select kiya hai.\n\nKripya payment karein aur screenshot bhejein.",
            reply_markup=markup, parse_mode="HTML"
        )

# ═══════════════════════════════════════════════════════
# PHOTO HANDLER (Payment Proof)
# ═══════════════════════════════════════════════════════
@bot.message_handler(content_types=['photo', 'document'])
def handle_proof(message):
    chat_id = message.chat.id
    
    if chat_id not in user_plan:
        bot.reply_to(message, "⚠️ Kripya pehle plan select karein (/start dabayein)!")
        return

    plan_name = user_plan[chat_id]
    username = message.from_user.username or "No Username"
    
    bot.reply_to(message, "⏳ <b>Proof Received!</b>\n\nAdmin verify kar raha hai. Aapko jaldi hi key mil jayegi.", parse_mode="HTML")
    
    if ADMIN_ID != 0:
        alert_text = (
            f"🚨 <b>NEW PAYMENT PROOF</b>\n\n"
            f"👤 User: @{username}\n"
            f"🆔 ID: <code>{chat_id}</code>\n"
            f"📦 Plan: <b>{plan_name}</b>\n\n"
            f"👉 <b>Reply to THIS message with:</b> <code>OK YOUR_KEY</code>"
        )
        admin_msg = bot.send_message(ADMIN_ID, alert_text, parse_mode="HTML")
        admin_msg_map[admin_msg.message_id] = chat_id
        
        forwarded = bot.forward_message(ADMIN_ID, chat_id, message.message_id)
        admin_msg_map[forwarded.message_id] = chat_id

# ═══════════════════════════════════════════════════════
# 👑 ADMIN OK KEY HANDLER
# ═══════════════════════════════════════════════════════
@bot.message_handler(func=lambda message: message.chat.id == ADMIN_ID and message.reply_to_message, content_types=['text'])
def handle_admin_reply(message):
    text = message.text.strip()
    
    if text.upper().startswith("OK "):
        license_key = text[3:].strip()
        user_chat_id = admin_msg_map.get(message.reply_to_message.message_id)
        
        if user_chat_id:
            try:
                bot.send_message(
                    user_chat_id,
                    f"🎉 <b>Payment Verified Successfully!</b>\n\n"
                    f"🔑 <b>Your License Key:</b>\n<code>{license_key}</code>\n\n"
                    f"✅ <b>Activation Process:</b>\n"
                    f"1. Open SuperBot software.\n"
                    f"2. Enter this key.\n"
                    f"3. Bot will start trading!\n\n"
                    f"Koi dikkat aaye toh message karein.",
                    parse_mode="HTML"
                )
                bot.reply_to(message, f"✅ Key successfully sent to User ID: {user_chat_id}!")
            except Exception as e:
                bot.reply_to(message, f"❌ Error: {e}")
            
            del admin_msg_map[message.reply_to_message.message_id]
            if user_chat_id in user_plan: del user_plan[user_chat_id]

# ═══════════════════════════════════════════════════════
# 🤖 AI CHAT HANDLER (Short reply + Always show buttons)
# ═══════════════════════════════════════════════════════
@bot.message_handler(func=lambda message: message.text and not message.text.startswith('/'))
def handle_ai_chat(message):
    chat_id = message.chat.id
    
    if chat_id == ADMIN_ID and message.reply_to_message and message.text.strip().upper().startswith("OK "):
        return

    if not ai_client or not GROQ_API_KEY:
        bot.reply_to(message, "⚠️ AI service is down. (Missing GROQ_API_KEY)")
        return

    bot.send_chat_action(chat_id, 'typing')
    try:
        response = ai_client.chat.completions.create(
            model="llama-3.1-8b-instant", # Fast model for quick, short answers
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": message.text}
            ],
            temperature=0.4, max_tokens=100 # Max tokens restricted to keep it short
        )
        
        ai_reply = response.choices[0].message.content
        
        # 🆕 HAR REPLY KE SAATH BUTTONS AUR PAYMENT MESSAGE
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("1 Month ($100)", callback_data="plan_100"),
            InlineKeyboardButton("3 Months ($200)", callback_data="plan_200"),
            InlineKeyboardButton("6 Months ($300) 🔥", callback_data="plan_300"),
            InlineKeyboardButton("1 Year ($500) ⭐", callback_data="plan_500"),
            InlineKeyboardButton("💳 Payment Details (USDT)", callback_data="payment_info")
        )
        
        # Add standard footer
        final_msg = f"{ai_reply}\n\n👇 <b>Buy SuperBot:</b>\nNeeche se plan select karein ya payment details dekhein."
        
        bot.reply_to(message, final_msg, reply_markup=markup, parse_mode="HTML")

    except Exception as e:
        print(f"AI Error: {e}")
        bot.reply_to(message, "⚠️ AI is busy. Kripya /start dabayein.")
        
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
        except Exception:
            time.sleep(5)

if __name__ == '__main__':
    threading.Thread(target=run_bot, daemon=True).start()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
