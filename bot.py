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

# ==================== COMMANDS LIST ====================
@bot.message_handler(commands=['commands'])
def commands_list(message):
    commands_text = """
📌 AVAILABLE COMMANDS

/start - A command to start interacting with the bot
/whatisescrow - A command to tell you more about escrow
/instructions - A command with text instructions
/terms - A command to bring out our TOS
/dispute - A command to contact the admins
/menu - A command to bring out a menu for the bot
/contact - A command to get admin's contact
/commands - A command to get commands list
/stats - A command to check user stats
/vouch - A command to vouch for the bot
/newdeal - A command to start a new deal
/tradeid - A command to get trade id for a chat
/dd - A command to add deal details
/escrow - A command to get a escrow group link
/token - A command to select token for the escrow
/deposit - A command to generate deposit address
/verify - A command to verify wallet address.
/dispute - A command to raise a dispute request
/balance - A command to check the balance of the escrow address
/release - A command to release the funds in the escrow
/refund - A command to refund the funds in the escrow
/seller - A command to set the seller
/buyer - A command to set the buyer
/setfee - A command to set custom trade fee
/save - A command to save default addresses for various chains.
/saved - A command to check saved addresses
/referral - A command to check your referrals
"""
    # Inline button for Back
    markup = types.InlineKeyboardMarkup()
    back_button = types.InlineKeyboardButton("🔙 Back", callback_data="back_to_start")
    markup.add(back_button)
    
    bot.send_message(message.chat.id, commands_text, reply_markup=markup)

# ==================== BUTTON CALLBACK ====================
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.data == "back_to_start":
        start(call.message)

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
