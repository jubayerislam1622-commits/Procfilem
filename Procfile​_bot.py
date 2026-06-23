import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import random
import string
import pyotp
import json
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import requests
import io

# ========== GOOGLE SHEETS সেটআপ ==========
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
CREDS = Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
gc = gspread.authorize(CREDS)

SPREADSHEET_ID = '1Ry8n35syUrCWoeWVO5saWqo3v97D3Zr7CifedkEFhfU'

try:
    spreadsheet = gc.open_by_key(SPREADSHEET_ID)
    worksheet = spreadsheet.sheet1
except Exception as e:
    print(f"Google Sheets সংযোগ ব্যর্থ: {e}")
    worksheet = None

# ========== বটের কনফিগারেশন ==========
API_TOKEN = '8848253078:AAHxbEqZFPypogFA6IzO2oeXYxoXMYQvMNk'
ADMIN_CHAT_ID = 7993941422
CHANNEL_USERNAME = 'smartearningdigitalplatform'
CHANNEL_URL = 'https://t.me/smartearningdigitalplatform'

bot = telebot.TeleBot(API_TOKEN)

# ডিফল্ট সেটিংস
settings = {
    'password': 'jubayer@22',
    'work_reward': 3.40,
    'refer_bonus': 2.00,
    'refer_commission': 5.0,
    'tasks': {
        'instagram_2fa': {
            'name': '⚡ ইনস্টাগ্রাম 2FA',
            'reward': 3.40,
            'active': True
        }
    }
}

# ডাটাবেজ
user_balances = {}
user_steps = {}
user_data = {}
withdraw_data = {}
referred_users = {}
admin_sessions = {}
submitted_tasks = {}
approved_count = {}
user_names = {}
completed_task_ids = set()
rejected_task_ids = set()
pending_action = {}  # admin এর জন্য — কোন user এর approve/reject চলছে

def check_channel_member(user_id):
    try:
        member = bot.get_chat_member(f'@{CHANNEL_USERNAME}', user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

def generate_unique_username():
    prefix = "oeaukodw"
    random_str = ''.join(random.choices(string.ascii_lowercase, k=6))
    return f"{prefix}{random_str}"

def save_to_google_sheets(user_id, username, password, secret_key):
    try:
        if worksheet:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            worksheet.append_row([user_id, username, password, secret_key, timestamp])
            return True
    except Exception as e:
        print(f"Google Sheets সেভ ব্যর্থ: {e}")
    return False

def download_sheet_data():
    try:
        if not worksheet:
            return None
        all_records = worksheet.get_all_values()
        if len(all_records) == 0:
            return None
        csv_content = ""
        for row in all_records:
            csv_content += ",".join(str(cell) for cell in row) + "\n"
        return csv_content.encode('utf-8')
    except Exception as e:
        print(f"Sheet ডাউনলোড ব্যর্থ: {e}")
        return None

def get_main_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("💼 কাজ করুন"), KeyboardButton("💰 আমার ব্যালেন্স"))
    markup.add(KeyboardButton("💳 টাকা উত্তোলন করুন"), KeyboardButton("🏆 লিডারবোর্ড দেখুন"))
    markup.add(KeyboardButton("📞 আমাদের সাপোর্ট"), KeyboardButton("👥 আয় করুন Invite দিয়ে"))
    return markup

def get_admin_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("⚙️ সিস্টেম সেটিংস"), KeyboardButton("💼 কাজ ম্যানেজমেন্ট"))
    markup.add(KeyboardButton("🔐 পাসওয়ার্ড পরিবর্তন করুন"), KeyboardButton("💰 রিওয়ার্ড পরিবর্তন করুন"))
    markup.add(KeyboardButton("📊 সিস্টেম স্ট্যাটিস্টিক্স"), KeyboardButton("📥 পেন্ডিং কাজ দেখুন"))
    markup.add(KeyboardButton("📢 সবাইকে বার্তা পাঠান"), KeyboardButton("📊 Sheet ডাউনলোড করুন"))
    markup.add(KeyboardButton("🚪 লগআউট করুন"))
    return markup

# ==================== ADMIN HANDLERS ====================

@bot.message_handler(commands=['admin'])
def admin_login(message):
    chat_id = message.chat.id
    if chat_id == ADMIN_CHAT_ID:
        user_steps[chat_id] = 'ADMIN_LOGIN'
        bot.send_message(chat_id,
            "🔐 *━━━━━━━━━━━━━━━━━━━━━*\n"
            "👑 *ADMIN প্যানেলে স্বাগতম!*\n"
            "*━━━━━━━━━━━━━━━━━━━━━*\n\n"
            "🔑 পাসওয়ার্ড লিখুন:",
            parse_mode="Markdown")
    else:
        bot.send_message(chat_id,
            "🚫 *অ্যাক্সেস নেই!*\n\n"
            "❌ আপনি Admin নন।",
            parse_mode="Markdown")

@bot.message_handler(func=lambda message: user_steps.get(message.chat.id) == 'ADMIN_LOGIN')
def verify_admin_password(message):
    chat_id = message.chat.id
    if message.text.strip() == "admin123":
        admin_sessions[chat_id] = True
        user_steps[chat_id] = None
        bot.send_message(chat_id,
            "✅ *━━━━━━━━━━━━━━━━━━━━━*\n"
            "👑 *Admin লগইন সফল হয়েছে!*\n"
            "*━━━━━━━━━━━━━━━━━━━━━*\n\n"
            "🎛️ নিচের মেনু থেকে কাজ করুন।",
            reply_markup=get_admin_menu(), parse_mode="Markdown")
    else:
        bot.send_message(chat_id, "❌ *ভুল পাসওয়ার্ড! আবার চেষ্টা করুন।*", parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "🚪 লগআউট করুন")
def admin_logout(message):
    chat_id = message.chat.id
    if chat_id in admin_sessions:
        del admin_sessions[chat_id]
    user_steps[chat_id] = None
    bot.send_message(chat_id,
        "👋 *লগআউট সফল!*\n\n"
        "🔒 Admin সেশন বন্ধ হয়েছে।",
        parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "📊 Sheet ডাউনলোড করুন" and admin_sessions.get(message.chat.id))
