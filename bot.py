import os
import random
import string
import sqlite3
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import quote

from PIL import Image, ImageDraw, ImageFont
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# =========================================================
# CONFIG
# =========================================================

ADMIN_ID = 8262339619  # আপনার টেলিগ্রাম আইডি
ADMIN_USERNAME = "Ownertanvir99"  # @ ছাড়া ইউজারনেম

GROUP_1 = os.getenv("GROUP_1", "@Captchabotsupportgroup")
GROUP_2 = os.getenv("GROUP_2", "@captchaearnofficial")

REFER_BONUS = 5.0
CAPTCHA_REWARD = 2.0
MIN_WITHDRAW = 50.0

PORT = int(os.getenv("PORT", "10000"))
DB_FILE = "bot.db"

# =========================================================
# MINI WEB SERVER FOR HOSTING (Render etc.)
# =========================================================

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"QuickCash Captcha Bot is running!")

    def log_message(self, format, *args):
        return


def run_server():
    server = HTTPServer(("0.0.0.0", PORT), SimpleHandler)
    server.serve_forever()


threading.Thread(target=run_server, daemon=True).start()

# =========================================================
# DATABASE
# =========================================================

db_lock = threading.Lock()


def db():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with db_lock:
        conn = db()
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                balance REAL DEFAULT 0,
                total_withdrawn REAL DEFAULT 0,
                referral_count INTEGER DEFAULT 0,
                wallet_type TEXT DEFAULT '',
                wallet_number TEXT DEFAULT '',
                is_active INTEGER DEFAULT 0,
                referred_by INTEGER DEFAULT NULL
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS withdrawals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                wallet_type TEXT NOT NULL,
                wallet_number TEXT NOT NULL,
                status TEXT DEFAULT 'Processing',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()


init_db()

# =========================================================
# USER HELPERS
# =========================================================

def ensure_user(user_id: int):
    with db_lock:
        conn = db()
        conn.execute(
            "INSERT OR IGNORE INTO users (user_id) VALUES (?)",
            (user_id,),
        )
        conn.commit()
        conn.close()


def get_user(user_id: int):
    ensure_user(user_id)
    with db_lock:
        conn = db()
        row = conn.execute(
            "SELECT * FROM users WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        conn.close()
        return row


def get_all_user_ids():
    with db_lock:
        conn = db()
        rows = conn.execute("SELECT user_id FROM users").fetchall()
        conn.close()
        return [row["user_id"] for row in rows]


def update_user(user_id: int, **fields):
    if not fields:
        return

    ensure_user(user_id)

    allowed = {
        "balance",
        "total_withdrawn",
        "referral_count",
        "wallet_type",
        "wallet_number",
        "is_active",
        "referred_by",
    }

    fields = {k: v for k, v in fields.items() if k in allowed}
    if not fields:
        return

    parts = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [user_id]

    with db_lock:
        conn = db()
        conn.execute(
            f"UPDATE users SET {parts} WHERE user_id = ?",
            values,
        )
        conn.commit()
        conn.close()


# =========================================================
# CAPTCHA
# =========================================================

user_captchas = {}


def generate_captcha_text():
    return "".join(
        random.choices(string.ascii_uppercase + string.digits, k=5)
    )


def generate_captcha_image(text, user_id):
    width, height = 260, 90
    image = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)

    for _ in range(8):
        x1 = random.randint(0, width)
        y1 = random.randint(0, height)
        x2 = random.randint(0, width)
        y2 = random.randint(0, height)
        draw.line(
            [x1, y1, x2, y2],
            fill=(180, 180, 180),
            width=2,
        )

    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 42)
    except Exception:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    x = (width - text_width) // 2
    y = (height - text_height) // 2 - 5

    draw.text(
        (x, y),
        text,
        fill=(0, 0, 0),
        font=font,
    )

    path = f"captcha_{user_id}.png"
    image.save(path)
    return path


# =========================================================
# MEMBERSHIP
# =========================================================

async def check_membership(user_id: int, context):
    if user_id == ADMIN_ID:
        return True

    try:
        member1 = await context.bot.get_chat_member(
            chat_id=GROUP_1,
            user_id=user_id,
        )
        member2 = await context.bot.get_chat_member(
            chat_id=GROUP_2,
            user_id=user_id,
        )

        valid_status = {
            "creator",
            "administrator",
            "member",
        }

        return (
            member1.status in valid_status
            and member2.status in valid_status
        )

    except Exception as e:
        print("Membership check error:", e)
        return False


