# QuickCash Captcha Bot

## Files
- `bot.py` - main bot
- `requirements.txt` - Python packages
- `.env.example` - environment variable example

## Important
Do NOT put your Telegram Bot Token directly inside `bot.py` or commit it to GitHub.

Set these environment variables in your hosting service:
- `BOT_TOKEN`
- `ADMIN_ID`
- `ADMIN_USERNAME`
- `GROUP_1`
- `GROUP_2`

The bot stores user balances, wallets, referrals and withdrawals in SQLite (`bot.db`).

## Admin commands
- `/activate USER_ID`
- `/addbalance USER_ID AMOUNT`
- `/success WITHDRAWAL_ID`
- `/broadcast MESSAGE`

## Note
Account activation is controlled by the admin command. The bot does not instruct users to send an activation payment.
