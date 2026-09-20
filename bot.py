import os
import threading
import random
import string
from http.server import HTTPServer, BaseHTTPRequestHandler
from PIL import Image, ImageDraw, ImageFont
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# --- রেন্ডার পোর্ট বাইন্ডিং ও স্লিপ হওয়া রোধ করার জন্য মিনি ওয়েব সার্ভার ---
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running 24/7!")

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHandler)
    server.serve_forever()

server_thread = threading.Thread(target=run_server, daemon=True)
server_thread.start()
# -------------------------------------------------------------------------

ADMIN_ID = 8262339619
ADMIN_BKASH = "01705351616"
ADMIN_USERNAME = "Ownertanvir99"
REFER_BONUS = 5.0
MIN_WITHDRAW = 50.0

GROUP_1 = "@Captchabotsupportgroup"
GROUP_2 = "@captchaearnofficial"

user_captchas = {}
user_balances = {}
user_wallets = {}
user_is_active = {}
referred_by = {}
all_users = set()

def generate_captcha_image(text):
    width, height = 200, 70
    image = Image.new('RGB', (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)
    
    for _ in range(5):
        x1 = random.randint(0, width)
        y1 = random.randint(0, height)
        x2 = random.randint(0, width)
        y2 = random.randint(0, height)
        draw.line([x1, y1, x2, y2], fill=(200, 200, 200), width=2)

    try:
        font = ImageFont.truetype("arial.ttf", 36)
    except:
        font = ImageFont.load_default()

    draw.text((35, 15), text, fill=(0, 0, 0), font=font)
    
    path = "captcha.png"
    image.save(path)
    return path

def generate_captcha_text():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))

