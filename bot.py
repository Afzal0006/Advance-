from telebot import TeleBot, types
from pymongo import MongoClient
from datetime import datetime

BOT_TOKEN = "8232198206:AAHz2GHiKWQAcMKTF-Iz5Nl_Haatsi4ol_o"
MONGO_URI = "mongodb+srv://afzal99550:afzal99550@cluster0.aqmbh9q.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

bot = TeleBot(BOT_TOKEN, parse_mode="HTML")
client = MongoClient(MONGO_URI)
db = client["escrow_bot"]
users = db["users"]

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
        "💫 @demoescrowerbot💫\n"
        "Your Trustworthy Telegram Escrow Service\n\n"
        "Welcome to @demoescrowerbot . This bot provides a reliable escrow service for your transactions on Telegram.\n"
        "Avoid scams, your funds are safeguarded throughout your deals. If you run into any issues, simply type /dispute and an arbitrator will join the group chat within 24 hours.\n\n"
        "🎟 <b>ESCROW FEE:</b>\n"
        "1.0% for P2P and 1.0% for OTC Flat\n\n"
        "🌐 <a href='https://t.me/RulerofSaudi'>UPDATES</a>   <a href='https://t.me/Multicellular'>VOUCHES</a> ☑️\n\n"
        "💬 Proceed with /escrow (to start with a new escrow)\n\n"
        "⚠️ <b>IMPORTANT</b> - Make sure coin is same of Buyer and Seller else you may loose your coin.\n\n"
        "💡 Type /menu to summon a menu with all bots features"
    )
    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=["menu"])
def menu(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("/escrow", "/dispute")
    markup.add("My Transactions", "Help")
    bot.send_message(message.chat.id, "📋 Menu Options:", reply_markup=markup)

bot.infinity_polling()