async def send_join_request(update, context):
    keyboard = [
        [
            InlineKeyboardButton(
                "📢 Join Support Group",
                url="https://t.me/Captchabotsupportgroup",
            )
        ],
        [
            InlineKeyboardButton(
                "📢 Join Payment Group",
                url="https://t.me/captchaearnofficial",
            )
        ],
        [
            InlineKeyboardButton(
                "✅ I've Joined – Verify",
                callback_data="check_join",
            )
        ],
    ]

    markup = InlineKeyboardMarkup(keyboard)

    msg = (
        "⚡ *QuickCash Captcha Bot*\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "🔒 *বটে কাজ করতে হলে নিচের গ্রুপগুলোতে জয়েন করুন!*\n\n"
        "📢 জয়েন করার পর *I've Joined – Verify* বাটনে ক্লিক করুন।"
    )

    target = update.message or update.callback_query.message

    await target.reply_text(
        msg,
        reply_markup=markup,
        parse_mode="Markdown",
    )


# =========================================================
# START
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.chat.type != "private":
        return

    user_id = update.effective_user.id
    first_name = update.effective_user.first_name or "User"

    if not await check_membership(user_id, context):
        await send_join_request(update, context)
        return

    ensure_user(user_id)

    # Referral handling
    if context.args:
        try:
            referrer_id = int(context.args[0])
            current = get_user(user_id)

            if (
                referrer_id != user_id
                and current["referred_by"] is None
            ):
                ensure_user(referrer_id)
                referrer = get_user(referrer_id)

                update_user(
                    user_id,
                    referred_by=referrer_id,
                )

                update_user(
                    referrer_id,
                    balance=referrer["balance"] + REFER_BONUS,
                    referral_count=referrer["referral_count"] + 1,
                )

                try:
                    await context.bot.send_message(
                        chat_id=referrer_id,
                        text=(
                            "🎉 *নতুন রেফারেল বোনাস!*\n\n"
                            f"আপনি পেয়েছেন *{REFER_BONUS:.2f}৳*।"
                        ),
                        parse_mode="Markdown",
                    )
                except Exception:
                    pass

        except ValueError:
            pass

    keyboard = [
        ["🚀 Capcha Earn", "📢 Watch Ad"],
        ["💰 Balance", "💸 Withdraw"],
        ["☎️ Support"],
    ]

    if user_id == ADMIN_ID:
        keyboard[-1].append("👑 Admin Panel")

    markup = ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
    )

    welcome = (
        "⚡ *QuickCash Captcha Bot*\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🔒 *Welcome, {first_name}!*\n\n"
        "✅ ক্যাপচা পূরণ করে রিওয়ার্ড সংগ্রহ করুন\n"
        "🎉 বন্ধুদের রেফার করে বোনাস পান\n"
        "💰 ব্যালেন্স ও withdrawal status দেখুন\n\n"
        "⚡ *কাজ শুরু করতে নিচের অপশন নির্বাচন করুন.ன்*"
    )

    target = update.message or update.callback_query.message

    await target.reply_text(
        welcome,
        reply_markup=markup,
        parse_mode="Markdown",
    )


# =========================================================
# EARN
# =========================================================

async def earn_handler(update, context):
    user_id = update.effective_user.id
    ensure_user(user_id)

    captcha = generate_captcha_text()
    user_captchas[user_id] = captcha

    path = generate_captcha_image(captcha, user_id)
    target = update.message or update.callback_query.message

    try:
        with open(path, "rb") as photo:
            await target.reply_photo(
                photo=photo,
                caption="🖼 *ছবির কোডটি দেখে নিচে লিখে পাঠান:*",
                parse_mode="Markdown",
            )
    finally:
        try:
            os.remove(path)
        except Exception:
            pass


# =========================================================
# WATCH AD
# =========================================================

async def watch_ad_handler(update, context):
    target = update.message or update.callback_query.message

    await target.reply_text(
        "🚀 *Ad is coming soon!*\n\n"
        "খুব শীঘ্রই বিজ্ঞাপন যুক্ত করা হবে।\n"
        "বর্তমানে CAPTCHA ও referral ব্যবহার করতে পারেন।",
        parse_mode="Markdown",
    )


# =========================================================
# BALANCE
# =========================================================