def download_sheet(message):
    chat_id = message.chat.id
    try:
        csv_data = download_sheet_data()
        if csv_data is None:
            bot.send_message(chat_id, "❌ *কোনো ডাটা পাওয়া যায়নি।*", reply_markup=get_admin_menu(), parse_mode="Markdown")
            return
        filename = f'submitted_ids_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        file_stream = io.BytesIO(csv_data)
        bot.send_document(chat_id, document=file_stream, visible_file_name=filename,
            caption="📊 *সকল সাবমিটেড আইডির তালিকা*\n\n✅ সফলভাবে এক্সপোর্ট করা হয়েছে।")
        if worksheet:
            all_records = worksheet.get_all_values()
            record_count = len(all_records) - 1 if len(all_records) > 1 else 0
        else:
            record_count = 0
        bot.send_message(chat_id,
            f"✅ *ডাউনলোড সফল হয়েছে!*\n\n"
            f"📊 *মোট রেকর্ড:* `{record_count}`",
            reply_markup=get_admin_menu(), parse_mode="Markdown")
    except Exception as e:
        bot.send_message(chat_id, f"❌ *ডাউনলোড ব্যর্থ:* `{str(e)}`", reply_markup=get_admin_menu(), parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "💼 কাজ ম্যানেজমেন্ট" and admin_sessions.get(message.chat.id))
def task_management(message):
    chat_id = message.chat.id
    management_text = "💼 *━━ কাজ ম্যানেজমেন্ট ━━*\n\n"
    for key, task in settings['tasks'].items():
        status = "✅ সক্রিয়" if task['active'] else "❌ নিষ্ক্রিয়"
        management_text += f"▸ {task['name']} — {status}\n"
        management_text += f"  💵 রেট: `৳{task['reward']:.2f}`\n\n"
    management_text += "📝 _কাজ যোগ/সম্পাদনা শীঘ্রই আসছে।_"
    bot.send_message(chat_id, management_text, reply_markup=get_admin_menu(), parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "📥 পেন্ডিং কাজ দেখুন" and admin_sessions.get(message.chat.id))
def view_pending_tasks(message):
    chat_id = message.chat.id
    pending_tasks = {}
    for user_id, tasks_list in submitted_tasks.items():
        for task in tasks_list:
            task_id = f"{user_id}_{task['timestamp']}"
            if task_id not in completed_task_ids and task_id not in rejected_task_ids:
                if user_id not in pending_tasks:
                    pending_tasks[user_id] = []
                pending_tasks[user_id].append(task)

    if not pending_tasks:
        bot.send_message(chat_id, "📭 *কোনো পেন্ডিং কাজ নেই।*", reply_markup=get_admin_menu(), parse_mode="Markdown")
        return

    pending_report = "📊 *━━ পেন্ডিং কাজের তালিকা ━━*\n\n"
    for user_id, tasks_list in pending_tasks.items():
        user_name = user_names.get(user_id, "অজানা")
        pending_report += f"👤 *নাম:* {user_name}\n"
        pending_report += f"🆔 *ID:* `{user_id}`\n"
        pending_report += f"⏳ *পেন্ডিং:* {len(tasks_list)} টি\n"
        pending_report += f"✅ *এপ্রুভ:* {approved_count.get(user_id, 0)} টি\n"
        pending_report += "─────────────────\n"

    bot.send_message(chat_id, pending_report, parse_mode="Markdown")
    user_steps[chat_id] = 'APPROVE_TASKS'
    bot.send_message(chat_id,
        "✏️ *এপ্রুভ করতে নিচের ফরম্যাটে লিখুন:*\n\n"
        "📌 *ফরম্যাট:* `ইউজারআইডি:সংখ্যা`\n"
        "📌 *উদাহরণ:* `7993941422:5`",
        parse_mode="Markdown")

@bot.message_handler(func=lambda message: user_steps.get(message.chat.id) == 'APPROVE_TASKS')
def process_approve_tasks(message):
    chat_id = message.chat.id
    approval_text = message.text.strip()
    pending_tasks = {}
    for user_id, tasks_list in submitted_tasks.items():
        for task in tasks_list:
            task_id = f"{user_id}_{task['timestamp']}"
            if task_id not in completed_task_ids and task_id not in rejected_task_ids:
                if user_id not in pending_tasks:
                    pending_tasks[user_id] = []
                pending_tasks[user_id].append(task)

    try:
        parts = approval_text.split(':')
        user_id = int(parts[0])
        count = int(parts[1])

        if user_id not in pending_tasks or not pending_tasks[user_id]:
            bot.send_message(chat_id, "❌ *এই ইউজারের কোনো পেন্ডিং কাজ নেই।*", reply_markup=get_admin_menu(), parse_mode="Markdown")
            user_steps[chat_id] = None
            return

        if count > len(pending_tasks[user_id]):
            bot.send_message(chat_id, f"❌ *মাত্র `{len(pending_tasks[user_id])}` টি কাজ আছে।*", reply_markup=get_admin_menu(), parse_mode="Markdown")
            user_steps[chat_id] = None
            return

        total_amount = count * settings['work_reward']
        if user_id not in user_balances:
            user_balances[user_id] = 0.00

        user_balances[user_id] += total_amount
        approved = 0
        for task in pending_tasks[user_id]:
            if approved < count:
                task_id = f"{user_id}_{task['timestamp']}"
                completed_task_ids.add(task_id)
                approved += 1

        approved_count[user_id] = approved_count.get(user_id, 0) + count
        referral_commission = (total_amount * settings['refer_commission']) / 100
        referrer_id = referred_users.get(user_id)

        if referrer_id and referrer_id in user_balances:
            user_balances[referrer_id] += referral_commission
            try:
                user_name = user_names.get(user_id, "ইউজার")
                bot.send_message(referrer_id,
                    f"💰 *━━ রেফারেল কমিশন পেয়েছেন! ━━*\n\n"
                    f"👤 *ইউজার:* {user_name}\n"
                    f"✅ *অনুমোদিত কাজ:* {count} টি\n"
                    f"💵 *আপনার কমিশন:* `৳{referral_commission:.2f}` (৫%)\n\n"
                    f"💰 *নতুন ব্যালেন্স:* `৳{user_balances[referrer_id]:.2f}`",
                    parse_mode="Markdown")
            except:
                pass

        user_steps[chat_id] = None
        bot.send_message(chat_id,
            f"✅ *{count} টি কাজ এপ্রুভ হয়েছে!*\n\n"
            f"💰 *যোগ করা হয়েছে:* `৳{total_amount:.2f}`\n"
            f"💵 *রেফারেল কমিশন:* `৳{referral_commission:.2f}`",
            reply_markup=get_admin_menu(), parse_mode="Markdown")

        try:
            bot.send_message(user_id,
                f"🎊 *━━━━━━━━━━━━━━━━━━━━━*\n"
                f"✅ *অভিনন্দন! কাজ এপ্রুভ হয়েছে!*\n"
                f"*━━━━━━━━━━━━━━━━━━━━━*\n\n"
                f"📋 *এপ্রুভ হয়েছে:* `{count}` টি কাজ\n"
                f"💰 *আপনার ব্যালেন্সে যোগ হয়েছে:* `৳{total_amount:.2f}`\n\n"
                f"💳 উত্তোলন করতে *টাকা উত্তোলন করুন* বাটনে চাপুন।",
                parse_mode="Markdown")
        except:
            pass
    except:
        bot.send_message(chat_id,
            "❌ *ফরম্যাট ভুল!*\n\n"
            "✅ *সঠিক ফরম্যাট:* `ইউজারআইডি:সংখ্যা`\n"
            "📌 *উদাহরণ:* `7993941422:5`",
            reply_markup=get_admin_menu(), parse_mode="Markdown")
        user_steps[chat_id] = None

