from telebot import TeleBot
from pymongo import MongoClient
from datetime import datetime

BOT_TOKEN = "8350094964:AAE-ebwWQBx_YWnW_stEqcxiKKVVx8SZaAw"
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
        "🌐 <a href='https://t.me/updates_channel'>UPDATES</a>   <a href='https://t.me/vouches_channel'>VOUCHES</a> ☑️\n\n"
        "💬 Proceed with /escrow (to start with a new escrow)\n\n"
        "⚠️ <b>IMPORTANT</b> - Make sure coin is same of Buyer and Seller else you may loose your coin.\n\n"
        "💡 Type /menu to summon a menu with all bots features"
    )
    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=["menu"])
def menu(message):
    text = (
        "📋 <b>Menu Options</b>\n\n"
        "/escrow - Start a new escrow\n"
        "/dispute - Raise a dispute\n"
        "/commands - Full command list\n"
        "/contact - Contact arbitrator\n"
        "/stats - Your stats\n"
        "/help - Help section"
    )
    bot.send_message(message.chat.id, text, parse_mode="HTML")

@bot.message_handler(commands=["commands"])
def commands(message):
    text = (
        "📌 <b>AVAILABLE COMMANDS</b>\n\n"
        "/start - Start interacting with the bot\n"
        "/whatisescrow - Info about escrow\n"
        "/instructions - Text instructions\n"
        "/terms - Terms of service\n"
        "/dispute - Contact the admins\n"
        "/menu - Bring out a menu\n"
        "/contact - Get admin's contact\n"
        "/commands - Get commands list\n"
        "/stats - Check user stats\n"
        "/vouch - Vouch for the bot\n"
        "/newdeal - Start a new deal\n"
        "/tradeid - Get trade id\n"
        "/dd - Add deal details\n"
        "/escrow - Get escrow group link\n"
        "/token - Select token for escrow\n"
        "/deposit - Generate deposit address\n"
        "/verify - Verify wallet address\n"
        "/dispute - Raise dispute request\n"
        "/balance - Check escrow balance\n"
        "/release - Release funds\n"
        "/refund - Refund funds\n"
        "/seller - Set the seller\n"
        "/buyer - Set the buyer\n"
        "/setfee - Set custom trade fee\n"
        "/save - Save default addresses\n"
        "/saved - Check saved addresses\n"
        "/referral - Check referrals"
    )
    bot.send_message(message.chat.id, text, parse_mode="HTML")

@bot.message_handler(commands=["contact"])
def contact(message):
    text = (
        "☎️ <b>CONTACT ARBITRATOR</b>\n\n"
        "💬 Type /dispute\n\n"
        "💡 If you're not getting a response, you can reach out to @golgibody"
    )
    bot.send_message(message.chat.id, text, parse_mode="HTML")

bot.infinity_polling()