async def balance_handler(update, context):
    user_id = update.effective_user.id
    ensure_user(user_id)

    user = get_user(user_id)
    bot_username = context.bot.username

    refer_link = f"https://t.me/{bot_username}?start={user_id}"

    share_text = quote(
        "ঘরে বসে সহজে CAPTCHA reward সংগ্রহ করুন! "
        "আমার referral link থেকে join করুন:\n"
        f"{refer_link}"
    )

    share_url = (
        "https://t.me/share/url?"
        f"url={quote(refer_link)}&text={share_text}"
    )

    text = (
        "👥 *রেফার করুন ও বোনাস পান*\n\n"
        f"💰 *আপনার ব্যালেন্স:* {user['balance']:.2f}৳\n"
        f"👤 *মোট রেফার:* {user['referral_count']} জন\n\n"
        "🔗 *আপনার Referral Link:*\n"
        f"`{refer_link}`\n\n"
        f"💸 *প্রতি referral:* {REFER_BONUS:.2f}৳"
    )

    markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "📤 Share Link",
                url=share_url,
            )
        ]
    ])

    target = update.message or update.callback_query.message

    await target.reply_text(
        text,
        reply_markup=markup,
        parse_mode="Markdown",
    )


# =========================================================
# WITHDRAW PAGE
# =========================================================

async def withdraw_handler(update, context):
    user_id = update.effective_user.id
    ensure_user(user_id)

    user = get_user(user_id)
    wallet_display = "সেট করা হয়নি"

    if user["wallet_number"]:
        wallet_display = (
            f"{user['wallet_type']}: "
            f"{user['wallet_number']}"
        )

    text = (
        "💸 *Wallet*\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"👤 User ID: `{user_id}`\n\n"
        f"💰 Balance: *{user['balance']:.2f}৳*\n\n"
        f"💵 Total Withdrawn: "
        f"*{user['total_withdrawn']:.2f}৳*\n\n"
        f"👥 Referrals: *{user['referral_count']}*\n\n"
        f"🎁 Referral Reward: "
        f"*{user['referral_count'] * REFER_BONUS:.2f}৳*\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"📉 Minimum Withdraw: *{MIN_WITHDRAW:.2f}৳*\n\n"
        "💳 Fee: *0%*\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🏦 Wallet: *{wallet_display}*"
    )

    keyboard = [
        [
            InlineKeyboardButton(
                "⚙️ Set Wallet",
                callback_data="btn_setwallet",
            ),
            InlineKeyboardButton(
                "💸 Withdraw",
                callback_data="btn_process_withdraw",
            ),
        ]
    ]

    target = update.message or update.callback_query.message

    await target.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


# =========================================================
# SUPPORT
# =========================================================

