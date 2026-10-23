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

# ═══════════════════════════════════════════════════════
# DATABASE (In-Memory Storage)
# ═══════════════════════════════════════════════════════
user_states = {}       # Tracks where the user is in the bot
user_plans = {}        # Tracks selected plan
pending_payments = {}  # Admin msg ID -> {user_id, plan, photo_id}
active_keys = {}       # user_id -> license_key
broadcast_mode = {}    # Admin ID -> True/False for broadcasting

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
# 🎨 UI / MENUS
# ═══════════════════════════════════════════════════════

# --- CUSTOMER MENUS ---
def get_customer_main_menu(user_id):
    markup = InlineKeyboardMarkup(row_width=2)
    sub_status = "✅ Active" if user_id in active_keys else "❌ None"
    
    markup.add(
        InlineKeyboardButton("💳 Buy Plan", callback_data="cust_buy"),
        InlineKeyboardButton(f"📊 My Sub: {sub_status}", callback_data="cust_status")
    )
    markup.add(
        InlineKeyboardButton("🤖 AI Support Chat", callback_data="cust_ai"),
        InlineKeyboardButton("📞 Chat with Admin", callback_data="cust_contact")
    )
    return markup

def get_customer_plans_menu():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("1M ($100)", callback_data="buy_100"),
        InlineKeyboardButton("3M ($200)", callback_data="buy_200"),
        InlineKeyboardButton("6M ($300) 🔥", callback_data="buy_300"),
        InlineKeyboardButton("1Y ($500) ⭐", callback_data="buy_500"),
        InlineKeyboardButton("⬅️ Back", callback_data="cust_main")
    )
    return markup

def get_ai_exit_menu():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("❌ Exit AI Chat", callback_data="cust_main"))
    return markup

def get_admin_chat_exit_menu():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("❌ Exit Admin Chat", callback_data="cust_main"))
    return markup

# --- ADMIN MENUS ---
def get_admin_main_menu():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("⏳ Pending Payments", callback_data="adm_pending"),
        InlineKeyboardButton("👥 User Database", callback_data="adm_users"),
        InlineKeyboardButton("📢 Broadcast Message", callback_data="adm_broadcast"),
        InlineKeyboardButton("🧠 AI Tester", callback_data="adm_aitest"),
        InlineKeyboardButton("👤 Switch to Customer View", callback_data="cust_main")
    )
    return markup

def get_payment_action_menu(payment_id):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("✅ Approve (Send Key)", callback_data=f"adm_approve_{payment_id}"),
        InlineKeyboardButton("❌ Reject", callback_data=f"adm_reject_{payment_id}")
    )
    return markup

# ═══════════════════════════════════════════════════════
# 🚀 START COMMAND (Separates Admin & Customer)
# ═══════════════════════════════════════════════════════
@bot.message_handler(commands=['start', 'admin'])
def send_welcome(message):
    chat_id = message.chat.id
    
    # --- ADMIN DASHBOARD ---
    if chat_id == ADMIN_ID:
        user_states[chat_id] = 'admin_main'
        bot.send_message(
            chat_id, 
            "👑 <b>ULTRA ADMIN DASHBOARD</b>\n\n"
            "Welcome back, Boss! Here is your control panel:\n"
            f"📊 Total Users: {len(active_keys)}\n"
            f"⏳ Pending Payments: {len(pending_payments)}", 
            reply_markup=get_admin_main_menu(), parse_mode="HTML"
        )
        return

    # --- CUSTOMER DASHBOARD ---
    user_states[chat_id] = 'cust_main'
    bot.send_message(
        chat_id, 
        "👋 <b>Welcome to SuperBot!</b>\n\n"
        "Ye ek fully automated MT5 trading bot hai jo Gold & Euro trade karta hai.\n"
        "Neeche diye gaye dashboard se apna kaam karein:", 
        reply_markup=get_customer_main_menu(chat_id), parse_mode="HTML"
    )

