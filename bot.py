from telebot import TeleBot, types
from pymongo import MongoClient
from datetime import datetime

BOT_TOKEN = "8269236510:AAHhnjm_jTFKDFnLY0kmwlISzBib0fV55pg"
MONGO_URI = "mongodb+srv://afzal99550:afzal99550@cluster0.aqmbh9q.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

bot = TeleBot(BOT_TOKEN, parse_mode="HTML")
client = MongoClient(MONGO_URI)
db = client["escrow_bot"]
users = db["users"]

# --------- /start command ----------
@bot.message_handler(commands=["start"])
def start(message):
    user_id = message.from_user.id
    username = message.from_user.username
    if not users.find_one({"user_id": user_id}):
        users.insert_one({
            "user_id": user_id,
            "username": username,
            "joined_at": datetime.utcnow(),
            "transactions": [],
            "disputes": []
        })

    text = (
        "💫 @demoescrowerbot 💫\n"
        "Your Trustworthy Telegram Escrow Service\n\n"
        "Welcome! Use the buttons below to get started."
    )

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(
        types.InlineKeyboardButton("🔗 Updates Channel", url="https://t.me/updates_channel"),
        types.InlineKeyboardButton("🔗 Vouches Channel", url="https://t.me/vouches_channel")
    )
    keyboard.add(types.InlineKeyboardButton("💬 Start Escrow", callback_data="escrow"))
    keyboard.add(types.InlineKeyboardButton("📋 Menu", callback_data="menu"))

    bot.send_message(message.chat.id, text, reply_markup=keyboard)

# --------- /menu command ----------
@bot.message_handler(commands=["menu"])
def menu(message):
    text = "📋 <b>Menu Options</b>\n\nSelect an option below:"

    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton("💬 Start Escrow", callback_data="escrow"),
        types.InlineKeyboardButton("⚠️ Raise Dispute", callback_data="dispute"),
        types.InlineKeyboardButton("📌 Commands List", callback_data="commands"),
        types.InlineKeyboardButton("☎️ Contact Admin", callback_data="contact"),
        types.InlineKeyboardButton("📊 Your Stats", callback_data="stats"),
        types.InlineKeyboardButton("💡 Help", callback_data="help")
    )

    bot.send_message(message.chat.id, text, reply_markup=keyboard, parse_mode="HTML")

# --------- /commands command ----------
@bot.message_handler(commands=["commands"])
def commands(message):
    text = (
        "📌 <b>AVAILABLE COMMANDS</b>\n\n"
        "/start\n"
        "/menu\n"
        "/escrow\n"
        "/dispute\n"
        "/contact\n"
        "/stats\n"
        "/help\n"
        "/vouch\n"
        "/referral"
    )
    bot.send_message(message.chat.id, text, parse_mode="HTML")

# --------- /contact command ----------
@bot.message_handler(commands=["contact"])
def contact(message):
    text = (
        "☎️ <b>CONTACT ARBITRATOR</b>\n\n"
        "💬 Type /dispute\n"
        "💡 Or reach out to @golgibody"
    )
    bot.send_message(message.chat.id, text, parse_mode="HTML")

# --------- Handle button clicks ----------
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.data == "escrow":
        bot.send_message(call.message.chat.id, "💬 Send /escrow to start a new escrow.")
    elif call.data == "dispute":
        bot.send_message(call.message.chat.id, "⚠️ Send /dispute to raise a dispute.")
    elif call.data == "commands":
        bot.send_message(call.message.chat.id, "📌 Send /commands to see all available commands.")
    elif call.data == "contact":
        bot.send_message(call.message.chat.id, "☎️ Contact admin: @golgibody")
    elif call.data == "stats":
        bot.send_message(call.message.chat.id, "📊 Your stats will appear here.")
    elif call.data == "help":
        bot.send_message(call.message.chat.id, "💡 Type /help for assistance.")
    elif call.data == "menu":
        menu(call.message)  # Show menu buttons

# --------- Start bot ----------
bot.infinity_polling()