@bot.message_handler(func=lambda message: message.text == "📢 সবাইকে বার্তা পাঠান" and admin_sessions.get(message.chat.id))
def broadcast_menu(message):
    chat_id = message.chat.id
    user_steps[chat_id] = 'BROADCAST_MESSAGE'
    bot.send_message(chat_id,
        "📢 *ব্রডকাস্ট মেসেজ লিখুন:*\n\n"
        "📌 এই মেসেজটি সকল ইউজারের কাছে পাঠানো হবে।",
        parse_mode="Markdown")

@bot.message_handler(func=lambda message: user_steps.get(message.chat.id) == 'BROADCAST_MESSAGE')
def process_broadcast(message):
    chat_id = message.chat.id
    broadcast_msg = message.text.strip()
    success = 0
    failed = 0

    for user_id in user_balances.keys():
        if user_id != ADMIN_CHAT_ID:
            try:
                bot.send_message(user_id,
                    f"📢 *━━━━━━━━━━━━━━━━━━━━━*\n"
                    f"👑 *প্রশাসকের বিশেষ বার্তা*\n"
                    f"*━━━━━━━━━━━━━━━━━━━━━*\n\n"
                    f"{broadcast_msg}",
                    parse_mode="Markdown")
                success += 1
            except:
                failed += 1

    user_steps[chat_id] = None
    bot.send_message(chat_id,
        f"✅ *ব্রডকাস্ট সম্পন্ন!*\n\n"
        f"✅ *সফল:* {success} জন\n"
        f"❌ *ব্যর্থ:* {failed} জন",
        reply_markup=get_admin_menu(), parse_mode="Markdown")

# ==================== REWARD MANAGEMENT (দুটো অপশন) ====================

@bot.message_handler(func=lambda message: message.text == "💰 রিওয়ার্ড পরিবর্তন করুন" and admin_sessions.get(message.chat.id))
def admin_reward_menu(message):
    chat_id = message.chat.id
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("⚡ কাজের রেট পরিবর্তন করুন", callback_data="change_work_reward"))
    markup.add(InlineKeyboardButton("👥 রেফারেল বোনাস পরিবর্তন করুন", callback_data="change_refer_bonus"))
    bot.send_message(chat_id,
        f"💰 *━━ রিওয়ার্ড ম্যানেজমেন্ট ━━*\n\n"
        f"⚡ *বর্তমান কাজের রেট:* `৳{settings['work_reward']:.2f}`\n"
        f"👥 *বর্তমান রেফারেল বোনাস:* `৳{settings['refer_bonus']:.2f}`\n\n"
        f"🔽 কোনটা পরিবর্তন করতে চান?",
        reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "change_work_reward")
def cb_change_work_reward(call):
    chat_id = call.message.chat.id
    if not admin_sessions.get(chat_id):
        bot.answer_callback_query(call.id, "❌ আপনি Admin নন!", show_alert=True)
        return
    bot.answer_callback_query(call.id)
    user_steps[chat_id] = 'CHANGE_REWARD'
    bot.send_message(chat_id,
        f"⚡ *কাজের রেট পরিবর্তন করুন*\n\n"
        f"📌 *বর্তমান রেট:* `৳{settings['work_reward']:.2f}`\n\n"
        f"🔢 নতুন রেট লিখুন (শুধু সংখ্যা):",
        parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "change_refer_bonus")
def cb_change_refer_bonus(call):
    chat_id = call.message.chat.id
    if not admin_sessions.get(chat_id):
        bot.answer_callback_query(call.id, "❌ আপনি Admin নন!", show_alert=True)
        return
    bot.answer_callback_query(call.id)
    user_steps[chat_id] = 'CHANGE_REFER_BONUS'
    bot.send_message(chat_id,
        f"👥 *রেফারেল বোনাস পরিবর্তন করুন*\n\n"
        f"📌 *বর্তমান বোনাস:* `৳{settings['refer_bonus']:.2f}`\n\n"
        f"🔢 নতুন বোনাস লিখুন (শুধু সংখ্যা):",
        parse_mode="Markdown")

@bot.message_handler(func=lambda message: user_steps.get(message.chat.id) == 'CHANGE_REWARD')
def process_reward(message):
    chat_id = message.chat.id
    try:
        new_rate = float(message.text.strip())
        settings['work_reward'] = new_rate
        settings['tasks']['instagram_2fa']['reward'] = new_rate
        user_steps[chat_id] = None
        bot.send_message(chat_id,
            f"✅ *কাজের রেট আপডেট হয়েছে!*\n\n"
            f"⚡ *নতুন রেট:* `৳{new_rate:.2f}`",
            reply_markup=get_admin_menu(), parse_mode="Markdown")
    except:
        bot.send_message(chat_id, "❌ *সংখ্যা দিন! উদাহরণ:* `3.40`", parse_mode="Markdown")

@bot.message_handler(func=lambda message: user_steps.get(message.chat.id) == 'CHANGE_REFER_BONUS')
def process_refer_bonus(message):
    chat_id = message.chat.id
    try:
        new_bonus = float(message.text.strip())
        settings['refer_bonus'] = new_bonus
        user_steps[chat_id] = None
        bot.send_message(chat_id,
            f"✅ *রেফারেল বোনাস আপডেট হয়েছে!*\n\n"
            f"👥 *নতুন বোনাস:* `৳{new_bonus:.2f}`",
            reply_markup=get_admin_menu(), parse_mode="Markdown")
    except:
        bot.send_message(chat_id, "❌ *সংখ্যা দিন! উদাহরণ:* `2.00`", parse_mode="Markdown")

# ==================== APPROVE / REJECT INLINE CALLBACKS ====================

