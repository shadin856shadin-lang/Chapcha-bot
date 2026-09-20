import os
import random
import string
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import quote
from PIL import Image, ImageDraw, ImageFont
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
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
AD_REWARD = 4.0  # আপাতত এ্যাড বন্ধ রাখা হয়েছে

GROUP_1 = "@Captchabotsupportgroup"
GROUP_2 = "@captchaearnofficial"

user_captchas = {}
user_balances = {}
user_wallets = {}
user_wallet_types = {}
user_total_withdrawn = {}
user_referral_counts = {}
user_is_active = {}
referred_by = {}
all_users = set()
pending_withdrawals = {}

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
        [InlineKeyboardButton("📢 Join Support Group", url="https://t.me/Captchabotsupportgroup")],
        [InlineKeyboardButton("📢 Join Payment Group", url="https://t.me/captchaearnofficial")],
        [InlineKeyboardButton("✅ I've Joined – Verify", callback_data="check_join")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    msg = (
        "⚡ **QuickCash Captcha Bot**\n"
        "----------------------------------------\n"
        "🔒 **বটে কাজ করতে হলে নিচের গ্রুপগুলোতে জয়েন করুন!**\n\n"
        "📢 জয়েন করার পর নিচের অফিসিয়াল **'I've Joined – Verify'** বাটনে ক্লিক করুন."
    )
    if update.message:
        await update.message.reply_text(msg, reply_markup=reply_markup, parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.message.reply_text(msg, reply_markup=reply_markup, parse_mode="Markdown")

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
        user_balances[user_id] = 0.0
        user_is_active[user_id] = False
        user_total_withdrawn[user_id] = 0.0
        user_referral_counts[user_id] = 0

    if context.args:
        try:
            referrer_id = int(context.args[0])
            if referrer_id != user_id and referrer_id not in referred_by.get(user_id, []):
                referred_by[user_id] = referrer_id
                user_balances[referrer_id] = user_balances.get(referrer_id, 0) + REFER_BONUS
                user_referral_counts[referrer_id] = user_referral_counts.get(referrer_id, 0) + 1
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

    if user_id == ADMIN_ID:
        keyboard = [
            ['💸 Withdraw', '🚀 Capcha Earn'],
            ['📢 Watch Ad', '💰 Balance'],
            ['☎️ Support', '👑 Admin Panel']
        ]
    else:
        keyboard = [
            ['💸 Withdraw', '🚀 Capcha Earn'],
            ['📢 Watch Ad', '💰 Balance'],
            ['☎️ Support']
        ]

    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    welcome_msg = (
        "⚡ **QuickCash Captcha Bot**\n"
        "----------------------------------------\n"
        f"🔒 **Welcome, {user_name}!**\n\n"
        "✅ ঘরে বসে সহজে ক্যাপচা ও এড দেখে ইনকাম করুন\n"
        "🔔 সঠিক ক্যাপচা বা এড ভিউয়ে ইনস্ট্যান্ট ব্যালেন্স যোগ হবে\n"
        "🎉 বন্ধুদের রেফার করে আকর্ষণীয় বোনাস পান\n"
        "----------------------------------------\n"
        "⚡ **কাজ শুরু করতে নিচের অপশনগুলোতে ক্লিক করুন!**"
    )

    target_msg = update.message if update.message else update.callback_query.message
    await target_msg.reply_text(welcome_msg, reply_markup=reply_markup, parse_mode="Markdown")

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
        await query.message.reply_text("❌ আপনি এখনো সবগুলোতে জয়েন করেননি! দয়া করে জয়েন হয়ে আবার **'I've Joined – Verify'** বাটনে ক্লিক করুন.", parse_mode="Markdown")

async def earn_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    all_users.add(user_id)
    
    captcha_text = generate_captcha_text()
    user_captchas[user_id] = captcha_text
    img_path = generate_captcha_image(captcha_text)
    
    target_msg = update.message if update.message else update.callback_query.message
    with open(img_path, 'rb') as photo:
        await target_msg.reply_photo(
            photo=photo,
            caption="🖼 **উপরে ছবিতে থাকা কোডটি দেখে নিচে লিখে পাঠান:**"
        )

async def watch_ad_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    all_users.add(user_id)
    
    text = (
        "🚀 **Ad is coming soon!**\n\n"
        "খুব শীঘ্রই নতুন বিজ্ঞাপন যুক্ত করা হবে। ততদিন পর্যন্ত ক্যাপচা পূরণ করে এবং বন্ধুদের রেফার করে ইনকাম করুন।"
    )
    
    target_msg = update.message if update.message else update.callback_query.message
    if update.callback_query:
        await update.callback_query.answer("Ad is coming soon!", show_alert=True)
    await target_msg.reply_text(text, parse_mode="Markdown")

async def balance_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    all_users.add(user_id)
    
    balance = user_balances.get(user_id, 0.0)
    ref_count = user_referral_counts.get(user_id, 0)
    bot_username = context.bot.username
    refer_link = f"https://t.me/{bot_username}?start={user_id}"
    
    share_text = quote(f"ঘরে বসে সহজেই ক্যাপচা ও এড দেখে টাকা ইনকাম করুন! আমার রেফারেল লিংক থেকে জয়েন করুন:\n{refer_link}")
    share_url = f"https://t.me/share/url?url={quote(refer_link)}&text={share_text}"

    text = (
        f"👥 **রেফার করুন ও ইনকাম করুন**\n\n"
        f"💰 **আপনার ব্যালেন্স:** {balance:.2f}৳\n"
        f"👤 **মোট রেফার:** {ref_count} জন\n\n"
        f"🔗 **আপনার রেফারেল লিংক:**\n`{refer_link}`\n\n"
        f"📌 আপনি যাকে রেফার করবেন সে যদি Bot start করে তাহলে আপনি পাবেন ৫ টাকা।\n\n"
        f"💸 **প্রতি রেফারে পাবেন ৫ টাকা**\n\n"
        f"🔥 তাই বেশি ইনকাম করতে চাইলে বেশি বেশি রেফার করুন!"
    )

    keyboard = [
        [InlineKeyboardButton("📤 Share Link", url=share_url)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    target_msg = update.message if update.message else update.callback_query.message
    await target_msg.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

async def withdraw_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    all_users.add(user_id)
    
    wallet = user_wallets.get(user_id)
    target_msg = update.message if update.message else update.callback_query.message
    
    balance = user_balances.get(user_id, 0.0)
    total_w = user_total_withdrawn.get(user_id, 0.0)
    ref_count = user_referral_counts.get(user_id, 0)
    ref_reward_total = ref_count * REFER_BONUS
    
    wallet_status = f"{user_wallet_types.get(user_id, 'Wallet')}: {wallet}" if wallet else "সেট করা হয়নি"

    text = (
        f"Wallet\n"
        f"-----------------------\n"
        f"User ID: `{user_id}`\n\n"
        f"Balance: {balance:.2f}৳\n\n"
        f"Total Withdrawn: {total_w:.2f}৳\n\n"
        f"Referrals: {ref_count}\n\n"
        f"Refer Reward: {ref_reward_total:.2f}৳\n"
        f"---------------------------------\n"
        f"📌 Minimum Withdraw: {MIN_WITHDRAW:.2f}৳\n\n"
        f"⚡ Fee: Free 0%\n"
        f"-----------------------------------\n"
        f"Wallet: {wallet_status}"
    )

    if not wallet:
        keyboard = [
            [InlineKeyboardButton("💳 Set Wallet", callback_data="btn_setwallet"), InlineKeyboardButton("💸 Withdraw", callback_data="btn_withdraw_check")]
        ]
    else:
        keyboard = [
            [InlineKeyboardButton("💳 Change Wallet", callback_data="btn_setwallet"), InlineKeyboardButton("💸 Withdraw", callback_data="btn_withdraw_check")]
        ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await target_msg.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

async def support_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    all_users.add(user_id)
    
    support_keyboard = [
        [InlineKeyboardButton("💬 Contact Admin", url=f"https://t.me/{ADMIN_USERNAME}")],
        [InlineKeyboardButton("💳 Payment Group", url="https://t.me/captchaearnofficial")],
        [InlineKeyboardButton("👥 Support Group", url="https://t.me/Captchabotsupportgroup")]
    ]
    reply_markup = InlineKeyboardMarkup(support_keyboard)
    msg = update.message if update.message else update.callback_query.message
    await msg.reply_text(
        "👨‍💻 **এডমিন সাপোর্ট ও কমিউনিটি প্যানেল:**\n\n"
        "যেকোনো সমস্যায় সরাসরি এডমিনের সাথে যোগাযোগ করুন অথবা আমাদের পেমেন্ট ও সাপোর্ট গ্রুপে যুক্ত থাকুন:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def admin_panel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return
    total_users = len(all_users)
    
    admin_text = (
        f"👑 **এডমিন প্যানেল**\n\n"
        f"📊 মোট ইউজার: {total_users} জন\n"
        f"📌 পেন্ডিং উইথড্র রিকোয়েস্ট: {len(pending_withdrawals)} টি\n\n"
        "**কমান্ডসমূহ:**\n"
        "1. আইডি অ্যাক্টিভ করতে: `/activate USER_ID`\n"
        "2. ব্যালেন্স দিতে: `/addbalance USER_ID AMOUNT`\n"
        "3. উইথড্র এপ্রুভ করতে: `/approve USER_ID`\n"
        "4. ব্রডকাস্ট করতে: `/broadcast মেসেজ`"
    )
    
    keyboard = []
    for uid, data in pending_withdrawals.items():
        if data['status'] == "Processing":
            keyboard.append([InlineKeyboardButton(f"✅ Approve {uid} ({data['amount']}৳)", callback_data=f"app_{uid}")])
    
    target_msg = update.message if update.message else update.callback_query.message
    if keyboard:
        reply_markup = InlineKeyboardMarkup(keyboard)
        await target_msg.reply_text(admin_text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await target_msg.reply_text(admin_text, parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or update.message.chat.type != 'private':
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

    if text in ["🚀 Capcha Earn", "Capcha Earn", "Earn", "/earn"]:
        context.user_data['waiting_for_wallet_input'] = None
        context.user_data['waiting_for_withdraw_amount'] = False
        await earn_handler(update, context)
        return
    elif text in ["📢 Watch Ad", "Watch Ad", "/ad"]:
        context.user_data['waiting_for_wallet_input'] = None
        context.user_data['waiting_for_withdraw_amount'] = False
        await watch_ad_handler(update, context)
        return
    elif text in ["💰 Balance", "Balance", "/balance"]:
        context.user_data['waiting_for_wallet_input'] = None
        context.user_data['waiting_for_withdraw_amount'] = False
        await balance_handler(update, context)
        return
    elif text in ["💸 Withdraw", "Withdraw", "/withdraw"]:
        context.user_data['waiting_for_wallet_input'] = None
        await withdraw_handler(update, context)
        return
    elif text in ["☎️ Support", "Support", "/support"]:
        context.user_data['waiting_for_wallet_input'] = None
        context.user_data['waiting_for_withdraw_amount'] = False
        await support_handler(update, context)
        return
    elif text in ["👑 Admin Panel", "Admin Panel", "/admin"] and user_id == ADMIN_ID:
        context.user_data['waiting_for_wallet_input'] = None
        context.user_data['waiting_for_withdraw_amount'] = False
        await admin_panel_handler(update, context)
        return

    if context.user_data.get('waiting_for_wallet_input'):
        w_method = context.user_data['waiting_for_wallet_input']
        user_wallets[user_id] = text
        user_wallet_types[user_id] = w_method
        context.user_data['waiting_for_wallet_input'] = None
        await update.message.reply_text(
            f"🎉 **অভিনন্দন! আপনার {w_method.lower()} নাম্বার যোগ হয়েছে।**\n\n"
            f"নাম্বার: `{text}`",
            parse_mode="Markdown"
        )
        return

    if context.user_data.get('waiting_for_withdraw_amount'):
        context.user_data['waiting_for_withdraw_amount'] = False
        try:
            amount = float(text)
            balance = user_balances.get(user_id, 0.0)
            wallet = user_wallets.get(user_id)

            if not wallet:
                await update.message.reply_text("❌ আপনার বিকাশ/নগদ/রকেট নাম্বার সেট করা নেই! আগে Withdraw বাটনে ক্লিক করে নাম্বার দিন।")
                return

            if amount < MIN_WITHDRAW or amount > balance:
                await update.message.reply_text("❌ আপনার একাউন্টে পর্যাপ্ত ব্যালেন্স নাই বা সর্বনিম্ন উইথড্র এমাউন্ট হয়নি।", parse_mode="Markdown")
                return

            is_active = user_is_active.get(user_id, False)
            if not is_active:
                msg = (
                    f"❌ **আপনার একাউন্ট একটিভ নয়।**\n\n"
                    f"একাউন্ট একটিভ করবার জন্য নিচের দেওয়া নাম্বারে **৩০ টাকা** সেন্ড মানি করুন:\n"
                    f"📱 `{ADMIN_BKASH}` (বিকাশ/নগদ)\n\n"
                    f"টাকা পাঠিয়ে স্কিনশট এবং ট্রানজেকশন আইডি এডমিন এর ইনবক্সে দিন। এডমিন একাউন্ট একটিভ করার পর উইথড্র করতে পারবেন।"
                )
                await update.message.reply_text(msg, parse_mode="Markdown")
                return

            user_balances[user_id] = balance - amount
            user_total_withdrawn[user_id] = user_total_withdrawn.get(user_id, 0.0) + amount
            w_type = user_wallet_types.get(user_id, "Wallet")
            
            pending_withdrawals[user_id] = {
                "amount": amount,
                "wallet": f"{w_type}: {wallet}",
                "status": "Processing"
            }

            await update.message.reply_text(
                f"⏳ **দয়া করে অপেক্ষা করুন।**\n\n"
                f"💸 এমাউন্ট: {amount} TK\n"
                f"💳 নাম্বার: `{wallet}`\n"
                f"📊 স্ট্যাটাস: **Processing...**",
                parse_mode="Markdown"
            )
        except ValueError:
            await update.message.reply_text("❌ সঠিক সংখ্যায় এমাউন্ট লিখে পাঠান (যেমন: 50 বা 100)।")
        return

    if user_id in user_captchas:
        correct_captcha = user_captchas[user_id]
        if text.upper() == correct_captcha.upper():
            user_balances[user_id] = user_balances.get(user_id, 0.0) + 2.0
            del user_captchas[user_id]
            await update.message.reply_text("✅ **সঠিক হয়েছে! ২ টাকা আপনার অ্যাকাউন্টে যোগ হয়েছে।**", parse_mode="Markdown")
        else:
            await update.message.reply_text("❌ **ভুল ক্যাপচা! আবার চেষ্টা করুন।**", parse_mode="Markdown")
        return

    await update.message.reply_text("দয়া করে নিচের মেনু থেকে কোনো একটি অপশন বেছে নিন।")

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass

    user_id = query.from_user.id
    
    if query.data == "check_join":
        await verify_button(update, context)
        return

    if query.data == "btn_setwallet":
        keyboard = [
            [InlineKeyboardButton("📱 bKash", callback_data="wallet_bkash"), InlineKeyboardButton("🟠 Nagad", callback_data="wallet_nagad")],
            [InlineKeyboardButton("🟣 Rocket", callback_data="wallet_rocket")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        try:
            await query.message.reply_text("💳 **আপনার পেমেন্ট সিস্টেম সিলেক্ট করুন:**", reply_markup=reply_markup, parse_mode="Markdown")
        except Exception as e:
            print(f"Error in btn_setwallet: {e}")
        return

    if query.data == "btn_withdraw_check":
        wallet = user_wallets.get(user_id)
        if not wallet:
            try:
                await query.message.reply_text("❌ আগে 'Set Wallet' এ ক্লিক করে আপনার বিকাশ/নগদ/রকেট নাম্বার সেট করুন।", parse_mode="Markdown")
            except Exception as e:
                print(f"Error sending wallet missing msg: {e}")
            return
        
        context.user_data['waiting_for_withdraw_amount'] = True
        w_type = user_wallet_types.get(user_id, "Wallet")
        try:
            await query.message.reply_text(
                f"💵 **আপনি কত টাকা withdraw করতে চান??**\n\n"
                f"💳 To: {w_type}: {wallet}\n"
                f"📉 Minimum: {MIN_WITHDRAW:.2f}৳",
                parse_mode="Markdown"
            )
        except Exception as e:
            print(f"Error in btn_withdraw_check: {e}")
        return

    if query.data == "wallet_bkash":
        context.user_data['waiting_for_wallet_input'] = "bKash"
        try:
            await query.message.reply_text("📱 আপনার বিকাশ নাম্বার লিখুন:", parse_mode="Markdown")
        except:
            pass
        return

    if query.data == "wallet_nagad":
        context.user_data['waiting_for_wallet_input'] = "Nagad"
        try:
            await query.message.reply_text("🟠 আপনার নগদ নাম্বার লিখুন:", parse_mode="Markdown")
        except:
            pass
        return

    if query.data == "wallet_rocket":
        context.user_data['waiting_for_wallet_input'] = "Rocket"
        try:
            await query.message.reply_text("🟣 আপনার রকেট নাম্বার লিখুন:", parse_mode="Markdown")
        except:
            pass
        return

    if query.data.startswith("app_") and user_id == ADMIN_ID:
        target_uid = int(query.data.split("_")[1])
        if target_uid in pending_withdrawals:
            pending_withdrawals[target_uid]['status'] = "Approved ✅"
            amt = pending_withdrawals[target_uid]['amount']
            wlt = pending_withdrawals[target_uid]['wallet']
            
            try:
                await context.bot.send_message(
                    chat_id=target_uid,
                    text=f"🎉 **আপনার উইথড্র রিকোয়েস্ট সফলভাবে এপ্রুভ করা হয়েছে!**\n\n"
                         f"💸 এমাউন্ট: {amt} TK\n"
                         f"💳 মাধ্যম: {wlt}\n"
                         f"📊 স্ট্যাটাস: **Approved ✅**\n\n"
                         f"খুব শীঘ্রই আপনার নাম্বার চেক করুন."
                )
            except:
                pass
            
            try:
                await query.edit_message_text(f"✅ ইউজার `{target_uid}`-এর উইথড্র সফলভাবে এপ্রুভ করা হয়েছে।", parse_mode="Markdown")
            except:
                pass
        return

    if user_id != ADMIN_ID:
        return

    photo = context.user_data.get('pending_photo')
    caption = context.user_data.get('pending_caption', '')
    if not photo:
        try:
            await query.edit_message_text("❌ ছবির সময়সীমা শেষ হয়ে গেছে বা ছবি পাওয়া যায়নি।")
        except:
            pass
        return

    target = GROUP_1 if query.data == "post_g1" else GROUP_2
    try:
        await context.bot.send_photo(chat_id=target, photo=photo, caption=caption)
        await query.edit_message_text("✅ সফলভাবে নির্দিষ্ট গ্রুপে পোস্ট করা হয়েছে!")
    except Exception as e:
        try:
            await query.edit_message_text(f"❌ ত্রুটি দেখা দিয়েছে: {e}")
        except:
            pass

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
            await context.bot.send_message(chat_id=target_id, text="🎉 **অভিনন্দন! আপনার অ্যাকাউন্ট সফলভাবে অ্যাক্টিভ করা হয়েছে। এখন থেকে আপনি উইথড্র করতে পারবেন।**", parse_mode="Markdown")
        except: pass
    except:
        await update.message.reply_text("❌ সঠিক ফরম্যাট: `/activate USER_ID`", parse_mode="Markdown")

async def approve_withdraw_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID: return
    try:
        target_id = int(context.args[0])
        if target_id in pending_withdrawals:
            pending_withdrawals[target_id]['status'] = "Approved ✅"
            amt = pending_withdrawals[target_id]['amount']
            wlt = pending_withdrawals[target_id]['wallet']
            
            await update.message.reply_text(f"✅ ইউজার `{target_id}`-এর উইথড্র এপ্রুভ করা হয়েছে।", parse_mode="Markdown")
            try:
                await context.bot.send_message(
                    chat_id=target_id,
                    text=f"🎉 **আপনার উইথড্র রিকোয়েস্ট সফলভাবে এপ্রুভ করা হয়েছে!**\n\n"
                         f"💸 এমাউন্ট: {amt} TK\n"
                         f"💳 মাধ্যম: {wlt}\n"
                         f"📊 স্ট্যাটাস: **Approved ✅**"
                )
            except: pass
        else:
            await update.message.reply_text("❌ এই ইউজারের কোনো পেন্ডিং উইথড্র নেই।")
    except:
        await update.message.reply_text("❌ সঠিক ফরম্যাট: `/approve USER_ID`", parse_mode="Markdown")

async def add_balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID: return
    try:
        target_id = int(context.args[0])
        amount = float(context.args[1])
        user_balances[target_id] = user_balances.get(target_id, 0.0) + amount
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
    app.add_handler(CommandHandler("earn", earn_handler))
    app.add_handler(CommandHandler("ad", watch_ad_handler))
    app.add_handler(CommandHandler("balance", balance_handler))
    app.add_handler(CommandHandler("withdraw", withdraw_handler))
    app.add_handler(CommandHandler("support", support_handler))
    app.add_handler(CommandHandler("addbalance", add_balance_command))
    app.add_handler(CommandHandler("activate", activate_user_command))
    app.add_handler(CommandHandler("approve", approve_withdraw_command))
    app.add_handler(CommandHandler("broadcast", broadcast_command))
    
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.PHOTO | (filters.TEXT & ~filters.COMMAND), handle_message))

    print("বট সফলভাবে চালু হচ্ছে...")
    app.run_polling(drop_pending_updates=True)
