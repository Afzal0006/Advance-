from telebot import TeleBot, types
from pymongo import MongoClient
from datetime import datetime

# ==================== CONFIG ====================
BOT_TOKEN = "6098583669:AAE64kFMI_JE6BpgUKyBszq13LdvTgfnsjY"
MONGO_URI = "mongodb+srv://afzal99550:afzal99550@cluster0.aqmbh9q.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

bot = TeleBot(BOT_TOKEN)
client = MongoClient(MONGO_URI)
db = client['escrow_bot']
users_collection = db['users']

# ==================== START COMMAND ====================
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    
    # Save user to MongoDB if not exists
    if not users_collection.find_one({"user_id": user_id}):
        users_collection.insert_one({
            "user_id": user_id,
            "username": username,
            "first_name": first_name,
            "joined_at": datetime.utcnow()
        })
    
    # Send the start message
    start_text = """
Your Trustworthy Telegram Escrow Service

Welcome to bot! This bot provides a reliable escrow service for your transactions on Telegram.
Avoid scams, your funds are safeguarded throughout your deals. If you run into any issues, simply type /dispute and an arbitrator will join the group chat within 24 hours.

🎟 ESCROW FEE:
1.0% for P2P and 1.0% for OTC Flat

💬 Proceed with /escrow (to start with a new escrow)

⚠️ IMPORTANT - Make sure coin is same of Buyer and Seller else you may lose your coin.
"""
    bot.send_message(user_id, start_text)

# ==================== ESCROW COMMAND ====================
@bot.message_handler(commands=['escrow'])
def escrow(message):
    bot.send_message(message.chat.id, "Starting a new escrow... (functionality to be implemented)")

# ==================== DISPUTE COMMAND ====================
@bot.message_handler(commands=['dispute'])
def dispute(message):
    bot.send_message(message.chat.id, "An arbitrator will join the group chat within 24 hours.")

# ==================== RUN BOT ====================
bot.infinity_polling()