@bot.callback_query_handler(func=lambda call: call.data.startswith("approve_"))
def cb_approve_task(call):
    chat_id = call.message.chat.id
    if not admin_sessions.get(chat_id):
        bot.answer_callback_query(call.id, "❌ Admin লগইন করুন!", show_alert=True)
        return
    target_user_id = int(call.data.split("_")[1])
    bot.answer_callback_query(call.id)
    pending_action[chat_id] = {'action': 'approve', 'user_id': target_user_id}
    user_steps[chat_id] = 'INLINE_APPROVE'

    pending_count = sum(
        1 for task in submitted_tasks.get(target_user_id, [])
        if f"{target_user_id}_{task['timestamp']}" not in completed_task_ids
        and f"{target_user_id}_{task['timestamp']}" not in rejected_task_ids
    )
    user_name = user_names.get(target_user_id, "অজানা")
    bot.send_message(chat_id,
        f"✅ *এপ্রুভ করুন*\n\n"
        f"👤 *ইউজার:* {user_name}\n"
        f"🆔 *ID:* `{target_user_id}`\n"
        f"⏳ *পেন্ডিং কাজ:* {pending_count} টি\n\n"
        f"🔢 কয়টা এপ্রুভ করতে চান? সংখ্যা লিখুন:",
        parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("reject_"))
def cb_reject_task(call):
    chat_id = call.message.chat.id
    if not admin_sessions.get(chat_id):
        bot.answer_callback_query(call.id, "❌ Admin লগইন করুন!", show_alert=True)
        return
    target_user_id = int(call.data.split("_")[1])
    bot.answer_callback_query(call.id)
    pending_action[chat_id] = {'action': 'reject', 'user_id': target_user_id}
    user_steps[chat_id] = 'INLINE_REJECT'

    pending_count = sum(
        1 for task in submitted_tasks.get(target_user_id, [])
        if f"{target_user_id}_{task['timestamp']}" not in completed_task_ids
        and f"{target_user_id}_{task['timestamp']}" not in rejected_task_ids
    )
    user_name = user_names.get(target_user_id, "অজানা")
    bot.send_message(chat_id,
        f"❌ *রিজেক্ট করুন*\n\n"
        f"👤 *ইউজার:* {user_name}\n"
        f"🆔 *ID:* `{target_user_id}`\n"
        f"⏳ *পেন্ডিং কাজ:* {pending_count} টি\n\n"
        f"🔢 কয়টা রিজেক্ট করতে চান? সংখ্যা লিখুন:",
        parse_mode="Markdown")

@bot.message_handler(func=lambda message: user_steps.get(message.chat.id) == 'INLINE_APPROVE')
def process_inline_approve(message):
    chat_id = message.chat.id
    action_data = pending_action.get(chat_id, {})
    target_user_id = action_data.get('user_id')

    if not target_user_id:
        user_steps[chat_id] = None
        return

    try:
        count = int(message.text.strip())
    except:
        bot.send_message(chat_id, "❌ *শুধু সংখ্যা দিন!*", parse_mode="Markdown")
        return

    pending_list = [
        task for task in submitted_tasks.get(target_user_id, [])
        if f"{target_user_id}_{task['timestamp']}" not in completed_task_ids
        and f"{target_user_id}_{task['timestamp']}" not in rejected_task_ids
    ]

    if count > len(pending_list):
        bot.send_message(chat_id,
            f"❌ *মাত্র `{len(pending_list)}` টি পেন্ডিং কাজ আছে।*\n"
            f"🔢 আবার সংখ্যা দিন:",
            parse_mode="Markdown")
        return

    total_amount = count * settings['work_reward']
    if target_user_id not in user_balances:
        user_balances[target_user_id] = 0.00
    user_balances[target_user_id] += total_amount

    approved = 0
    for task in pending_list:
        if approved < count:
            task_id = f"{target_user_id}_{task['timestamp']}"
            completed_task_ids.add(task_id)
            approved += 1

    approved_count[target_user_id] = approved_count.get(target_user_id, 0) + count

    referral_commission = (total_amount * settings['refer_commission']) / 100
    referrer_id = referred_users.get(target_user_id)
    if referrer_id and referrer_id in user_balances:
        user_balances[referrer_id] += referral_commission
        try:
            bot.send_message(referrer_id,
                f"💰 *রেফারেল কমিশন পেয়েছেন!*\n\n"
                f"✅ *এপ্রুভ:* {count} টি কাজ\n"
                f"💵 *কমিশন:* `৳{referral_commission:.2f}`\n"
                f"💰 *ব্যালেন্স:* `৳{user_balances[referrer_id]:.2f}`",
                parse_mode="Markdown")
        except:
            pass

    user_steps[chat_id] = None
    pending_action.pop(chat_id, None)

    bot.send_message(chat_id,
        f"✅ *{count} টি কাজ এপ্রুভ করা হয়েছে!*\n\n"
        f"👤 *ইউজার ID:* `{target_user_id}`\n"
        f"💰 *যোগ হয়েছে:* `৳{total_amount:.2f}`\n"
        f"💵 *রেফারেল কমিশন:* `৳{referral_commission:.2f}`",
        reply_markup=get_admin_menu(), parse_mode="Markdown")

    try:
        bot.send_message(target_user_id,
            f"🎊 *━━━━━━━━━━━━━━━━━━━━━*\n"
            f"✅ *অভিনন্দন! কাজ এপ্রুভ হয়েছে!*\n"
            f"*━━━━━━━━━━━━━━━━━━━━━*\n\n"
            f"📋 *এপ্রুভ:* `{count}` টি কাজ\n"
            f"💰 *ব্যালেন্সে যোগ হয়েছে:* `৳{total_amount:.2f}`\n\n"
            f"💳 *টাকা উত্তোলন করুন* বাটনে চাপুন!",
            parse_mode="Markdown")
    except:
        pass

@bot.message_handler(func=lambda message: user_steps.get(message.chat.id) == 'INLINE_REJECT')
def process_inline_reject(message):
    chat_id = message.chat.id
    action_data = pending_action.get(chat_id, {})
    target_user_id = action_data.get('user_id')

    if not target_user_id:
        user_steps[chat_id] = None
        return

    try:
        count = int(message.text.strip())
    except:
        bot.send_message(chat_id, "❌ *শুধু সংখ্যা দিন!*", parse_mode="Markdown")
        return

    pending_list = [
        task for task in submitted_tasks.get(target_user_id, [])
        if f"{target_user_id}_{task['timestamp']}" not in completed_task_ids
        and f"{target_user_id}_{task['timestamp']}" not in rejected_task_ids
    ]

    if count > len(pending_list):
        bot.send_message(chat_id,
            f"❌ *মাত্র `{len(pending_list)}` টি পেন্ডিং কাজ আছে।*\n"
            f"🔢 আবার সংখ্যা দিন:",
            parse_mode="Markdown")
        return

    rejected = 0
    for task in pending_list:
        if rejected < count:
            task_id = f"{target_user_id}_{task['timestamp']}"
            rejected_task_ids.add(task_id)
            rejected += 1

    user_steps[chat_id] = None
    pending_action.pop(chat_id, None)

    bot.send_message(chat_id,
        f"❌ *{count} টি কাজ রিজেক্ট করা হয়েছে!*\n\n"
        f"👤 *ইউজার ID:* `{target_user_id}`",
        reply_markup=get_admin_menu(), parse_mode="Markdown")

    try:
        bot.send_message(target_user_id,
            f"⚠️ *━━━━━━━━━━━━━━━━━━━━━*\n"
            f"❌ *কাজ রিজেক্ট হয়েছে!*\n"
            f"*━━━━━━━━━━━━━━━━━━━━━*\n\n"
            f"📋 *রিজেক্ট:* `{count}` টি কাজ\n\n"
            f"📌 সঠিকভাবে কাজ করুন এবং আবার সাবমিট করুন।\n"
            f"📞 সমস্যা হলে সাপোর্টে যোগাযোগ করুন।",
            parse_mode="Markdown")
    except:
        pass