# ═══════════════════════════════════════════════════════
# 🔘 CALLBACK HANDLER (All Buttons)
# ═══════════════════════════════════════════════════════
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    chat_id = call.message.chat.id
    data = call.data

    # ══════════════ CUSTOMER LOGIC ══════════════
    if data == "cust_main":
        user_states[chat_id] = 'cust_main'
        bot.edit_message_text("👋 <b>Customer Dashboard</b>\n\nAap kya karna chahte hain?", 
                              chat_id, call.message.message_id, reply_markup=get_customer_main_menu(chat_id), parse_mode="HTML")

    elif data == "cust_buy":
        user_states[chat_id] = 'cust_buy'
        bot.edit_message_text("💳 <b>Select a Plan:</b>", chat_id, call.message.message_id, reply_markup=get_customer_plans_menu(), parse_mode="HTML")

    elif data == "cust_status":
        if chat_id in active_keys:
            bot.answer_callback_query(call.id, "✅ Your subscription is active!", show_alert=True)
        else:
            bot.answer_callback_query(call.id, "❌ No active subscription. Please buy a plan.", show_alert=True)

    elif data == "cust_ai":
        user_states[chat_id] = 'cust_ai'
        bot.edit_message_text("🤖 <b>AI Support Chat</b>\n\nAap apna sawal type karein, main turant jawab dunga.",
                              chat_id, call.message.message_id, reply_markup=get_ai_exit_menu(), parse_mode="HTML")

    elif data == "cust_contact":
        user_states[chat_id] = 'cust_contact'
        bot.edit_message_text("📞 <b>Admin Chat</b>\n\nApna message type karein, Admin jaldi reply karenge.",
                              chat_id, call.message.message_id, reply_markup=get_admin_chat_exit_menu(), parse_mode="HTML")

    elif data.startswith("buy_"):
        amount = data.split("_")[1]
        plan_name = f"{amount} Plan (${amount})"
        user_plans[chat_id] = plan_name
        user_states[chat_id] = 'cust_pay'
        
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("⬅️ Back", callback_data="cust_buy"))
        bot.edit_message_text(
            f"✅ <b>Aapne {plan_name} select kiya hai.</b>\n\n"
            f"💳 <b>Payment (USDT TRC20):</b>\n<code>{TRC20_WALLET}</code>\n\n"
            f"Payment ke baad <b>Screenshot</b> yahan bhejein.",
            chat_id, call.message.message_id, reply_markup=markup, parse_mode="HTML"
        )

    # ══════════════ ADMIN LOGIC ══════════════
    elif data == "adm_main":
        user_states[chat_id] = 'admin_main'
        bot.edit_message_text("👑 <b>Admin Panel</b>", chat_id, call.message.message_id, reply_markup=get_admin_main_menu(), parse_mode="HTML")

    elif data == "adm_pending":
        if not pending_payments:
            bot.answer_callback_query(call.id, "✅ No pending payments right now.", show_alert=True)
        else:
            bot.send_message(chat_id, "⏳ <b>Pending Payments:</b>\nCheck the forwarded photos below and click Approve/Reject.", parse_mode="HTML")
            for p_id, p_data in pending_payments.items():
                markup = get_payment_action_menu(p_id)
                bot.send_photo(chat_id, p_data['photo_id'], caption=f"👤 User ID: <code>{p_data['user_id']}</code>\n📦 Plan: {p_data['plan']}", reply_markup=markup, parse_mode="HTML")

    elif data == "adm_users":
        bot.answer_callback_query(call.id, f"Total active users: {len(active_keys)}", show_alert=True)

    elif data == "adm_broadcast":
        user_states[chat_id] = 'admin_broadcast'
        bot.send_message(chat_id, "📢 <b>Broadcast Mode</b>\n\nType the message you want to send to ALL active users. (Type /cancel to stop).", parse_mode="HTML")

    elif data == "adm_aitest":
        user_states[chat_id] = 'admin_aitest'
        bot.send_message(chat_id, "🧠 <b>AI Tester</b>\n\nType anything to test the AI. (Type /cancel to stop).", reply_markup=get_ai_exit_menu(), parse_mode="HTML")

    elif data.startswith("adm_approve_"):
        p_id = data.split("_")[2]
        if p_id in pending_payments:
            user_id = pending_payments[p_id]['user_id']
            # Ask Admin for the Key
            user_states[chat_id] = f'admin_sending_key_{user_id}'
            bot.send_message(chat_id, f"🔑 <b>Send the License Key for User {user_id}.</b>\n\nPlease type the key now (e.g., SB-12345):", parse_mode="HTML")
            bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None) # Remove buttons

    elif data.startswith("adm_reject_"):
        p_id = data.split("_")[2]
        if p_id in pending_payments:
            user_id = pending_payments[p_id]['user_id']
            bot.send_message(user_id, "❌ <b>Payment Rejected.</b>\n\nAdmin could not verify your payment. Please contact support.", parse_mode="HTML")
            bot.send_message(chat_id, f"✅ Rejected payment for User {user_id}.")
            del pending_payments[p_id]
            bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None)

