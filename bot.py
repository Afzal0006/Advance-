from telebot import TeleBot, types
from pymongo import MongoClient

BOT_TOKEN = "8269236510:AAHhnjm_jTFKDFnLY0kmwlISzBib0fV55pg"
MONGO_URI = "mongodb+srv://afzal99550:afzal99550@cluster0.aqmbh9q.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

UPDATES_CHANNEL = "https://t.me/YourUpdatesChannel"
VOUCHES_CHANNEL = "https://t.me/YourVouchesChannel"

START_MESSAGE = f"""
💫 @PagaLEscrowBot 💫
Your Trustworthy Telegram Escrow Service

Welcome to @PagaLEscrowBot. This bot provides a reliable escrow service for your transactions on Telegram.
Avoid scams, your funds are safeguarded throughout your deals. If you run into any issues, simply type /dispute and an arbitrator will join the group chat within 24 hours.

🎟 ESCROW FEE:
1.0% for P2P and 1.0% for OTC Flat

🌐 Updates: {UPDATES_CHANNEL}  
☑️ Vouches: {VOUCHES_CHANNEL}

💬 Proceed with /escrow (to start with a new escrow)

⚠️ IMPORTANT - Make sure coin is same of Buyer and Seller else you may lose your coin.

💡 Type /menu to summon a menu with all bots features
"""

bot = TeleBot(BOT_TOKEN)
client = MongoClient(MONGO_URI)
db = client['escrow_bot']
users_collection = db['users']

@bot.message_handler(commands=['start'])
def send_welcome(message):
    if not users_collection.find_one({"user_id": message.from_user.id}):
        users_collection.insert_one({
            "user_id": message.from_user.id,
            "username": message.from_user.username,
            "joined_at": message.date
        })
    bot.send_message(message.chat.id, START_MESSAGE, parse_mode="Markdown")

@bot.message_handler(commands=['menu'])
def menu(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("/escrow", "/dispute", "/updates", "/vouches")
    bot.send_message(message.chat.id, "Select an option:", reply_markup=markup)

@bot.message_handler(commands=['escrow'])
def start_escrow(message):
    bot.send_message(message.chat.id, "📝 Please provide escrow details to start a new transaction.")

@bot.message_handler(commands=['dispute'])
def dispute(message):
    bot.send_message(message.chat.id, "⚠️ An arbitrator will join the chat within 24 hours to resolve your dispute.")

@bot.message_handler(commands=['updates'])
def updates(message):
    bot.send_message(message.chat.id, f"🌐 Latest updates: {UPDATES_CHANNEL}")

@bot.message_handler(commands=['vouches'])
def vouches(message):
    bot.send_message(message.chat.id, f"☑️ Verified vouches: {VOUCHES_CHANNEL}")

bot.infinity_polling()