# ==================== USER HANDLERS ====================

@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    text_args = message.text.split()

    if not check_channel_member(chat_id):
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("📢 চ্যানেলে যোগ দিন এখনই!", url=CHANNEL_URL))
        bot.send_message(chat_id,
            "🌟 *━━━━━━━━━━━━━━━━━━━━━*\n"
            "🔔 *চ্যানেলে যোগ দেওয়া বাধ্যতামূলক!*\n"
            "*━━━━━━━━━━━━━━━━━━━━━*\n\n"
            "💎 আমাদের প্রিমিয়াম প্ল্যাটফর্ম ব্যবহার করতে\n"
            "আমাদের অফিশিয়াল চ্যানেলে যোগ দিন।\n\n"
            "⬇️ *নিচের বাটনে ক্লিক করুন:*",
            reply_markup=markup, parse_mode="Markdown")
        return

    if chat_id not in user_balances:
        user_balances[chat_id] = 0.00
        user_info = message.from_user
        user_name = user_info.first_name or "ব্যবহারকারী"
        if user_info.last_name:
            user_name += f" {user_info.last_name}"
        user_names[chat_id] = user_name

        if len(text_args) > 1:
            try:
                referrer_id = int(text_args[1])
                if referrer_id != chat_id and referrer_id != ADMIN_CHAT_ID and chat_id not in referred_users:
                    referred_users[chat_id] = referrer_id
                    if referrer_id not in user_balances:
                        user_balances[referrer_id] = 0.00
                    user_balances[referrer_id] += settings['refer_bonus']
                    try:
                        bot.send_message(referrer_id,
                            f"🎉 *━━━━━━━━━━━━━━━━━━━━━*\n"
                            f"🌟 *নতুন রেফারেল বোনাস পেয়েছেন!*\n"
                            f"*━━━━━━━━━━━━━━━━━━━━━*\n\n"
                            f"💰 আপনার অ্যাকাউন্টে `৳{settings['refer_bonus']:.2f}` যোগ হয়েছে!\n\n"
                            f"🚀 আরও বেশি আয় করতে বন্ধুদের ইনভাইট করতে থাকুন!",
                            parse_mode="Markdown")
                    except:
                        pass
            except:
                pass

    bot.send_message(chat_id,
        "🌟 *━━━━━━━━━━━━━━━━━━━━━━━━*\n"
        "💎 *SMART EARNING PLATFORM-এ*\n"
        "   *স্বাগতম!*\n"
        "*━━━━━━━━━━━━━━━━━━━━━━━━*\n\n"
        "🏆 বাংলাদেশের সেরা অনলাইন আয়ের প্ল্যাটফর্ম\n\n"
        "✅ *কাজ করুন* — প্রতিটি কাজে পান `৳৩.৪০`\n"
        "✅ *ইনভাইট করুন* — প্রতিজনে পান `৳২.০০`\n"
        "✅ *কমিশন পান* — প্রতিটি কাজে `৫%` কমিশন\n"
        "✅ *যেকোনো সময়* টাকা উত্তোলন করুন\n\n"
        "💳 *পেমেন্ট মাধ্যম:* বিকাশ | নগদ | রকেট\n\n"
        "⬇️ *নিচের মেনু থেকে শুরু করুন:*",
        reply_markup=get_main_menu(), parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "💼 কাজ করুন")
def handle_kaaj(message):
    chat_id = message.chat.id
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    for key, task in settings['tasks'].items():
        if task['active']:
            markup.add(KeyboardButton(f"⚡ {task['name']} (৳{task['reward']:.2f})"))
    markup.add(KeyboardButton("🔙 মেইন মেনু"))
    bot.reply_to(message,
        "💼 *━━━━━━━━━━━━━━━━━━━━━*\n"
        "🎯 *কাজ সিলেক্ট করুন*\n"
        "*━━━━━━━━━━━━━━━━━━━━━*\n\n"
        "⬇️ নিচের যেকোনো একটি কাজ বেছে নিন:",
        reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda message: any(task['name'] in message.text for task in settings['tasks'].values()))
def handle_task_selection(message):
    chat_id = message.chat.id
    message_text = message.text
    selected_task = None
    for key, task in settings['tasks'].items():
        if task['name'] in message_text:
            selected_task = key
            break
    if selected_task and selected_task == 'instagram_2fa':
        handle_instagram(message)

def handle_instagram(message):
    chat_id = message.chat.id
    new_username = generate_unique_username()
    user_data[chat_id] = {'username': new_username}
    response_text = (
        "⚡ *━━━━━━━━━━━━━━━━━━━━━*\n"
        "📱 *ইনস্টাগ্রাম 2FA কাজ*\n"
        "*━━━━━━━━━━━━━━━━━━━━━*\n\n"
        "🔰 *ধাপ ১: নিচের তথ্য দিয়ে একটি নতুন*\n"
        "   *ইনস্টাগ্রাম অ্যাকাউন্ট তৈরি করুন:*\n\n"
        f"👤 *ইউজারনেম:* `{new_username}`\n"
        f"🔒 *পাসওয়ার্ড:* `{settings['password']}`\n\n"
        "🔰 *ধাপ ২: অ্যাকাউন্ট তৈরি হলে*\n"
        "   *2FA Enable করুন এবং Secret Key নিন।*\n\n"
        "🔰 *ধাপ ৩: Secret Key পেলে নিচের*\n"
        "   *বাটনে চাপুন।*\n\n"
        "⚠️ _সঠিকভাবে করলেই পেমেন্ট পাবেন।_"
    )
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("🔐 2FA Key আছে"))
    markup.add(KeyboardButton("🔙 মেইন মেনু"))
    bot.send_message(chat_id, response_text, parse_mode="Markdown", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "🔐 2FA Key আছে")
