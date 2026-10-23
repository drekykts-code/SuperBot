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
except Exception as e:
    ai_client = None

app = Flask(__name__)

try:
    bot.remove_webhook()
except Exception:
    pass

# ═══════════════════════════════════════════════════════
# USER STATE MANAGEMENT
# ═══════════════════════════════════════════════════════
user_plan = {}
admin_msg_map = {}
user_state = {} # 'main' ya 'ai_chat' track karne ke liye

PLAN_NAMES = {
    "plan_100": "1 Month ($100)",
    "plan_200": "3 Months ($200)",
    "plan_300": "6 Months ($300)",
    "plan_500": "1 Year ($500)"
}

SYSTEM_PROMPT = """
You are 'SuperBot AI', a polite and professional sales agent for the 'SuperBot v2.1.1' MT5 trading bot.
Facts: Trades EURUSD/Gold, 33+ strategies, Anti-blowup protection. 
Payment: USDT TRC20 ONLY. (Never mention UPI).
Keep answers short (max 2 sentences). Be helpful.
"""

# ═══════════════════════════════════════════════════════
# MENU BUILDERS
# ═══════════════════════════════════════════════════════
def get_main_menu():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("💳 Buy Plan / Pricing", callback_data="menu_buy"),
        InlineKeyboardButton("🤖 AI Support Chat", callback_data="menu_ai"),
        InlineKeyboardButton("📞 Contact Admin", callback_data="menu_contact")
    )
    return markup

def get_plans_menu():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("1 Month ($100)", callback_data="plan_100"),
        InlineKeyboardButton("3 Months ($200)", callback_data="plan_200"),
        InlineKeyboardButton("6 Months ($300) 🔥", callback_data="plan_300"),
        InlineKeyboardButton("1 Year ($500) ⭐", callback_data="plan_500"),
        InlineKeyboardButton("⬅️ Back to Menu", callback_data="menu_main")
    )
    return markup

def get_ai_menu():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("❌ Exit AI Chat", callback_data="menu_main"))
    return markup

