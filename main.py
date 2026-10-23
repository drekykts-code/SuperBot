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
except Exception:
    ai_client = None

app = Flask(__name__)

try:
    bot.remove_webhook()
except Exception:
    pass

user_plan = {}
admin_msg_map = {} # Forwarded message ID -> User Chat ID
user_state = {}    # 'main', 'ai_chat', 'admin_chat'

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
# ID CHECK COMMAND
# ═══════════════════════════════════════════════════════
@bot.message_handler(commands=['id'])
def send_id(message):
    chat_id = message.chat.id
    bot.reply_to(message, f"🆔 Aapki Telegram ID: <code>{chat_id}</code>\n\nMake sure Render ke Environment me <code>ADMIN_ID</code> me yahi number daala ho.", parse_mode="HTML")

# ═══════════════════════════════════════════════════════
# MENU BUILDERS
# ═══════════════════════════════════════════════════════
def get_main_menu():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("💳 Buy Plan / Pricing", callback_data="menu_buy"),
        InlineKeyboardButton("🤖 AI Support Chat", callback_data="menu_ai"),
        InlineKeyboardButton("📞 Chat with Admin", callback_data="menu_contact")
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

def get_admin_chat_menu():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("❌ Exit Admin Chat", callback_data="menu_main"))
    return markup

# ═══════════════════════════════════════════════════════
# START & MENU HANDLERS
# ═══════════════════════════════════════════════════════
@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    user_state[chat_id] = 'main'
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
            text="🤖 <b>AI Support Activated!</b>\n\nAap ab yahan apne sawal type karke poochh sakte hain. Main aapki puri madad karunga.",
            reply_markup=get_ai_menu(), parse_mode="HTML"
        )

    elif call.data == "menu_contact":
        user_state[chat_id] = 'admin_chat'
        bot.edit_message_text(
            chat_id=chat_id, message_id=call.message.message_id,
            text="📞 <b>Admin Chat Activated!</b>\n\nAap ab apna message type karke bhej sakte hain. Admin aapko yahan reply karenge.",
            reply_markup=get_admin_chat_menu(), parse_mode="HTML"
        )

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
# USER MESSAGE HANDLER (Text, Photo, Doc)
# ═══════════════════════════════════════════════════════
@bot.message_handler(func=lambda message: message.chat.id != ADMIN_ID, content_types=['text', 'photo', 'document'])
def handle_user_messages(message):
    chat_id = message.chat.id
    state = user_state.get(chat_id, 'main')

    # 1. Agar user Admin Chat me hai
    if state == 'admin_chat':
        # Forward to Admin
        if ADMIN_ID != 0:
            try:
                forwarded = bot.forward_message(ADMIN_ID, chat_id, message.message_id)
                admin_msg_map[forwarded.message_id] = chat_id
                bot.reply_to(message, "✅ <b>Message sent to Admin!</b>\nAdmin jaldi reply karenge.", parse_mode="HTML")
            except Exception as e:
                bot.reply_to(message, "⚠️ Admin ko message nahi bhej paye. Thodi der baad try karein.")
        return

    # 2. Agar user AI Chat me hai
    if state == 'ai_chat' and message.text:
        if not ai_client or not GROQ_API_KEY:
            bot.reply_to(message, "⚠️ AI service is down.")
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
            bot.reply_to(message, response.choices[0].message.content, reply_markup=get_ai_menu())
        except Exception as e:
            print(f"AI Error: {e}")
            bot.reply_to(message, "⚠️ AI is busy. Please try again.")
        return

    # 3. Agar user payment proof bhej raha hai (Plan selected)
    if message.content_type in ['photo', 'document'] and chat_id in user_plan:
        plan_name = user_plan[chat_id]
        username = message.from_user.username or "No Username"
        
        bot.reply_to(message, "⏳ <b>Proof Received!</b>\n\nAdmin verify kar raha hai.", parse_mode="HTML")
        
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
        return

    # 4. Agar normal chat me hai aur bina state ke kuch bheja hai
    bot.reply_to(
        message, 
        "⚠️ Kripya menu ka use karein.",
        reply_markup=get_main_menu(), parse_mode="HTML"
    )

# ═══════════════════════════════════════════════════════
# 👑 ADMIN HANDLER (Replying to Any Message)
# ═══════════════════════════════════════════════════════
@bot.message_handler(func=lambda message: message.chat.id == ADMIN_ID and message.reply_to_message, content_types=['text', 'photo', 'document'])
def handle_admin_reply(message):
    text = message.text or ""
    user_chat_id = admin_msg_map.get(message.reply_to_message.message_id)

    if not user_chat_id:
        bot.reply_to(message, "⚠️ <b>User ID not found.</b>\nAapne jis message ko reply kiya hai, wo bot ka forwarded message nahi hai.")
        return

    # 1. Agar OK KEY hai (Payment Verification)
    if text.upper().startswith("OK "):
        license_key = text[3:].strip()
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
            if user_chat_id in user_plan: del user_plan[user_chat_id]
        except Exception as e:
            bot.reply_to(message, f"❌ Error: {e}")
        return

    # 2. Agar normal Text reply hai (Two-Way Chat)
    if text:
        try:
            bot.send_message(user_chat_id, f"👨‍💻 <b>Admin:</b> {text}", parse_mode="HTML")
            bot.reply_to(message, "✅ Message sent to user!")
        except Exception as e:
            bot.reply_to(message, f"❌ Error: {e}")
            
    # 3. Agar Admin photo bhejta hai
    elif message.photo:
        try:
            bot.send_photo(user_chat_id, message.photo[-1].file_id, caption=f"👨‍💻 <b>Admin:</b> {message.caption or ''}", parse_mode="HTML")
            bot.reply_to(message, "✅ Photo sent to user!")
        except Exception as e:
            bot.reply_to(message, f"❌ Error: {e}")

@app.route('/')
def home(): return "SuperBot Server is Alive!"

def run_bot():
    print("🚀 Bot is starting...")
    while True:
        try:
            bot.infinity_polling(skip_pending=True, timeout=20, long_polling_timeout=10, none_stop=True)
        except Exception:
            time.sleep(5)

if __name__ == '__main__':
    threading.Thread(target=run_bot, daemon=True).start()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