def ask_secret_key(message):
    chat_id = message.chat.id
    user_steps[chat_id] = 'WAITING_SECRET_KEY'
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("🔙 মেইন মেনু"))
    bot.send_message(chat_id,
        "🔑 *━━━━━━━━━━━━━━━━━━━━━*\n"
        "🔐 *2FA Secret Key সাবমিট করুন*\n"
        "*━━━━━━━━━━━━━━━━━━━━━*\n\n"
        "📌 ইনস্টাগ্রাম থেকে পাওয়া পুরো Key\n"
        "   নিচে পেস্ট করুন (স্পেস সহ চলবে):\n\n"
        "⚠️ _সঠিক Key না দিলে কাজ গ্রহণ হবে না।_",
        parse_mode="Markdown", reply_markup=markup)

@bot.message_handler(func=lambda message: user_steps.get(message.chat.id) == 'WAITING_SECRET_KEY')
def process_secret_key(message):
    chat_id = message.chat.id
    if message.text == "🔙 মেইন মেনু":
        user_steps[chat_id] = None
        user_data[chat_id] = {}
        bot.send_message(chat_id, "🔙 *মেইন মেনুতে ফিরে এসেছেন।*", reply_markup=get_main_menu(), parse_mode="Markdown")
        return

    secret_key = message.text.strip()
    username = user_data.get(chat_id, {}).get('username', 'Unknown')

    try:
        totp = pyotp.TOTP(secret_key.replace(" ", ""))
        live_code = totp.now()
        if chat_id not in submitted_tasks:
            submitted_tasks[chat_id] = []

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        task_data = {
            'user_id': chat_id,
            'username': username,
            'password': settings['password'],
            'secret_key': secret_key,
            'timestamp': timestamp
        }
        submitted_tasks[chat_id].append(task_data)

        if chat_id not in user_names:
            user_info = message.from_user
            user_name = user_info.first_name or "ব্যবহারকারী"
            if user_info.last_name:
                user_name += f" {user_info.last_name}"
            user_names[chat_id] = user_name

        save_to_google_sheets(chat_id, username, settings['password'], secret_key)

        admin_report = (
            f"📥 *━━━━━━━━━━━━━━━━━━━━━*\n"
            f"🔔 *নতুন কাজ জমা হয়েছে!*\n"
            f"*━━━━━━━━━━━━━━━━━━━━━*\n\n"
            f"👤 *ইউজার নাম:* {user_names.get(chat_id, 'অজানা')}\n"
            f"🆔 *ইউজার ID:* `{chat_id}`\n"
            f"🏷️ *ইউজারনেম:* `{username}`\n"
            f"🔐 *2FA Key:*\n`{secret_key}`\n"
            f"🔢 *লাইভ কোড:* `{live_code}`\n\n"
            f"⏳ *স্ট্যাটাস:* পেন্ডিং রিভিউ"
        )

        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("✅ এপ্রুভ করুন", callback_data=f"approve_{chat_id}"),
            InlineKeyboardButton("❌ রিজেক্ট করুন", callback_data=f"reject_{chat_id}")
        )

        try:
            bot.send_message(ADMIN_CHAT_ID, admin_report, parse_mode="Markdown", reply_markup=markup)
        except:
            pass

        bot.send_message(chat_id,
            f"✅ *━━━━━━━━━━━━━━━━━━━━━*\n"
            f"🎯 *কাজ সফলভাবে জমা হয়েছে!*\n"
            f"*━━━━━━━━━━━━━━━━━━━━━*\n\n"
            f"⏳ *স্ট্যাটাস:* 🔄 রিভিউ চলছে...\n"
            f"🔢 *লাইভ কোড:* `{live_code}`\n\n"
            f"⚠️ _লাইভ কোড প্রতি ৩০ সেকেন্ডে পরিবর্তন হয়।_\n\n"
            f"📌 এপ্রুভ হলে আপনাকে নোটিফিকেশন দেওয়া হবে।",
            parse_mode="Markdown")
    except Exception as e:
        bot.send_message(chat_id,
            "❌ *Key সঠিক নয়!*\n\n"
            "📌 ইনস্টাগ্রাম থেকে পাওয়া পুরো Key\n"
            "   সঠিকভাবে পেস্ট করুন এবং আবার চেষ্টা করুন।",
            parse_mode="Markdown")
        return

    user_steps[chat_id] = None
    bot.send_message(chat_id, "🔙 *মেইন মেনুতে ফিরে এসেছেন।*", reply_markup=get_main_menu(), parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "💰 আমার ব্যালেন্স")
def handle_balance(message):
    chat_id = message.chat.id
    balance = user_balances.get(chat_id, 0.00)
    total_approved = approved_count.get(chat_id, 0)
    total_referrals = sum(1 for ref_id in referred_users.values() if ref_id == chat_id)

    bot.reply_to(message,
        f"💰 *━━━━━━━━━━━━━━━━━━━━━*\n"
        f"📊 *আপনার অ্যাকাউন্ট ড্যাশবোর্ড*\n"
        f"*━━━━━━━━━━━━━━━━━━━━━*\n\n"
        f"💎 *মোট ব্যালেন্স:* `৳{balance:.2f}`\n\n"
        f"✅ *সম্পন্ন কাজ:* {total_approved} টি\n"
        f"👥 *মোট রেফারেল:* {total_referrals} জন\n\n"
        f"💳 *উত্তোলন করতে* → টাকা উত্তোলন করুন",
        parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "💳 টাকা উত্তোলন করুন")
def handle_withdrawal(message):
    chat_id = message.chat.id
    balance = user_balances.get(chat_id, 0.00)
    if balance <= 0.00:
        bot.reply_to(message,
            "❌ *━━━━━━━━━━━━━━━━━━━━━*\n"
            "💸 *ব্যালেন্স অপর্যাপ্ত!*\n"
            "*━━━━━━━━━━━━━━━━━━━━━*\n\n"
            "💰 *বর্তমান ব্যালেন্স:* `৳০.০০`\n\n"
            "📌 *আয় করুন:*\n"
            "  💼 কাজ করুন — `৳৩.৪০` প্রতিটি\n"
            "  👥 ইনভাইট দিন — `৳২.০০` প্রতিজন",
            parse_mode="Markdown")
    else:
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(KeyboardButton("📱 নগদ (Nagad)"), KeyboardButton("💳 বিকাশ (bKash)"))
        markup.add(KeyboardButton("🟪 রকেট (Rocket)"), KeyboardButton("🔙 মেইন মেনু"))
        user_steps[chat_id] = 'SELECT_METHOD'
        bot.send_message(chat_id,
            f"💳 *━━━━━━━━━━━━━━━━━━━━━*\n"
            f"💸 *টাকা উত্তোলন করুন*\n"
            f"*━━━━━━━━━━━━━━━━━━━━━*\n\n"
            f"💰 *উত্তোলনযোগ্য ব্যালেন্স:* `৳{balance:.2f}`\n\n"
            f"⬇️ *পেমেন্ট মাধ্যম বেছে নিন:*",
            reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda message: user_steps.get(message.chat.id) == 'SELECT_METHOD')
