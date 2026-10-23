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
user_states = {}       
user_plans = {}        
pending_payments = {}  
active_keys = {}       
admin_msg_map = {}     # 🆕 Tracks Admin's messages to map replies back to users

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

def get_admin_main_menu():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("⏳ Pending Payments", callback_data="adm_pending"),
        InlineKeyboardButton("👥 User Database", callback_data="adm_users"),
        InlineKeyboardButton("📢 Broadcast Message", callback_data="adm_broadcast"),
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
# 🚀 START COMMAND
# ═══════════════════════════════════════════════════════
@bot.message_handler(commands=['start', 'admin'])
def send_welcome(message):
    chat_id = message.chat.id
    if chat_id == ADMIN_ID:
        user_states[chat_id] = 'admin_main'
        bot.send_message(chat_id, "👑 <b>ULTRA ADMIN DASHBOARD</b>\n\nWelcome back, Boss!", reply_markup=get_admin_main_menu(), parse_mode="HTML")
        return

    user_states[chat_id] = 'cust_main'
    bot.send_message(chat_id, "👋 <b>Welcome to SuperBot!</b>\n\nNeeche diye gaye dashboard se apna kaam karein:", reply_markup=get_customer_main_menu(chat_id), parse_mode="HTML")

# ═══════════════════════════════════════════════════════
# 🔘 CALLBACK HANDLER (Buttons)
# ═══════════════════════════════════════════════════════
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    chat_id = call.message.chat.id
    data = call.data

    # --- CUSTOMER LOGIC ---
    if data == "cust_main":
        user_states[chat_id] = 'cust_main'
        bot.edit_message_text("👋 <b>Customer Dashboard</b>", chat_id, call.message.message_id, reply_markup=get_customer_main_menu(chat_id), parse_mode="HTML")
    elif data == "cust_buy":
        user_states[chat_id] = 'cust_buy'
        bot.edit_message_text("💳 <b>Select a Plan:</b>", chat_id, call.message.message_id, reply_markup=get_customer_plans_menu(), parse_mode="HTML")
    elif data == "cust_status":
        if chat_id in active_keys: bot.answer_callback_query(call.id, "✅ Your subscription is active!", show_alert=True)
        else: bot.answer_callback_query(call.id, "❌ No active subscription.", show_alert=True)
    elif data == "cust_ai":
        user_states[chat_id] = 'cust_ai'
        bot.edit_message_text("🤖 <b>AI Support Chat</b>\n\nAap apna sawal type karein.", chat_id, call.message.message_id, reply_markup=get_ai_exit_menu(), parse_mode="HTML")
    elif data == "cust_contact":
        user_states[chat_id] = 'cust_contact'
        bot.edit_message_text("📞 <b>Admin Chat</b>\n\nApna message type karein.", chat_id, call.message.message_id, reply_markup=get_admin_chat_exit_menu(), parse_mode="HTML")
    elif data.startswith("buy_"):
        amount = data.split("_")[1]
        plan_name = f"{amount} Plan (${amount})"
        user_plans[chat_id] = plan_name
        user_states[chat_id] = 'cust_pay'
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Back", callback_data="cust_buy"))
        bot.edit_message_text(f"✅ <b>Aapne {plan_name} select kiya hai.</b>\n\n💳 <b>Payment (USDT TRC20):</b>\n<code>{TRC20_WALLET}</code>\n\nPayment ke baad <b>Screenshot</b> bhejein.", chat_id, call.message.message_id, reply_markup=markup, parse_mode="HTML")

    # --- ADMIN LOGIC ---
    elif data == "adm_main":
        user_states[chat_id] = 'admin_main'
        bot.edit_message_text("👑 <b>Admin Panel</b>", chat_id, call.message.message_id, reply_markup=get_admin_main_menu(), parse_mode="HTML")
    elif data == "adm_pending":
        if not pending_payments: bot.answer_callback_query(call.id, "✅ No pending payments.", show_alert=True)
        else:
            bot.send_message(chat_id, "⏳ <b>Pending Payments:</b>", parse_mode="HTML")
            for p_id, p_data in pending_payments.items():
                markup = get_payment_action_menu(p_id)
                bot.send_photo(chat_id, p_data['photo_id'], caption=f"👤 User ID: <code>{p_data['user_id']}</code>\n📦 Plan: {p_data['plan']}", reply_markup=markup, parse_mode="HTML")
    elif data == "adm_users":
        bot.answer_callback_query(call.id, f"Total active users: {len(active_keys)}", show_alert=True)
    elif data == "adm_broadcast":
        user_states[chat_id] = 'admin_broadcast'
        bot.send_message(chat_id, "📢 <b>Broadcast Mode</b>\n\nType message to send to ALL users. (Type /cancel to stop).", parse_mode="HTML")
    
    # Admin Key Approval
    elif data.startswith("adm_approve_"):
        p_id = data.split("_")[2]
        if p_id in pending_payments:
            user_id = pending_payments[p_id]['user_id']
            user_states[chat_id] = f'admin_sending_key_{user_id}'
            bot.send_message(chat_id, f"🔑 <b>Send the License Key for User {user_id}.</b>\n\nPlease type the key now:", parse_mode="HTML")
            bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None)

    elif data.startswith("adm_reject_"):
        p_id = data.split("_")[2]
        if p_id in pending_payments:
            user_id = pending_payments[p_id]['user_id']
            bot.send_message(user_id, "❌ <b>Payment Rejected.</b>\n\nAdmin could not verify your payment.", parse_mode="HTML")
            bot.send_message(chat_id, f"✅ Rejected payment for User {user_id}.")
            del pending_payments[p_id]
            bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None)

    # Admin Reply via Button
    elif data.startswith("reply_"):
        if chat_id != ADMIN_ID: return
        user_id = int(data.split("_")[1])
        user_states[ADMIN_ID] = f"admin_replying_{user_id}"
        bot.send_message(ADMIN_ID, f"✍️ <b>Type your reply for User {user_id}:</b>\n(Type /cancel to stop)")

