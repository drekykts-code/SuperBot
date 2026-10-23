import os
import threading
import time
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask
from groq import Groq

# ═══════════════════════════════════════════════════════
# CONFIGURATION (Render Environment Variables)
# ═══════════════════════════════════════════════════════
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE") 
ADMIN_ID = int(os.getenv("ADMIN_ID", "0")) 
TRC20_WALLET = os.getenv("TRC20_WALLET", "T_YOUR_DEFAULT_ADDRESS_HERE")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

bot = telebot.TeleBot(BOT_TOKEN)

try:
    ai_client = Groq(api_key=GROQ_API_KEY)
    if not GROQ_API_KEY:
        print("⚠️ WARNING: GROQ_API_KEY is missing! AI will not work.")
except Exception as e:
    ai_client = None
    print(f"⚠️ AI Init Error: {e}")

app = Flask(__name__)

try:
    bot.remove_webhook()
    print("✅ Webhook removed successfully.")
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

SYSTEM_PROMPT = """
You are 'SuperBot AI', a smart, fast, and polite sales agent for the 'SuperBot v2.1.1' automated MT5 trading bot.
Knowledge:
- Fully automated MT5 trading software (Python based, Windows).
- Trades EURUSD and XAUUSD.
- Uses 33+ technical concepts. No hidden AI fees.
- Safety: Anti-Blowup Protection (lot capping, daily drawdown limits).
- Pricing: 1M=$100, 3M=$200, 6M=$300, 1Y=$500.
- Payment: USDT on TRC20 network.
Rules:
1. Reply in Hindi (Hinglish) or English based on user's language.
2. Be fast and persuasive.
3. If they ask how to buy: Tell them to select a plan below, pay via TRC20, and send the screenshot.
4. Keep answers short and crisp.
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
        markup.add(InlineKeyboardButton("💳 Payment Details", callback_data="payment_info"))
        
        bot.send_message(
            chat_id, 
            f"👋 <b>Welcome!</b>\n\nAapne <b>{plan_name}</b> select kiya hai.\n\n"
            f"Kripya payment karein aur <b>Screenshot</b> bhejein.\n"
            f"Ya koi bhi sawal poochhein, main AI hoon!",
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
            "👋 <b>Hello! Main SuperBot ka AI Assistant hoon.</b>\n\n"
            "Ye ek fully automated MT5 bot hai jo Gold & Euro trade karta hai.\n\n"
            "<b>Plans:</b>\n1M - $100\n3M - $200\n6M - $300\n1Y - $500\n\n"
            "Neeche se plan select karein. Ya koi bhi sawal poochhein, main turant jawab dunga!", 
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
            f"💳 <b>Payment Details (USDT TRC20):</b>\n\n"
            f"🪙 Coin: <b>USDT</b>\n🌐 Network: <b>TRC20</b>\n"
            f"👛 Address:\n<code>{TRC20_WALLET}</code>\n\n"
            f"⚠️ Sirf TRC20 par payment karein.\nPayment ke baad <b>Screenshot</b> bhejein!",
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
                    f"1. Open SuperBot software on your PC.\n"
                    f"2. Enter this key when prompted.\n"
                    f"3. Bot will activate and start trading!\n\n"
                    f"Agar koi dikkat aaye, toh yahin message karein.",
                    parse_mode="HTML"
                )
                bot.reply_to(message, f"✅ Key successfully sent to User ID: {user_chat_id}!")
            except Exception as e:
                bot.reply_to(message, f"❌ Error sending to user: {e}")
            
            del admin_msg_map[message.reply_to_message.message_id]
            if user_chat_id in user_plan: del user_plan[user_chat_id]
        else:
            bot.reply_to(message, "⚠️ User ID not found. Please make sure you are REPLYING to the bot's alert message.")

# ═══════════════════════════════════════════════════════
# 🤖 AI CHAT HANDLER (Fixed Model)
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
        # 🔥 YAHAN NAYA MODEL USE KIYA HAI 🔥
        response = ai_client.chat.completions.create(
            model="openai/gpt-oss-120b", 
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": message.text}
            ],
            temperature=0.6, max_tokens=300
        )
        bot.reply_to(message, response.choices[0].message.content)
    except Exception as e:
        print(f"AI Error: {e}")
        # Fallback to llama-3.1-8b-instant if the new model fails
        try:
            response = ai_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": message.text}
                ],
                temperature=0.6, max_tokens=300
            )
            bot.reply_to(message, response.choices[0].message.content)
        except Exception as e2:
            bot.reply_to(message, f"⚠️ AI Error: {str(e2)[:50]}... Please check Render logs.")

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