def process_method(message):
    chat_id = message.chat.id
    method = message.text
    if method in ["📱 নগদ (Nagad)", "💳 বিকাশ (bKash)", "🟪 রকেট (Rocket)"]:
        withdraw_data[chat_id] = {'method': method}
        user_steps[chat_id] = 'WAITING_NUMBER'
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(KeyboardButton("🔙 মেইন মেনু"))
        method_clean = method.split('(')[1].replace(')', '')
        bot.send_message(chat_id,
            f"📱 *{method_clean} নম্বর দিন*\n\n"
            f"📌 যেই নম্বরে টাকা পেতে চান সেটি লিখুন:",
            reply_markup=markup, parse_mode="Markdown")
    elif method == "🔙 মেইন মেনু":
        user_steps[chat_id] = None
        withdraw_data[chat_id] = {}
        bot.send_message(chat_id, "🔙 *মেইন মেনুতে ফিরে এসেছেন।*", reply_markup=get_main_menu(), parse_mode="Markdown")

@bot.message_handler(func=lambda message: user_steps.get(message.chat.id) == 'WAITING_NUMBER')
def process_number(message):
    chat_id = message.chat.id
    if message.text == "🔙 মেইন মেনু":
        user_steps[chat_id] = None
        withdraw_data[chat_id] = {}
        bot.send_message(chat_id, "🔙 *মেইন মেনুতে ফিরে এসেছেন।*", reply_markup=get_main_menu(), parse_mode="Markdown")
        return

    number = message.text.strip()
    method = withdraw_data[chat_id]['method']
    balance = user_balances.get(chat_id, 0.00)
    user_balances[chat_id] = 0.00
    method_clean = method.split('(')[1].replace(')', '')

    payment_request = (
        f"💳 *━━━━━━━━━━━━━━━━━━━━━*\n"
        f"💸 *নতুন উত্তোলন রিকোয়েস্ট!*\n"
        f"*━━━━━━━━━━━━━━━━━━━━━*\n\n"
        f"👤 *ইউজার নাম:* {user_names.get(chat_id, 'অজানা')}\n"
        f"🆔 *ইউজার ID:* `{chat_id}`\n"
        f"🛠️ *পেমেন্ট মাধ্যম:* `{method_clean}`\n"
        f"📱 *নম্বর:* `{number}`\n"
        f"💰 *পরিমাণ:* `৳{balance:.2f}`"
    )
    try:
        bot.send_message(ADMIN_CHAT_ID, payment_request, parse_mode="Markdown")
    except:
        pass

    bot.send_message(chat_id,
        f"✅ *━━━━━━━━━━━━━━━━━━━━━*\n"
        f"🎯 *উত্তোলন রিকোয়েস্ট জমা হয়েছে!*\n"
        f"*━━━━━━━━━━━━━━━━━━━━━*\n\n"
        f"💰 *পরিমাণ:* `৳{balance:.2f}`\n"
        f"📱 *মাধ্যম:* `{method_clean}`\n"
        f"📞 *নম্বর:* `{number}`\n\n"
        f"⏳ *স্ট্যাটাস:* প্রসেসিং হচ্ছে...\n\n"
        f"📌 সাধারণত ২৪ ঘণ্টার মধ্যে পেমেন্ট পৌঁছায়।",
        reply_markup=get_main_menu(), parse_mode="Markdown")
    user_steps[chat_id] = None

@bot.message_handler(func=lambda message: message.text == "🏆 লিডারবোর্ড দেখুন")
def handle_leaderboard(message):
    sorted_users = sorted(user_balances.items(), key=lambda x: x[1], reverse=True)[:10]
    leaderboard_text = (
        "🏆 *━━━━━━━━━━━━━━━━━━━━━*\n"
        "👑 *শীর্ষ ১০ আয়কারী*\n"
        "*━━━━━━━━━━━━━━━━━━━━━*\n\n"
    )
    if not sorted_users or all(b <= 0 for _, b in sorted_users):
        leaderboard_text += "📊 _এখনো কোনো ডাটা নেই। প্রথম হওয়ার সুযোগ আপনার!_"
    else:
        for i, (user_id, balance) in enumerate(sorted_users, 1):
            if balance > 0:
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"  {i}."
                user_name = user_names.get(user_id, "ব্যবহারকারী")
                leaderboard_text += f"{medal} *{user_name}*\n    💰 `৳{balance:.2f}`\n\n"
    bot.send_message(message.chat.id, leaderboard_text, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "📞 আমাদের সাপোর্ট")
def handle_support(message):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("📢 অফিশিয়াল চ্যানেল", url=CHANNEL_URL))
    markup.add(InlineKeyboardButton("💬 সরাসরি অ্যাডমিন", url="https://t.me/jubayer1622"))
    bot.send_message(message.chat.id,
        "📞 *━━━━━━━━━━━━━━━━━━━━━*\n"
        "🤝 *আমাদের সাথে যোগাযোগ করুন*\n"
        "*━━━━━━━━━━━━━━━━━━━━━*\n\n"
        "💬 যেকোনো সমস্যা বা প্রশ্নের জন্য\n"
        "আমরা সবসময় আপনার পাশে আছি।\n\n"
        "👤 *অ্যাডমিন:* @jubayer1622\n"
        "📢 *চ্যানেল:* @smartearningdigitalplatform\n\n"
        "⏰ *সাপোর্ট সময়:* সকাল ৯টা — রাত ১১টা",
        reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "👥 আয় করুন Invite দিয়ে")
def handle_invite(message):
    chat_id = message.chat.id
    bot_username = "inst_sell_1622_bot"
    refer_link = f"https://t.me/{bot_username}?start={chat_id}"
    total_referrals = sum(1 for ref_id in referred_users.values() if ref_id == chat_id)
    total_bonus = total_referrals * settings['refer_bonus']

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔗 রেফারাল লিংক কপি করুন", callback_data="copy_refer_link"))
    markup.add(InlineKeyboardButton("📊 আমার রেফারেল দেখুন", callback_data="my_referrals"))
    markup.add(InlineKeyboardButton("💰 আয়ের নিয়ম দেখুন", callback_data="earn_rules"))

    invite_text = (
        f"👥 *━━━━━━━━━━━━━━━━━━━━━*\n"
        f"🚀 *Invite করুন — আয় করুন!*\n"
        f"*━━━━━━━━━━━━━━━━━━━━━*\n\n"
        f"🔗 *আপনার রেফারাল লিংক:*\n"
        f"`{refer_link}`\n\n"
        f"💎 *আপনার রেফারেল স্ট্যাটাস:*\n"
        f"  👥 মোট রেফারেল: *{total_referrals} জন*\n"
        f"  💰 মোট বোনাস: `৳{total_bonus:.2f}`\n\n"
        f"🎁 *প্রতিজনে পাবেন:* `৳{settings['refer_bonus']:.2f}` বোনাস\n"
        f"💵 *প্লাস:* তাদের প্রতিটি কাজে `{settings['refer_commission']:.1f}%` কমিশন!\n\n"
        f"📌 _যত বেশি ইনভাইট, তত বেশি আয়!_"
    )
    bot.send_message(message.chat.id, invite_text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "copy_refer_link")