# ═══════════════════════════════════════════════════════
# 📩 MESSAGE HANDLERS
# ═══════════════════════════════════════════════════════
@bot.message_handler(content_types=['text', 'photo'])
def handle_messages(message):
    chat_id = message.chat.id
    state = user_states.get(chat_id, 'cust_main')
    text = message.text or ""

    # ═══════════ 🆕 ADMIN DIRECT SWIPE REPLY ═══════════
    if chat_id == ADMIN_ID and message.reply_to_message and text:
        target_user = admin_msg_map.get(message.reply_to_message.message_id)
        if target_user:
            if text.upper().startswith("OK "): # Key via swipe reply
                key = text[3:].strip()
                active_keys[target_user] = key
                bot.send_message(target_user, f"🎉 <b>Payment Verified!</b>\n\n🔑 <b>Your Key:</b> <code>{key}</code>", parse_mode="HTML")
                bot.reply_to(message, f"✅ Key sent to User {target_user}.")
            else: # Normal chat reply via swipe
                bot.send_message(target_user, f"👨‍💻 <b>Admin:</b> {text}", parse_mode="HTML")
                bot.reply_to(message, "✅ Reply sent to user!")
            return

    if text == "/cancel" and chat_id == ADMIN_ID:
        user_states[chat_id] = 'admin_main'
        bot.send_message(chat_id, "❌ Action cancelled.", reply_markup=get_admin_main_menu())
        return

    # --- ADMIN LOGIC ---
    if state == 'admin_broadcast' and text:
        success = 0
        for user in active_keys:
            try: bot.send_message(user, f"📢 <b>ADMIN:</b>\n\n{text}", parse_mode="HTML"); success += 1; time.sleep(0.1)
            except: pass
        user_states[chat_id] = 'admin_main'
        bot.send_message(chat_id, f"✅ Broadcast sent to {success} users.", reply_markup=get_admin_main_menu())
        return

    if state.startswith('admin_sending_key_') and text:
        target_user = int(state.split('_')[3])
        active_keys[target_user] = text
        try:
            bot.send_message(target_user, f"🎉 <b>Payment Verified!</b>\n\n🔑 <b>Your Key:</b> <code>{text}</code>", parse_mode="HTML")
            bot.send_message(chat_id, f"✅ Key sent to User {target_user}.", reply_markup=get_admin_main_menu())
            for p_id, p_data in list(pending_payments.items()):
                if p_data['user_id'] == target_user: del pending_payments[p_id]
        except: bot.send_message(chat_id, "❌ Failed to send key.")
        user_states[chat_id] = 'admin_main'
        return

    if state.startswith('admin_replying_') and text:
        target_user = int(state.split('_')[2])
        bot.send_message(target_user, f"👨‍💻 <b>Admin:</b> {text}", parse_mode="HTML")
        bot.send_message(chat_id, "✅ Reply sent!", reply_markup=get_admin_main_menu())
        user_states[chat_id] = 'admin_main'
        return

    # --- CUSTOMER LOGIC ---
    if message.content_type == 'photo' and state == 'cust_pay':
        plan = user_plans.get(chat_id, "Unknown Plan")
        photo_id = message.photo[-1].file_id
        bot.reply_to(message, "⏳ <b>Proof Received!</b>\n\nAdmin is verifying.", parse_mode="HTML")
        
        p_id = str(int(time.time()))
        pending_payments[p_id] = {'user_id': chat_id, 'plan': plan, 'photo_id': photo_id}
        
        markup = get_payment_action_menu(p_id)
        msg = bot.send_photo(ADMIN_ID, photo_id, caption=f"🚨 <b>NEW PAYMENT PROOF</b>\n\n👤 User: @{message.from_user.username or 'None'}\n🆔 ID: <code>{chat_id}</code>\n📦 Plan: {plan}", reply_markup=markup, parse_mode="HTML")
        
        # Save map for direct swipe reply
        admin_msg_map[msg.message_id] = chat_id 
        return

    if state == 'cust_ai' and text:
        if not ai_client: return
        bot.send_chat_action(chat_id, 'typing')
        try:
            res = ai_client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": text}])
            bot.reply_to(message, res.choices[0].message.content, reply_markup=get_ai_exit_menu())
        except: bot.reply_to(message, "⚠️ AI busy.")
        return

    if state == 'cust_contact':
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("↩️ Reply to User", callback_data=f"reply_{chat_id}"))
        msg = bot.send_message(ADMIN_ID, f"👨‍💻 <b>Message from User</b> <code>{chat_id}</code>:\n\n{text}", reply_markup=markup, parse_mode="HTML")
        
        # Save map for direct swipe reply
        admin_msg_map[msg.message_id] = chat_id 
        
        bot.reply_to(message, "✅ Message sent to Admin.", reply_markup=get_admin_chat_exit_menu())
        return

    if chat_id != ADMIN_ID:
        bot.reply_to(message, "⚠️ Kripya menu ka use karein.", reply_markup=get_customer_main_menu(chat_id))

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