async def check_membership(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if user_id == ADMIN_ID:
        return True
    try:
        member1 = await context.bot.get_chat_member(chat_id=GROUP_1, user_id=user_id)
        member2 = await context.bot.get_chat_member(chat_id=GROUP_2, user_id=user_id)
        valid_status = ['creator', 'administrator', 'member']
        return (member1.status in valid_status and member2.status in valid_status)
    except Exception as e:
        print(f"Membership check error: {e}")
        return True

async def send_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📢 Join Channel / Group 1", url=f"https://t.me/{GROUP_1.replace('@', '')}")],
        [InlineKeyboardButton("📢 Join Channel / Group 2", url=f"https://t.me/{GROUP_2.replace('@', '')}")],
        [InlineKeyboardButton("✅ I've Joined – Verify", callback_data="check_join")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    msg = (
        "⚡ **QuickCash Captcha Bot**\n"
        "----------------------------------------\n"
        "🔒 **বটে কাজ করতে হলে নিচের চ্যানেলগুলোতে জয়েন করুন!**\n\n"
        "📢 জয়েন করার পর নিচের **'I've Joined – Verify'** বাটনে ক্লিক করুন।"
    )
    if update.message:
        await update.message.reply_text(msg, reply_markup=reply_markup, parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.message.reply_text(msg, reply_markup=reply_markup, parse_mode="Markdown")

# স্ক্রিনশটের স্টাইলে প্রফেশনাল ইনলাইন মেনু কিবোর্ড
def get_main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Get Number", callback_data="menu_earn"), InlineKeyboardButton("🌍 Available Country", callback_data="menu_country")],
        [InlineKeyboardButton("📞 Support", callback_data="menu_support"), InlineKeyboardButton("💰 Balance", callback_data="menu_balance")],
        [InlineKeyboardButton("💳 Withdraw", callback_data="menu_withdraw"), InlineKeyboardButton("🏆 Leaderboard", callback_data="menu_leaderboard")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.chat.type != 'private':
        return

    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    
    is_joined = await check_membership(user_id, context)
    if not is_joined:
        await send_join_request(update, context)
        return

    all_users.add(user_id)
    if user_id not in user_balances:
        user_balances[user_id] = 0
        user_is_active[user_id] = False

    if context.args:
        try:
            referrer_id = int(context.args[0])
            if referrer_id != user_id and referrer_id not in referred_by.get(user_id, []):
                referred_by[user_id] = referrer_id
                user_balances[referrer_id] = user_balances.get(referrer_id, 0) + REFER_BONUS
                try:
                    await context.bot.send_message(
                        chat_id=referrer_id,
                        text=f"🎉 **নতুন রেফারেল বোনাস!**\n\nকেউ আপনার লিংকে জয়েন করেছে। আপনি পেয়েছেন **{REFER_BONUS} টাকা** বোনাস!",
                        parse_mode="Markdown"
                    )
                except:
                    pass
        except ValueError:
            pass

    welcome_msg = (
        "⚡ **QuickCash Captcha Bot**\n"
        "----------------------------------------\n"
        f"🔒 **Welcome, {user_name}!**\n\n"
        "✅ ঘরে বসে সহজে ক্যাপচা টাইপ করে ইনকাম করুন\n"
        "🔔 সঠিক ক্যাপচায় ইনস্ট্যান্ট ব্যালেন্স যোগ হবে\n"
        "🎉 বন্ধুদের রেফার করে আকর্ষণীয় বোনাস পান\n"
        "----------------------------------------\n"
        "⚡ **কাজ শুরু করতে নিচের মেনু থেকে অপশন বেছে নিন!**"
    )

    target_msg = update.message if update.message else update.callback_query.message
    await target_msg.reply_text(welcome_msg, reply_markup=get_main_menu_keyboard(), parse_mode="Markdown")

async def verify_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    is_joined = await check_membership(user_id, context)
    if is_joined:
        try:
            await query.message.delete()
        except:
            pass
        await start(update, context)
    else:
        await query.message.reply_text("❌ আপনি এখনো সবগুলোতে জয়েন করেননি! দয়া করে জয়েন হয়ে আবার **'I've Joined – Verify'** বাটনে ক্লিক করুন।", parse_mode="Markdown")

async def earn_handler(update_obj, context):
    user_id = update_obj.effective_user.id
    all_users.add(user_id)
    
    captcha_text = generate_captcha_text()
    user_captchas[user_id] = captcha_text
    img_path = generate_captcha_image(captcha_text)
    
    with open(img_path, 'rb') as photo:
        await update_obj.message.reply_photo(
            photo=photo,
            caption="🖼 **উপরে ছবিতে থাকা কোডটি দেখে নিচে লিখে পাঠান:**",
            reply_markup=get_main_menu_keyboard()
        )

async def account_handler(update_obj, context):
    user_id = update_obj.effective_user.id
    all_users.add(user_id)
    
    balance = user_balances.get(user_id, 0)
    wallet = user_wallets.get(user_id, "সেট করা হয়নি")
    status = "✅ অ্যাক্টিভ" if user_is_active.get(user_id, False) else "❌ ইনঅ্যাক্টিভ"
    
    text = (
        f"💰 **Wallet**\n\n"
        f"🆔 **User ID:** `{user_id}`\n"
        f"💵 **Balance:** {balance} TK\n"
        f"💳 **Wallet:** {wallet}\n"
        f"📊 **Status:** {status}"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 Set Wallet", callback_data="menu_setwallet"), InlineKeyboardButton("🏧 Withdraw", callback_data="menu_withdraw")]
    ])
    await update_obj.message.reply_text(text, reply_markup=keyboard, parse_mode="Markdown")

async def withdraw_handler(update_obj, context):
    user_id = update_obj.effective_user.id
    all_users.add(user_id)
    
    wallet = user_wallets.get(user_id)
    if not wallet:
        await update_obj.message.reply_text("❌ আপনার বিকাশ/নগদ নাম্বার সেট করা নেই! আগে নাম্বার সেট করুন।", reply_markup=get_main_menu_keyboard())
        return

    balance = user_balances.get(user_id, 0)
    context.user_data['waiting_for_withdraw_amount'] = True
    await update_obj.message.reply_text(
        f"🏧 **মিনিমাম উইথড্র: {MIN_WITHDRAW} TK**\n"
        f"💰 **আপনার বর্তমান ব্যালেন্স:** {balance} TK\n\n"
        f"কত টাকা উইথড্র করতে চান? এমাউন্টটি লিখে পাঠান:",
        parse_mode="Markdown"
    )

async def setwallet_handler(update_obj, context):
    user_id = update_obj.effective_user.id
    all_users.add(user_id)
    
    context.user_data['waiting_for_wallet'] = True
    current_wallet = user_wallets.get(user_id, "সেট করা হয়নি")
    await update_obj.message.reply_text(
        f"📱 **বর্তমান বিকাশ/নগদ নাম্বার:** `{current_wallet}`\n\n"
        f"আপনার সঠিক বিকাশ অথবা নগদ নাম্বারটি লিখে পাঠান:",
        parse_mode="Markdown"
    )

async def refer_handler(update_obj, context):
    user_id = update_obj.effective_user.id
    all_users.add(user_id)
    
    bot_username = context.bot.username
    refer_link = f"https://t.me/{bot_username}?start={user_id}"
    text = (
        f"👥 **রেফার করুন ও ইনকাম করুন**\n\n"
        f"🔗 **আপনার রেফারেল লিংক:**\n`{refer_link}`\n\n"
        f"🎁 প্রতি রেফারে পাবেন **{REFER_BONUS} টাকা** বোনাস!"
    )
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔗 Share Link", url=f"https://t.me/share/url?url={refer_link}")]])
    await update_obj.message.reply_text(text, reply_markup=keyboard, parse_mode="Markdown")

async def support_handler(update_obj, context):
    support_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📞 Contact Support", url=f"https://t.me/{ADMIN_USERNAME}")],
        [InlineKeyboardButton("👨‍💻 Contact Developer", url=f"https://t.me/{ADMIN_USERNAME}")]
    ])
    await update_obj.message.reply_text("👨‍💻 **এডমিন সাপোর্ট প্যানেল:**\n\nযেকোনো সমস্যায় সরাসরি যোগাযোগ করুন:", reply_markup=support_keyboard, parse_mode="Markdown")

async def leaderboard_handler(update_obj, context):
    text = (
        "🏆 **Daily Leaderboard – Today Top 10**\n"
        "----------------------------------------\n"
        "১. Admin — 69 OTP — 69.00৳\n"
        "২. User2 — 64 OTP — 64.00৳\n"
        "৩. User3 — 9 OTP — 9.00৳"
    )
    await update_obj.message.reply_text(text, reply_markup=get_main_menu_keyboard(), parse_mode="Markdown")

async def admin_panel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return
    total_users = len(all_users)
    admin_text = (
        f"👑 **এডমিন প্যানেল**\n\n"
        f"📊 মোট ইউজার: {total_users} জন\n"
        f"🖼️ *গ্রুপে পেমেন্ট প্রুফ বা ছবি পোস্ট করতে যেকোনো ছবি এই ইনবক্সে পাঠান।*\n\n"
        "**কমান্ডসমূহ:**\n"
        "1. আইডি অ্যাক্টিভ করতে: `/activate USER_ID`\n"
        "2. ব্যালেন্স দিতে: `/addbalance USER_ID AMOUNT`\n"
        "3. ব্রডকাস্ট করতে: `/broadcast মেসেজ`"
    )
    await update.message.reply_text(admin_text, reply_markup=get_main_menu_keyboard(), parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type != 'private':
        return

    user_id = update.effective_user.id
    all_users.add(user_id)

    if update.message.photo and user_id == ADMIN_ID:
        caption = update.message.caption or "পেমেন্ট প্রুফ / আপডেট"
        context.user_data['pending_photo'] = update.message.photo[-1].file_id
        context.user_data['pending_caption'] = caption
        kb = [
            [InlineKeyboardButton("📢 গ্রুপ ১ এ পোস্ট করুন", callback_data="post_g1")],
            [InlineKeyboardButton("📢 গ্রুপ ২ এ পোস্ট করুন", callback_data="post_g2")]
        ]
        await update.message.reply_text("🖼️ ছবি পাওয়া গেছে! কোন গ্রুপে পোস্ট করবেন সিলেক্ট করুন:", reply_markup=InlineKeyboardMarkup(kb))
        return

    if not update.message.text:
        return

    text = update.message.text.strip()

    if text in ["Earn", "/earn"]:
        context.user_data['waiting_for_wallet'] = False
        context.user_data['waiting_for_withdraw_amount'] = False
        await earn_handler(update, context)
        return
    elif text in ["Account", "/account"]:
        context.user_data['waiting_for_wallet'] = False
        context.user_data['waiting_for_withdraw_amount'] = False
        await account_handler(update, context)
        return
    elif text in ["Withdraw", "/withdraw"]:
        context.user_data['waiting_for_wallet'] = False
        await withdraw_handler(update, context)
        return
    elif text in ["Set Wallet", "/setwallet"]:
        context.user_data['waiting_for_withdraw_amount'] = False
        await setwallet_handler(update, context)
        return
    elif text in ["Refer", "/refer"]:
        context.user_data['waiting_for_wallet'] = False
        context.user_data['waiting_for_withdraw_amount'] = False
        await refer_handler(update, context)
        return
    elif text in ["Support", "/support"]:
        context.user_data['waiting_for_wallet'] = False
        context.user_data['waiting_for_withdraw_amount'] = False
        await support_handler(update, context)
        return
    elif text in ["Admin Panel", "/admin"] and user_id == ADMIN_ID:
        context.user_data['waiting_for_wallet'] = False
        context.user_data['waiting_for_withdraw_amount'] = False
        await admin_panel_handler(update, context)
        return

    if context.user_data.get('waiting_for_wallet'):
        user_wallets[user_id] = text
        context.user_data['waiting_for_wallet'] = False
        await update.message.reply_text(f"✅ আপনার বিকাশ/নগদ নাম্বার সফলভাবে সেট করা হয়েছে: `{text}`", reply_markup=get_main_menu_keyboard(), parse_mode="Markdown")
        return

    if context.user_data.get('waiting_for_withdraw_amount'):
        context.user_data['waiting_for_withdraw_amount'] = False
        try:
            amount = float(text)
            balance = user_balances.get(user_id, 0)
            wallet = user_wallets.get(user_id)

            if not wallet:
                await update.message.reply_text("❌ আপনার বিকাশ/নগদ নাম্বার সেট করা নেই! আগে 'Set Wallet' থেকে নাম্বার দিন।", reply_markup=get_main_menu_keyboard())
                return

            if amount < MIN_WITHDRAW or amount > balance:
                await update.message.reply_text("❌ আপনার অ্যাকাউন্টে পর্যাপ্ত টাকা নাই অথবা মিনিমাম উইথড্র ৫০ টাকা।", reply_markup=get_main_menu_keyboard())
                return

            is_active = user_is_active.get(user_id, False)
            if not is_active:
                msg = (
                    "⚠️ **আইডি ইনঅ্যাক্টিভ!**\n\n"
                    "আপনার অ্যাকাউন্টটি এখনো ইনঅ্যাক্টিভ রয়েছে। টাকা উইথড্র করতে হলে আপনার অ্যাকাউন্টটি একবার অ্যাক্টিভ করতে হবে। একবার অ্যাক্টিভ করলে পরবর্তীতে আর কখনো ফি লাগবে না。\n\n"
                    "আইডি অ্যাক্টিভ করার জন্য **৩০ টাকা** নিচের বিকাশ/নগদ নাম্বারে সেন্ড মানি করুন:\n\n"
                    f"📱 **বিকাশ/নগদ নাম্বার:** `{ADMIN_BKASH}`\n\n"
                    "টাকা পাঠানোর পর ট্রানজেকশন আইডি (TrxID) সহ সাপোর্ট অপশন থেকে এডমিনকে জানান।"
                )
                await update.message.reply_text(msg, reply_markup=get_main_menu_keyboard(), parse_mode="Markdown")
                return

            user_balances[user_id] = balance - amount
            await update.message.reply_text(
                f"✅ **উইথড্র রিকোয়েস্ট সফল হয়েছে!**\n\n"
                f"উইথড্র এমাউন্ট: {amount} TK\n"
                f"বিকাশ/নগদ নাম্বার: `{wallet}`\n"
                f"খুব শীঘ্রই আপনার নাম্বারে পেমেন্ট পৌঁছে যাবে।",
                reply_markup=get_main_menu_keyboard(),
                parse_mode="Markdown"
            )
        except ValueError:
            await update.message.reply_text("❌ সঠিক সংখ্যায় এমাউন্ট লিখে পাঠান (যেমন: 50 বা 100)।", reply_markup=get_main_menu_keyboard())
        return

    if user_id in user_captchas:
        correct_captcha = user_captchas[user_id]
        if text.upper() == correct_captcha.upper():
            user_balances[user_id] = user_balances.get(user_id, 0) + 2
            del user_captchas[user_id]
            await update.message.reply_text("✅ **সঠিক হয়েছে! ২ টাকা আপনার অ্যাকাউন্টে যোগ হয়েছে।**", reply_markup=get_main_menu_keyboard(), parse_mode="Markdown")
        else:
            await update.message.reply_text("❌ **ভুল ক্যাপচা! আবার চেষ্টা করুন।**", reply_markup=get_main_menu_keyboard(), parse_mode="Markdown")
        return

    await update.message.reply_text("দয়া করে নিচের মেনু থেকে কোনো একটি অপশন বেছে নিন।", reply_markup=get_main_menu_keyboard())

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    if query.data == "check_join":
        await verify_button(update, context)
        return

    # ইনলাইন মেনু বাটন হ্যান্ডলিং
    if query.data.startswith("menu_"):
        await query.answer()
        action = query.data.replace("menu_", "")
        
        # ডামি মেসেজ অবজেক্ট তৈরি যাতে আগের ফাংশনগুলো কাজ করে
        class FakeMessage:
            def __init__(self, msg):
                self.message = msg
                self.effective_user = query.from_user
            async def reply_text(self, *args, **kwargs):
                return await self.message.reply_text(*args, **kwargs)
            async def reply_photo(self, *args, **kwargs):
                return await self.message.reply_photo(*args, **kwargs)

        fake_update = FakeMessage(query.message)

        if action == "earn":
            await earn_handler(fake_update, context)
        elif action == "country":
            await query.message.reply_text("🌍 **Available Countries:**\n- Bangladesh (Available)\n- India (Available)", reply_markup=get_main_menu_keyboard(), parse_mode="Markdown")
        elif action == "support":
            await support_handler(fake_update, context)
        elif action == "balance":
            await account_handler(fake_update, context)
        elif action == "withdraw":
            await withdraw_handler(fake_update, context)
        elif action == "leaderboard":
            await leaderboard_handler(fake_update, context)
        elif action == "setwallet":
            await setwallet_handler(fake_update, context)
        return

    await query.answer()
    if query.from_user.id != ADMIN_ID:
        return

    photo = context.user_data.get('pending_photo')
    caption = context.user_data.get('pending_caption', '')
    if not photo:
        await query.edit_message_text("❌ ছবির সময়সীমা শেষ হয়ে গেছে বা ছবি পাওয়া যায়নি।")
        return

    target = GROUP_1 if query.data == "post_g1" else GROUP_2
    try:
        await context.bot.send_photo(chat_id=target, photo=photo, caption=caption)
        await query.edit_message_text("✅ সফলভাবে নির্দিষ্ট গ্রুপে পোস্ট করা হয়েছে!")
    except Exception as e:
        await query.edit_message_text(f"❌ ত্রুটি দেখা দিয়েছে: {e}")

    context.user_data.pop('pending_photo', None)
    context.user_data.pop('pending_caption', None)

async def activate_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID: return
    try:
        target_id = int(context.args[0])
        user_is_active[target_id] = True
        await update.message.reply_text(f"✅ ইউজার `{target_id}`-এর আইডি সফলভাবে অ্যাক্টিভ করা হয়েছে।", parse_mode="Markdown")
        try:
            await context.bot.send_message(chat_id=target_id, text="🎉 **অভিনন্দন! আপনার অ্যাকাউন্ট সফলভাবে অ্যাক্টিভ করা হয়েছে। এখন থেকে আপনি উইথড্র করতে পারবেন।**")
        except: pass
    except:
        await update.message.reply_text("❌ সঠিক ফরম্যাট: `/activate USER_ID`", parse_mode="Markdown")

async def add_balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID: return
    try:
        target_id = int(context.args[0])
        amount = float(context.args[1])
        user_balances[target_id] = user_balances.get(target_id, 0) + amount
        await update.message.reply_text(f"✅ ইউজার `{target_id}`-কে {amount} TK দেওয়া হয়েছে।", parse_mode="Markdown")
        try:
            await context.bot.send_message(chat_id=target_id, text=f"💰 আপনার অ্যাকাউন্টে **{amount} টাকা** যোগ করা হয়েছে।", parse_mode="Markdown")
        except: pass
    except:
        await update.message.reply_text("❌ সঠিক ফরম্যাট: `/addbalance USER_ID AMOUNT`", parse_mode="Markdown")

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID: 
        return
    msg = " ".join(context.args)
    if not msg:
        await update.message.reply_text("❌ মেসেজ টাইপ করুন!", parse_mode="Markdown")
        return
    count = 0
    for uid in all_users:
        try:
            await context.bot.send_message(chat_id=uid, text=f"📢 **বিজ্ঞপ্তি:**\n\n{msg}", parse_mode="Markdown")
            count += 1
        except: 
            pass
    await update.message.reply_text(f"✅ মোট {count} জন ইউজারের কাছে নোটিশ পাঠানো হয়েছে।")

if __name__ == '__main__':
    TOKEN = "8948370050:AAFqFGKbyrZrFZ-fhdvPXhtd25GX3Nw_OcE"
    
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("earn", lambda u, c: earn_handler(u, c)))
    app.add_handler(CommandHandler("account", lambda u, c: account_handler(u, c)))
    app.add_handler(CommandHandler("withdraw", lambda u, c: withdraw_handler(u, c)))
    app.add_handler(CommandHandler("setwallet", lambda u, c: setwallet_handler(u, c)))
    app.add_handler(CommandHandler("refer", lambda u, c: refer_handler(u, c)))
    app.add_handler(CommandHandler("support", lambda u, c: support_handler(u, c)))
    app.add_handler(CommandHandler("addbalance", add_balance_command))
    app.add_handler(CommandHandler("activate", activate_user_command))
    app.add_handler(CommandHandler("broadcast", broadcast_command))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.PHOTO | (filters.TEXT & ~filters.COMMAND), handle_message))

    print("প্রফেশনাল ডিজাইনসহ বট সফলভাবে চালু হচ্ছে...")
    app.run_polling(drop_pending_updates=True)