def copy_refer_link(call):
    chat_id = call.message.chat.id
    bot_username = "inst_sell_1622_bot"
    refer_link = f"https://t.me/{bot_username}?start={chat_id}"
    bot.answer_callback_query(call.id, "✅ লিংক পাঠানো হয়েছে!", show_alert=False)
    bot.send_message(chat_id,
        f"🔗 *আপনার রেফারাল লিংক:*\n\n"
        f"`{refer_link}`\n\n"
        f"📌 _এই লিংকটি বন্ধুদের সাথে শেয়ার করুন!_",
        parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "my_referrals")
def my_referrals(call):
    chat_id = call.message.chat.id
    referral_count = sum(1 for ref_id in referred_users.values() if ref_id == chat_id)
    total_bonus = referral_count * settings['refer_bonus']
    bot.answer_callback_query(call.id)
    bot.send_message(chat_id,
        f"📊 *━━ আপনার রেফারেল রিপোর্ট ━━*\n\n"
        f"👥 *মোট রেফারেল:* {referral_count} জন\n"
        f"💰 *রেফারেল বোনাস:* `৳{total_bonus:.2f}`\n"
        f"💵 *কমিশন রেট:* {settings['refer_commission']:.1f}%\n\n"
        f"🚀 _আরও বেশি ইনভাইট করুন, আরও বেশি আয় করুন!_",
        parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "earn_rules")
def earn_rules(call):
    chat_id = call.message.chat.id
    bot.answer_callback_query(call.id)
    bot.send_message(chat_id,
        f"💰 *━━━━━━━━━━━━━━━━━━━━━*\n"
        f"📋 *আয়ের সম্পূর্ণ নিয়মাবলী*\n"
        f"*━━━━━━━━━━━━━━━━━━━━━*\n\n"
        f"1️⃣ *কাজ করে আয়:*\n"
        f"   প্রতিটি 2FA কাজ → `৳{settings['work_reward']:.2f}`\n\n"
        f"2️⃣ *রেফারেল বোনাস:*\n"
        f"   প্রতিজন নতুন ইউজার → `৳{settings['refer_bonus']:.2f}`\n\n"
        f"3️⃣ *কমিশন আয়:*\n"
        f"   রেফারের প্রতিটি কাজে → `{settings['refer_commission']:.1f}%`\n\n"
        f"💳 *পেমেন্ট:* বিকাশ | নগদ | রকেট\n\n"
        f"📌 _সঠিকভাবে কাজ করুন, নিয়মিত আয় করুন!_",
        parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text in ["🔙 মেইন মেনু", "🔙 মেইন মেনুতে ফিরে গেলাম।"])
def back_to_main(message):
    user_steps[message.chat.id] = None
    withdraw_data[message.chat.id] = {}
    bot.send_message(message.chat.id, "🔙 *মেইন মেনুতে ফিরে এসেছেন।*", reply_markup=get_main_menu(), parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "⚙️ সিস্টেম সেটিংস" and admin_sessions.get(message.chat.id))
def admin_settings(message):
    chat_id = message.chat.id
    bot.send_message(chat_id,
        f"⚙️ *━━ সিস্টেম সেটিংস ━━*\n\n"
        f"🔐 *পাসওয়ার্ড:* `{settings['password']}`\n"
        f"⚡ *কাজের রেট:* `৳{settings['work_reward']:.2f}`\n"
        f"👥 *রেফারেল বোনাস:* `৳{settings['refer_bonus']:.2f}`\n"
        f"💵 *কমিশন রেট:* `{settings['refer_commission']:.1f}%`",
        reply_markup=get_admin_menu(), parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "📊 সিস্টেম স্ট্যাটিস্টিক্স" and admin_sessions.get(message.chat.id))
def admin_statistics(message):
    chat_id = message.chat.id
    total_pending = sum(
        1 for user_id, tasks_list in submitted_tasks.items()
        for task in tasks_list
        if f"{user_id}_{task['timestamp']}" not in completed_task_ids
        and f"{user_id}_{task['timestamp']}" not in rejected_task_ids
    )
    bot.send_message(chat_id,
        f"📊 *━━ সিস্টেম স্ট্যাটিস্টিক্স ━━*\n\n"
        f"👥 *মোট ইউজার:* {len(user_balances)}\n"
        f"💰 *মোট ব্যালেন্স:* `৳{sum(user_balances.values()):.2f}`\n"
        f"⏳ *পেন্ডিং কাজ:* {total_pending}\n"
        f"✅ *সম্পন্ন কাজ:* {len(completed_task_ids)}\n"
        f"❌ *রিজেক্ট কাজ:* {len(rejected_task_ids)}",
        reply_markup=get_admin_menu(), parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "🔐 পাসওয়ার্ড পরিবর্তন করুন" and admin_sessions.get(message.chat.id))
def admin_change_password(message):
    chat_id = message.chat.id
    user_steps[chat_id] = 'CHANGE_PASSWORD'
    bot.send_message(chat_id,
        f"🔐 *নতুন পাসওয়ার্ড লিখুন:*\n\n"
        f"📌 *বর্তমান:* `{settings['password']}`\n"
        f"⚠️ _কমপক্ষে ৫ ক্যারেক্টার দিন।_",
        parse_mode="Markdown")

@bot.message_handler(func=lambda message: user_steps.get(message.chat.id) == 'CHANGE_PASSWORD')
def process_new_password(message):
    chat_id = message.chat.id
    new_password = message.text.strip()
    if len(new_password) >= 5:
        settings['password'] = new_password
        user_steps[chat_id] = None
        bot.send_message(chat_id,
            f"✅ *পাসওয়ার্ড পরিবর্তন হয়েছে!*\n\n"
            f"🔐 *নতুন পাসওয়ার্ড:* `{new_password}`",
            reply_markup=get_admin_menu(), parse_mode="Markdown")
    else:
        bot.send_message(chat_id, "❌ *কমপক্ষে ৫ ক্যারেক্টার দিতে হবে!*", parse_mode="Markdown")

print("🤖 VIP বট চালু হচ্ছে...")
bot.infinity_polling()