# ═══════════════════════════════════════════════════════
# 📩 MESSAGE HANDLERS (Text & Photos)
# ═══════════════════════════════════════════════════════
@bot.message_handler(content_types=['text', 'photo'])
def handle_messages(message):
    chat_id = message.chat.id
    state = user_states.get(chat_id, 'cust_main')
    text = message.text or ""

    # --- HANDLE /cancel for admin ---
    if text == "/cancel" and chat_id == ADMIN_ID:
        user_states[chat_id] = 'admin_main'
        bot.send_message(chat_id, "❌ Action cancelled.", reply_markup=get_admin_main_menu())
        return

    # --- ADMIN BROADCAST ---
    if state == 'admin_broadcast' and text:
        success = 0
        for user in active_keys:
            try:
                bot.send_message(user, f"📢 <b>ADMIN ANNOUNCEMENT:</b>\n\n{text}", parse_mode="HTML")
                success += 1
                time.sleep(0.1)
            except: pass
        user_states[chat_id] = 'admin_main'
        bot.send_message(chat_id, f"✅ Broadcast sent to {success} users.", reply_markup=get_admin_main_menu())
        return

    # --- ADMIN AI TEST ---
    if state == 'admin_aitest' and text:
        if not ai_client: return
        bot.send_chat_action(chat_id, 'typing')
        res = ai_client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": text}])
        bot.reply_to(message, f"🧠 <b>AI:</b> {res.choices[0].message.content}", reply_markup=get_ai_exit_menu(), parse_mode="HTML")
        return

    # --- ADMIN SENDING KEY ---
    if state.startswith('admin_sending_key_') and text:
        target_user = int(state.split('_')[3])
        active_keys[target_user] = text
        try:
            bot.send_message(target_user, f"🎉 <b>Payment Verified!</b>\n\n🔑 <b>Your Key:</b> <code>{text}</code>\n\nUse this to activate your bot.", parse_mode="HTML")
            bot.send_message(chat_id, f"✅ Key sent to User {target_user}.", reply_markup=get_admin_main_menu())
            # Clean pending
            for p_id, p_data in list(pending_payments.items()):
                if p_data['user_id'] == target_user: del pending_payments[p_id]
        except: bot.send_message(chat_id, "❌ Failed to send key to user.")
        user_states[chat_id] = 'admin_main'
        return

    # --- CUSTOMER PAYMENT PROOF (PHOTO) ---
    if message.content_type == 'photo' and state == 'cust_pay':
        plan = user_plans.get(chat_id, "Unknown Plan")
        photo_id = message.photo[-1].file_id
        
        bot.reply_to(message, "⏳ <b>Proof Received!</b>\n\nAdmin is verifying your payment.", parse_mode="HTML")
        
        # Forward to Admin
        p_id = str(int(time.time()))
        pending_payments[p_id] = {'user_id': chat_id, 'plan': plan, 'photo_id': photo_id}
        
        markup = get_payment_action_menu(p_id)
        bot.send_photo(ADMIN_ID, photo_id, caption=f"🚨 <b>NEW PAYMENT PROOF</b>\n\n👤 User: @{message.from_user.username or 'None'}\n🆔 ID: <code>{chat_id}</code>\n📦 Plan: {plan}", reply_markup=markup, parse_mode="HTML")
        return

    # --- CUSTOMER AI CHAT ---
    if state == 'cust_ai' and text:
        if not ai_client: return
        bot.send_chat_action(chat_id, 'typing')
        try:
            res = ai_client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": text}])
            bot.reply_to(message, res.choices[0].message.content, reply_markup=get_ai_exit_menu())
        except: bot.reply_to(message, "⚠️ AI busy.")
        return

    # --- CUSTOMER ADMIN CHAT ---
    if state == 'cust_contact':
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("↩️ Reply to User", callback_data=f"reply_{chat_id}"))
        bot.send_message(ADMIN_ID, f"👨‍💻 <b>Message from User</b> <code>{chat_id}</code>:\n\n{text}", reply_markup=markup, parse_mode="HTML")
        bot.reply_to(message, "✅ Message sent to Admin. Wait for reply.", reply_markup=get_admin_chat_exit_menu())
        return

    # --- DEFAULT MENU ---
    if chat_id != ADMIN_ID:
        bot.reply_to(message, "⚠️ Kripya menu ka use karein.", reply_markup=get_customer_main_menu(chat_id))

# --- ADMIN DIRECT REPLY HANDLER (For Two-Way Chat) ---
@bot.callback_query_handler(func=lambda call: call.data.startswith("reply_"))
def handle_admin_reply_button(call):
    if call.message.chat.id != ADMIN_ID: return
    user_id = int(call.data.split("_")[1])
    user_states[ADMIN_ID] = f"admin_replying_{user_id}"
    bot.send_message(ADMIN_ID, f"✍️ <b>Type your reply for User {user_id}:</b>\n(Type /cancel to stop)")

@bot.message_handler(func=lambda msg: msg.chat.id == ADMIN_ID and user_states.get(ADMIN_ID, "").startswith("admin_replying_") and msg.text)
def handle_admin_text_reply(message):
    user_id = int(user_states[ADMIN_ID].split("_")[2])
    bot.send_message(user_id, f"👨‍💻 <b>Admin:</b> {message.text}", parse_mode="HTML")
    bot.send_message(ADMIN_ID, "✅ Reply sent!", reply_markup=get_admin_main_menu())
    user_states[ADMIN_ID] = 'admin_main'

@app.route('/')
def home(): return "SuperBot Ultra Server is Alive!"

def run_bot():
    print("🚀 Ultra Bot is starting...")
    while True:
        try:
            bot.infinity_polling(skip_pending=True, timeout=20, long_polling_timeout=10, none_stop=True)
        except Exception:
            time.sleep(5)

if __name__ == '__main__':
    threading.Thread(target=run_bot, daemon=True).start()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