# ═══════════════════════════════════════════════════════
# START & MENU HANDLERS
# ═══════════════════════════════════════════════════════
@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    user_state[chat_id] = 'main' # Default state
    args = message.text.split()

    if len(args) > 1:
        plan_code = args[1]
        plan_name = PLAN_NAMES.get(plan_code, "Unknown Plan")
        user_plan[chat_id] = plan_name
        
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("💳 Payment Details (USDT)", callback_data="payment_info"))
        markup.add(InlineKeyboardButton("⬅️ Main Menu", callback_data="menu_main"))
        
        bot.send_message(
            chat_id, 
            f"👋 <b>Welcome!</b>\n\nAapne <b>{plan_name}</b> select kiya hai.\n\n"
            f"Kripya payment karein aur <b>Screenshot</b> bhejein.",
            reply_markup=markup, parse_mode="HTML"
        )
    else:
        bot.send_message(
            chat_id, 
            "👋 <b>Hello! Main SuperBot ka Assistant hoon.</b>\n\n"
            "Aap kya karna chahte hain? Neeche se option select karein:", 
            reply_markup=get_main_menu(), parse_mode="HTML"
        )

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    chat_id = call.message.chat.id
    
    if call.data == "menu_main":
        user_state[chat_id] = 'main'
        bot.edit_message_text(
            chat_id=chat_id, message_id=call.message.message_id,
            text="👋 <b>Main Menu</b>\n\nAap kya karna chahte hain?",
            reply_markup=get_main_menu(), parse_mode="HTML"
        )

    elif call.data == "menu_buy":
        bot.edit_message_text(
            chat_id=chat_id, message_id=call.message.message_id,
            text="💳 <b>Select a Plan:</b>\n\nNeeche se apna plan select karein:",
            reply_markup=get_plans_menu(), parse_mode="HTML"
        )

    elif call.data == "menu_ai":
        user_state[chat_id] = 'ai_chat'
        bot.edit_message_text(
            chat_id=chat_id, message_id=call.message.message_id,
            text="🤖 <b>AI Support Activated!</b>\n\nAap ab yahan apne sawal type karke poochh sakte hain. Main aapki puri madad karunga.\n\n<i>(Wapas menu me aane ke liye neeche Exit button dabayein)</i>",
            reply_markup=get_ai_menu(), parse_mode="HTML"
        )

    elif call.data == "menu_contact":
        bot.send_message(
            chat_id, 
            f"📞 <b>Contact Admin</b>\n\nAgar aapko koi dikkat aaye, toh aap direct admin se baat kar sakte hain.\nAdmin ID: <code>{ADMIN_ID}</code>",
            parse_mode="HTML"
        )
        bot.answer_callback_query(call.id)

    elif call.data == "payment_info":
        bot.answer_callback_query(call.id, "Details bhej rahe hain...")
        bot.send_message(
            chat_id,
            f"💳 <b>Payment Details (USDT TRC20 ONLY):</b>\n\n"
            f"🪙 Coin: <b>USDT</b>\n🌐 Network: <b>TRC20 (Tron)</b>\n"
            f"👛 Address:\n<code>{TRC20_WALLET}</code>\n\n"
            f"⚠️ <b>Warning:</b> Sirf TRC20 par payment karein.\n\n"
            f"Payment ke baad <b>Screenshot</b> bhejein!",
            parse_mode="HTML"
        )
        
    elif call.data.startswith("plan_"):
        plan_name = PLAN_NAMES.get(call.data, "Unknown")
        user_plan[chat_id] = plan_name
        bot.answer_callback_query(call.id, f"{plan_name} Selected!")
        
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("💳 Payment Details (USDT)", callback_data="payment_info"))
        markup.add(InlineKeyboardButton("⬅️ Main Menu", callback_data="menu_main"))
        
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
        bot.reply_to(message, "⚠️ Kripya pehle 'Buy Plan' me jaakar plan select karein!")
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
                    f"1. Open SuperBot software.\n2. Enter this key.\n3. Bot will start trading!",
                    parse_mode="HTML"
                )
                bot.reply_to(message, f"✅ Key successfully sent to User ID: {user_chat_id}!")
            except Exception as e:
                bot.reply_to(message, f"❌ Error: {e}")
            
            del admin_msg_map[message.reply_to_message.message_id]
            if user_chat_id in user_plan: del user_plan[user_chat_id]

# ═══════════════════════════════════════════════════════
# 🤖 AI CHAT HANDLER (Only works if state is 'ai_chat')
# ═══════════════════════════════════════════════════════
@bot.message_handler(func=lambda message: message.text and not message.text.startswith('/'))
def handle_ai_chat(message):
    chat_id = message.chat.id
    
    # Admin OK command check
    if chat_id == ADMIN_ID and message.reply_to_message and message.text.strip().upper().startswith("OK "):
        return

    # Check state: Agar user AI chat me nahi hai, toh use menu dikhao
    if user_state.get(chat_id) != 'ai_chat':
        bot.reply_to(
            message, 
            "⚠️ AI Chat active nahi hai. Kripya neeche diye gaye menu se <b>'AI Support Chat'</b> par click karein.",
            reply_markup=get_main_menu(), parse_mode="HTML"
        )
        return

    if not ai_client or not GROQ_API_KEY:
        bot.reply_to(message, "⚠️ AI service is down. Admin check karein.")
        return

    bot.send_chat_action(chat_id, 'typing')
    try:
        response = ai_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": message.text}
            ],
            temperature=0.5, max_tokens=150
        )
        # Reply with AI and the Exit button
        bot.reply_to(message, response.choices[0].message.content, reply_markup=get_ai_menu())

    except Exception as e:
        print(f"AI Error: {e}")
        bot.reply_to(message, "⚠️ AI is busy. Please try again.")

@app.route('/')
def home(): return "SuperBot Server is Alive!"

def run_bot():
    print("🚀 Bot is starting...")
    while True:
        try:
            # 🆕 Fixed polling to avoid infinite start loops
            bot.infinity_polling(skip_pending=True, timeout=20, long_polling_timeout=10, none_stop=True)
        except Exception:
            time.sleep(5)

if __name__ == '__main__':
    threading.Thread(target=run_bot, daemon=True).start()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
