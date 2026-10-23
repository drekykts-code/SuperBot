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
ADMIN_ID = int(os.getenv("ADMIN_ID", "123456789")) 
TRC20_WALLET = os.getenv("TRC20_WALLET", "T_YOUR_DEFAULT_ADDRESS_HERE")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "YOUR_GROQ_KEY_HERE")

bot = telebot.TeleBot(BOT_TOKEN)

try:
    # Groq AI (Fastest & Smartest)
    ai_client = Groq(api_key=GROQ_API_KEY)
except Exception as e:
    ai_client = None
    print(f"AI Init Error: {e}")

app = Flask(__name__)

try:
    bot.remove_webhook()
    print("✅ Webhook removed successfully.")
except Exception:
    pass

# Storage
user_plan = {}
admin_msg_map = {}
active_users = set() # Jinko key mil chuki hai

PLAN_NAMES = {
    "plan_100": "1 Month ($100)",
    "plan_200": "3 Months ($200)",
    "plan_300": "6 Months ($300)",
    "plan_500": "1 Year ($500)"
}

# ═══════════════════════════════════════════════════════
# 🧠 AI BRAIN (SUPER SMART PROMPT)
# ═══════════════════════════════════════════════════════
SYSTEM_PROMPT = """
You are 'SuperBot AI', an ultra-smart, fast, and polite sales agent and tech support for the 'SuperBot v2.1.1' automated MT5 trading bot.

YOUR KNOWLEDGE BASE:
- **What is it?**: A fully automated MetaTrader 5 (MT5) trading software. It runs 24/7 on your PC (Windows).
- **Markets**: Trades EURUSD (Euro) and XAUUSD (Gold) only.
- **Strategy**: Uses 33+ advanced concepts (SMC, Candlestick patterns, EMA, MACD, Fibonacci). It does NOT use paid AI APIs, so zero monthly subscription fees.
- **Safety**: Anti-Blowup Protection (strict lot capping, min SL, daily drawdown limits).
- **Dashboard**: Shows real-time PnL, Strategy Leaderboard, and exact concept used for each trade.
- **Pricing**: 1M=$100, 3M=$200, 6M=$300, 1Y=$500.
- **Payment**: USDT on TRC20 network.
- **Risk**: No bot can guarantee 100% profit. It's a tool with ~55-65% win rate.

RULES:
1. You must understand and reply in BOTH Hindi (Hinglish) and English. Match the user's language.
2. Be extremely fast, helpful, and persuasive like a top salesman.
3. If they ask "how to buy", tell them to select a plan below, pay via TRC20, and send the screenshot.
4. If they ask any unrelated question (e.g., weather, politics), politely say: "Main sirf SuperBot aur trading se judi jaankari de sakta hoon."
5. Keep answers short and crisp. Do not write massive essays.
"""

# ═══════════════════════════════════════════════════════
# HANDLERS
# ═══════════════════════════════════════════════════════
@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    args = message.text.split()

    # Agar website se aaya hai
    if len(args) > 1:
        plan_code = args[1]
        plan_name = PLAN_NAMES.get(plan_code, "Unknown Plan")
        user_plan[chat_id] = plan_name
        
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("💳 Payment Details", callback_data="payment_info"))
        
        bot.send_message(
            chat_id, 
            f"👋 <b>Welcome to SuperBot!</b>\n\nAapne <b>{plan_name}</b> select kiya hai.\n\n"
            f"Kripya payment karein aur <b>Screenshot</b> bhejein.\n"
            f"Koi bhi sawal ho toh yahin poochhein, main AI hoon!",
            reply_markup=markup, parse_mode="HTML"
        )
    else:
        # Agar direct aaya hai
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
            "<b>Plans:</b>\n"
            "1 Month - $100\n"
            "3 Months - $200\n"
            "6 Months - $300\n"
            "1 Year - $500\n\n"
            "Neeche se plan select karein. Ya agar aapke koi sawal hain (Jaise: Kaise kaam karta hai? Safe hai? Payment kaise karein?), toh kripya yahan type karein, main turant jawab dunga!", 
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
            f"⚠️ <b>Note:</b> Sirf TRC20 par payment karein.\n"
            f"Payment ke baad <b>Screenshot</b> yahan bhejein!",
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

@bot.message_handler(content_types=['photo', 'document'])
def handle_proof(message):
    chat_id = message.chat.id
    
    if chat_id not in user_plan:
        bot.reply_to(message, "⚠️ Kripya pehle plan select karein (/start dabayein)!")
        return

    plan_name = user_plan[chat_id]
    username = message.from_user.username or "No Username"
    
    bot.reply_to(message, "⏳ <b>Proof Received!</b>\n\nAdmin verify kar raha hai. Aapko jaldi hi key mil jayegi.", parse_mode="HTML")
    
    # Admin ko alert
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
# 👑 ADMIN HANDLER (Aap sirf yahan OK KEY likhenge)
# ═══════════════════════════════════════════════════════
@bot.message_handler(func=lambda message: message.chat.id == ADMIN_ID and message.reply_to_message, content_types=['text'])
def handle_admin_reply(message):
    text = message.text.strip()
    
    if text.upper().startswith("OK "):
        license_key = text[3:].strip()
        user_chat_id = admin_msg_map.get(message.reply_to_message.message_id)
        
        if user_chat_id:
            try:
                # Customer ko key send karein
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
                active_users.add(user_chat_id)
            except Exception as e:
                bot.reply_to(message, f"❌ Error sending to user: {e}")
            
            del admin_msg_map[message.reply_to_message.message_id]
            if user_chat_id in user_plan: del user_plan[user_chat_id]
        else:
            bot.reply_to(message, "⚠️ User ID not found. Please make sure you are REPLYING (swiping) to the bot's alert message.")
    else:
        bot.reply_to(message, "⚠️ Invalid format. Please reply with: OK YOUR_KEY")

# ═══════════════════════════════════════════════════════
# 🤖 AI CHAT HANDLER (Customer ke saare sawalon ka jawab)
# ═══════════════════════════════════════════════════════
@bot.message_handler(func=lambda message: message.text and not message.text.startswith('/') and message.chat.id != ADMIN_ID)
def handle_ai_chat(message):
    chat_id = message.chat.id
    user_text = message.text

    if not ai_client:
        bot.reply_to(message, "⚠️ AI service temporarily down. Kripya /start dabayein.")
        return

    bot.send_chat_action(chat_id, 'typing')
    try:
        response = ai_client.chat.completions.create(
            model="llama-3.3-70b-versatile", # Sabse fast aur smart model
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_text}
            ],
            temperature=0.6, max_tokens=300
        )
        bot.reply_to(message, response.choices[0].message.content)
    except Exception as e:
        print(f"AI Error: {e}")
        bot.reply_to(message, "⚠️ Sorry, main thoda busy hoon. Kripya /start dabayein.")

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