async def support_handler(update, context):
    keyboard = [
        [
            InlineKeyboardButton(
                "💬 Contact Admin",
                url=f"https://t.me/{ADMIN_USERNAME}",
            )
        ],
        [
            InlineKeyboardButton(
                "💳 Payment Group",
                url="https://t.me/captchaearnofficial",
            )
        ],
        [
            InlineKeyboardButton(
                "👥 Support Group",
                url="https://t.me/Captchabotsupportgroup",
            )
        ],
    ]

    target = update.message or update.callback_query.message

    await target.reply_text(
        "👨‍💻 *Admin Support & Community*\n\n"
        "যেকোনো সমস্যায় Admin-এর সাথে যোগাযোগ করুন।",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


# =========================================================
# ADMIN PANEL
# =========================================================

async def admin_panel_handler(update, context):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return

    total_users = len(get_all_user_ids())

    with db_lock:
        conn = db()
        pending = conn.execute(
            "SELECT COUNT(*) AS c FROM withdrawals "
            "WHERE status = 'Processing'"
        ).fetchone()["c"]
        conn.close()

    text = (
        "👑 *Admin Panel*\n\n"
        f"📊 Total Users: {total_users}\n"
        f"📌 Pending Withdrawals: {pending}\n\n"
        "*Commands:*\n"
        "`/activate USER_ID`\n"
        "`/addbalance USER_ID AMOUNT`\n"
        "`/success WITHDRAWAL_ID`\n"
        "`/broadcast MESSAGE`"
    )

    await update.message.reply_text(
        text,
        parse_mode="Markdown",
    )


# =========================================================
# MAIN MESSAGE HANDLER
# =========================================================

async def handle_message(update, context):
    if not update.message:
        return

    if update.message.chat.type != "private":
        return

    user_id = update.effective_user.id
    ensure_user(user_id)

    # Admin photo broadcast handler
    if update.message.photo and user_id == ADMIN_ID:
        caption = update.message.caption or "Payment proof / update"
        context.user_data["pending_photo"] = (
            update.message.photo[-1].file_id
        )
        context.user_data["pending_caption"] = caption

        keyboard = [
            [
                InlineKeyboardButton(
                    "📢 Group 1",
                    callback_data="post_g1",
                )
            ],
            [
                InlineKeyboardButton(
                    "📢 Group 2",
                    callback_data="post_g2",
                )
            ],
        ]

        await update.message.reply_text(
            "🖼️ ছবি পাওয়া গেছে। কোথায় পোস্ট করবেন?",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    if not update.message.text:
        return

    text = update.message.text.strip()

    # Menu clicks
    if text in ["🚀 Capcha Earn", "Capcha Earn", "Earn", "/earn"]:
        context.user_data["waiting_for_wallet_input"] = None
        context.user_data["waiting_for_withdraw_amount"] = False
        await earn_handler(update, context)
        return

    if text in ["📢 Watch Ad", "Watch Ad", "/ad"]:
        context.user_data["waiting_for_wallet_input"] = None
        context.user_data["waiting_for_withdraw_amount"] = False
        await watch_ad_handler(update, context)
        return

    if text in ["💰 Balance", "Balance", "/balance"]:
        context.user_data["waiting_for_wallet_input"] = None
        context.user_data["waiting_for_withdraw_amount"] = False
        await balance_handler(update, context)
        return

    if text in ["💸 Withdraw", "Withdraw", "/withdraw"]:
        context.user_data["waiting_for_wallet_input"] = None
        context.user_data["waiting_for_withdraw_amount"] = False
        await withdraw_handler(update, context)
        return

    if text in ["☎️ Support", "Support", "/support"]:
        context.user_data["waiting_for_wallet_input"] = None
        context.user_data["waiting_for_withdraw_amount"] = False
        await support_handler(update, context)
        return

    if text in ["👑 Admin Panel", "Admin Panel", "/admin"] and user_id == ADMIN_ID:
        context.user_data["waiting_for_wallet_input"] = None
        context.user_data["waiting_for_withdraw_amount"] = False
        await admin_panel_handler(update, context)
        return

    # Wallet input step
    wallet_method = context.user_data.get("waiting_for_wallet_input")
    if wallet_method:
        wallet_number = text.replace(" ", "")

        if not wallet_number.isdigit() or len(wallet_number) != 11:
            await update.message.reply_text(
                "❌ সঠিক ১১ সংখ্যার মোবাইল নাম্বার দিন।"
            )
            return

        update_user(
            user_id,
            wallet_type=wallet_method,
            wallet_number=wallet_number,
        )

        context.user_data["waiting_for_wallet_input"] = None

        await update.message.reply_text(
            "✅ *Wallet Set Successfully!*\n\n"
            f"💳 Method: *{wallet_method}*\n"
            f"📱 Number: `{wallet_number}`\n\n"
            "এখন আপনি withdrawal request করতে পারবেন।",
            parse_mode="Markdown",
        )
        return

    # Withdraw amount step
    if context.user_data.get("waiting_for_withdraw_amount"):
        context.user_data["waiting_for_withdraw_amount"] = False

        try:
            amount = float(text)
        except ValueError:
            await update.message.reply_text(
                "❌ দয়া করে সঠিক সংখ্যা লিখুন।"
            )
            return

        if amount < MIN_WITHDRAW:
            await update.message.reply_text(
                f"❌ Minimum withdrawal হলো {MIN_WITHDRAW:.2f}৳।"
            )
            return

        user = get_user(user_id)

        if not user["wallet_number"]:
            await update.message.reply_text(
                "❌ প্রথমে Set Wallet থেকে আপনার wallet সেট করুন।"
            )
            return

        if user["balance"] < amount:
            await update.message.reply_text(
                f"❌ আপনার পর্যাপ্ত ব্যালেন্স নেই।\n\n"
                f"💰 বর্তমান ব্যালেন্স: {user['balance']:.2f}৳"
            )
            return

        if not user["is_active"]:
            await update.message.reply_text(
                "⏳ আপনার account এখনো withdrawal-এর জন্য "
                "admin দ্বারা activate করা হয়নি।\n\n"
                "Support থেকে admin-এর সাথে যোগাযোগ করুন।"
            )
            return

        new_balance = user["balance"] - amount
        new_total = user["total_withdrawn"] + amount

        update_user(
            user_id,
            balance=new_balance,
            total_withdrawn=new_total,
        )

        with db_lock:
            conn = db()
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO withdrawals
                (user_id, amount, wallet_type, wallet_number, status)
                VALUES (?, ?, ?, ?, 'Processing')
                """,
                (
                    user_id,
                    amount,
                    user["wallet_type"],
                    user["wallet_number"],
                ),
            )
            withdrawal_id = cur.lastrowid
            conn.commit()
            conn.close()

        await update.message.reply_text(
            "✅ *Withdrawal Request Submitted!*\n\n"
            f"🆔 Request ID: `{withdrawal_id}`\n"
            f"💸 Amount: *{amount:.2f}৳*\n"
            f"💳 Method: *{user['wallet_type']}*\n"
            f"📱 Number: `{user['wallet_number']}`\n"
            "📊 Status: *Processing*",
            parse_mode="Markdown",
        )

        try:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=(
                    "🔔 *New Withdrawal Request*\n\n"
                    f"🆔 Request ID: `{withdrawal_id}`\n"
                    f"👤 User ID: `{user_id}`\n"
                    f"💸 Amount: *{amount:.2f}৳*\n"
                    f"💳 Method: *{user['wallet_type']}*\n"
                    f"📱 Number: `{user['wallet_number']}`"
                ),
                parse_mode="Markdown",
            )
        except Exception as e:
            print("Admin notification error:", e)

        return

    # Captcha verification step
    if user_id in user_captchas:
        correct = user_captchas[user_id]

        if text.upper() == correct.upper():
            user = get_user(user_id)
            new_balance = user["balance"] + CAPTCHA_REWARD

            update_user(
                user_id,
                balance=new_balance,
            )

            del user_captchas[user_id]

            await update.message.reply_text(
                f"✅ *সঠিক হয়েছে!*\n\n"
                f"💰 {CAPTCHA_REWARD:.2f}৳ আপনার balance-এ যোগ হয়েছে।",
                parse_mode="Markdown",
            )
        else:
            await update.message.reply_text(
                "❌ *ভুল CAPTCHA! আবার চেষ্টা করুন।*",
                parse_mode="Markdown",
            )

        return

    await update.message.reply_text(
        "দয়া করে নিচের menu থেকে একটি option নির্বাচন করুন।"
    )


# =========================================================
# CALLBACK HANDLER
# =========================================================

async def callback_handler(update, context):
    query = update.callback_query

    try:
        await query.answer()
    except Exception:
        pass

    user_id = query.from_user.id
    data = query.data

    if data == "check_join":
        await verify_button(update, context)
        return

    if data == "btn_setwallet":
        keyboard = [
            [
                InlineKeyboardButton(
                    "💳 bKash",
                    callback_data="wallet_bkash",
                ),
                InlineKeyboardButton(
                    "💳 Nagad",
                    callback_data="wallet_nagad",
                ),
            ],
            [
                InlineKeyboardButton(
                    "💳 Rocket",
                    callback_data="wallet_rocket",
                )
            ],
        ]

        await query.message.reply_text(
            "💳 *আপনার payment wallet নির্বাচন করুন:*",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )
        return

    if data == "wallet_bkash":
        context.user_data["waiting_for_wallet_input"] = "bKash"
        await query.message.reply_text(
            "📱 আপনার *bKash number* লিখুন:\n\nউদাহরণ: `017XXXXXXXX`",
            parse_mode="Markdown",
        )
        return

    if data == "wallet_nagad":
        context.user_data["waiting_for_wallet_input"] = "Nagad"
        await query.message.reply_text(
            "📱 আপনার *Nagad number* লিখুন:\n\nউদাহরণ: `017XXXXXXXX`",
            parse_mode="Markdown",
        )
        return

    if data == "wallet_rocket":
        context.user_data["waiting_for_wallet_input"] = "Rocket"
        await query.message.reply_text(
            "📱 আপনার *Rocket number* লিখুন:\n\nউদাহরণ: `017XXXXXXXX`",
            parse_mode="Markdown",
        )
        return

    if data == "btn_process_withdraw":
        user = get_user(user_id)

        if not user["wallet_number"]:
            await query.message.reply_text(
                "❌ *প্রথমে Set Wallet করুন।*",
                parse_mode="Markdown",
            )
            return

        if user["balance"] < MIN_WITHDRAW:
            await query.message.reply_text(
                f"❌ পর্যাপ্ত balance নেই।\n\n"
                f"💰 Balance: {user['balance']:.2f}৳\n"
                f"📉 Minimum: {MIN_WITHDRAW:.2f}৳",
                parse_mode="Markdown",
            )
            return

        context.user_data["waiting_for_withdraw_amount"] = True

        await query.message.reply_text(
            "💸 *Withdraw Amount লিখুন*\n\n"
            f"💳 Wallet: {user['wallet_type']}\n"
            f"📱 Number: `{user['wallet_number']}`\n"
            f"💰 Balance: {user['balance']:.2f}৳\n"
            f"📉 Minimum: {MIN_WITHDRAW:.2f}৳\n\n"
            "উদাহরণ: `50`",
            parse_mode="Markdown",
        )
        return

    if data.startswith("succ_") and user_id == ADMIN_ID:
        try:
            withdrawal_id = int(data.split("_", 1)[1])
        except ValueError:
            return

        with db_lock:
            conn = db()
            row = conn.execute(
                "SELECT * FROM withdrawals WHERE id = ?",
                (withdrawal_id,),
            ).fetchone()

            if row:
                conn.execute(
                    "UPDATE withdrawals "
                    "SET status = 'Success' WHERE id = ?",
                    (withdrawal_id,),
                )

            conn.commit()
            conn.close()

        if not row:
            await query.message.reply_text(
                "❌ Withdrawal request পাওয়া যায়নি।"
            )
            return

        try:
            await context.bot.send_message(
                chat_id=row["user_id"],
                text=(
                    "🎉 *আপনার withdrawal সফল হয়েছে!*\n\n"
                    f"🆔 Request ID: `{withdrawal_id}`\n"
                    f"💸 Amount: *{row['amount']:.2f}৳*\n"
                    f"💳 Method: *{row['wallet_type']}*\n"
                    f"📱 Number: `{row['wallet_number']}`\n"
                    "📊 Status: *Success ✅*"
                ),
                parse_mode="Markdown",
            )
        except Exception as e:
            print("Success notification error:", e)

        try:
            await query.edit_message_text(
                f"✅ Request `{withdrawal_id}` সফল করা হয়েছে।",
                parse_mode="Markdown",
            )
        except Exception:
            pass

        return

    if user_id == ADMIN_ID:
        photo = context.user_data.get("pending_photo")
        caption = context.user_data.get("pending_caption", "")

        if not photo:
            await query.message.reply_text("❌ ছবি পাওয়া যায়নি।")
            return

        if data == "post_g1":
            target = GROUP_1
        elif data == "post_g2":
            target = GROUP_2
        else:
            return

        try:
            await context.bot.send_photo(
                chat_id=target,
                photo=photo,
                caption=caption,
            )
            await query.edit_message_text(
                "✅ সফলভাবে গ্রুপে পোস্ট করা হয়েছে!"
            )
        except Exception as e:
            await query.edit_message_text(
                f"❌ পোস্ট করতে সমস্যা হয়েছে:\n{e}"
            )

        context.user_data.pop("pending_photo", None)
        context.user_data.pop("pending_caption", None)


# =========================================================
# VERIFY
# =========================================================

async def verify_button(update, context):
    query = update.callback_query
    user_id = query.from_user.id

    if await check_membership(user_id, context):
        try:
            await query.message.delete()
        except Exception:
            pass
        await start(update, context)
    else:
        await query.message.reply_text(
            "❌ আপনি এখনো সবগুলো group-এ join করেননি।\n"
            "দয়া করে join করে আবার Verify করুন।"
        )


# =========================================================
# ADMIN COMMANDS
# =========================================================

async def activate_user_command(update, context):
    if update.effective_user.id != ADMIN_ID:
        return

    try:
        target_id = int(context.args[0])
    except (IndexError, ValueError):
        await update.message.reply_text(
            "❌ Format:\n`/activate USER_ID`",
            parse_mode="Markdown",
        )
        return

    ensure_user(target_id)
    update_user(target_id, is_active=1)

    await update.message.reply_text(
        f"✅ User `{target_id}` activated.",
        parse_mode="Markdown",
    )

    try:
        await context.bot.send_message(
            chat_id=target_id,
            text=(
                "🎉 *আপনার account withdrawal-এর জন্য "
                "সক্রিয় করা হয়েছে।*"
            ),
            parse_mode="Markdown",
        )
    except Exception:
        pass


async def add_balance_command(update, context):
    if update.effective_user.id != ADMIN_ID:
        return

    try:
        target_id = int(context.args[0])
        amount = float(context.args[1])
    except (IndexError, ValueError):
        await update.message.reply_text(
            "❌ Format:\n`/addbalance USER_ID AMOUNT`",
            parse_mode="Markdown",
        )
        return

    user = get_user(target_id)
    update_user(
        target_id,
        balance=user["balance"] + amount,
    )

    await update.message.reply_text(
        f"✅ User `{target_id}` balance-এ "
        f"{amount:.2f}৳ যোগ হয়েছে।",
        parse_mode="Markdown",
    )


async def success_withdraw_command(update, context):
    if update.effective_user.id != ADMIN_ID:
        return

    try:
        withdrawal_id = int(context.args[0])
    except (IndexError, ValueError):
        await update.message.reply_text(
            "❌ Format:\n`/success WITHDRAWAL_ID`",
            parse_mode="Markdown",
        )
        return

    with db_lock:
        conn = db()
        row = conn.execute(
            "SELECT * FROM withdrawals WHERE id = ?",
            (withdrawal_id,),
        ).fetchone()

        if row:
            conn.execute(
                "UPDATE withdrawals "
                "SET status = 'Success' WHERE id = ?",
                (withdrawal_id,),
            )

        conn.commit()
        conn.close()

    if not row:
        await update.message.reply_text(
            "❌ Withdrawal request পাওয়া যায়নি।"
        )
        return

    await update.message.reply_text(
        f"✅ Request `{withdrawal_id}` সফল করা হয়েছে।",
        parse_Mode="Markdown",
    )

    try:
        await context.bot.send_message(
            chat_id=row["user_id"],
            text=(
                "🎉 *আপনার withdrawal সফল হয়েছে!*\n\n"
                f"🆔 Request ID: `{withdrawal_id}`\n"
                f"💸 Amount: *{row['amount']:.2f}৳*\n"
                f"💳 Method: *{row['wallet_type']}*\n"
                f"📱 Number: `{row['wallet_number']}`\n"
                "📊 Status: *Success ✅*"
            ),
            parse_mode="Markdown",
        )
    except Exception:
        pass


async def broadcast_command(update, context):
    if update.effective_user.id != ADMIN_ID:
        return

    msg = " ".join(context.args).strip()
    if not msg:
        await update.message.reply_text("❌ মেসেজ লিখুন।")
        return

    count = 0
    for uid in get_all_user_ids():
        try:
            await context.bot.send_message(
                chat_id=uid,
                text=f"📢 *বিজ্ঞপ্তি:*\n\n{msg}",
                parse_mode="Markdown",
            )
            count += 1
        except Exception:
            pass

    await update.message.reply_text(
        f"✅ {count} জন user-এর কাছে notice পাঠানো হয়েছে।"
    )


# =========================================================
# MAIN
# =========================================================

def main():
    token = "8948370050:AAFqFGKbyrZrFZ-fhdvPXhtd25GX3Nw_OcE"

    if not token:
        raise RuntimeError("BOT_TOKEN environment variable সেট করা হয়নি।")

    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("earn", earn_handler))
    app.add_handler(CommandHandler("ad", watch_ad_handler))
    app.add_handler(CommandHandler("balance", balance_handler))
    app.add_handler(CommandHandler("withdraw", withdraw_handler))
    app.add_handler(CommandHandler("support", support_handler))

    app.add_handler(CommandHandler("activate", activate_user_command))
    app.add_handler(CommandHandler("addbalance", add_balance_command))
    app.add_handler(CommandHandler("success", success_withdraw_command))
    app.add_handler(CommandHandler("broadcast", broadcast_command))

    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(
        MessageHandler(
            filters.PHOTO | (filters.TEXT & ~filters.COMMAND),
            handle_message,
        )
    )

    print("QuickCash Captcha Bot is running...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
