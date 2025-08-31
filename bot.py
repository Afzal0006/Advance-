from telebot import TeleBot, types
from pymongo import MongoClient

BOT_TOKEN = "6098583669:AAE64kFMI_JE6BpgUKyBszq13LdvTgfnsjY"
MONGO_URI = "mongodb+srv://afzal99550:afzal99550@cluster0.aqmbh9q.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

bot = TeleBot(BOT_TOKEN)
client = MongoClient(MONGO_URI)
db = client['escrow_bot']
users_collection = db['users']
deals_collection = db['deals']  # store /dd deal info

AVAILABLE_COMMANDS = """📌 AVAILABLE COMMANDS

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

CONTACT_TEXT = """☎️ CONTACT ARBITRATOR

💬 Type /dispute

💡 Incase you're not getting a response, you can reach out to @golgibody
"""

INSTRUCTIONS_TEXT = """📘 GUIDE “HOW TO USE (Escrow Bot)” FOR SAFE AND FASTEST HASSLE-FREE ESCROW 🚀

Step 1 : Use /escrow command in the DM of the Bot.  
Step 2 : Use /dd command to initiate the process of escrow.  
Step 3 : Use /buyer or /seller to verify address.  
Step 4 : Choose token/network with /token.  
Step 5 : Use /deposit to deposit the asset.  
Step 6 : Once verified, continue the deal.  
Step 7 : After success, release asset with /release.  

🚨 Use /dispute in case of any issue.
"""

TERMS_TEXT = """📜 TERMS

Our terms of usage are simple.

🎟 Fees
1.0% for P2P and 1.0% for OTC Flat.

Transactions fee will be applicable.

TAKE THIS INTO ACCOUNT WHEN DEPOSITING FUNDS

1️⃣ Record/screenshot testing of logins or data.  
2️⃣ Learn what you are buying.  
3️⃣ Buyer should release funds only after receiving what was paid for.  
4️⃣ Use trusted wallets to avoid issues.  
5️⃣ Fees are taken from the wallet balance (1.0% P2P, 1.0% OTC).  
6️⃣ Ensure coin/network match for buyer and seller.
"""

UPDATE_CHANNEL_URL = "https://t.me/YOUR_UPDATE_CHANNEL"
VOUCH_CHANNEL_URL = "https://t.me/YOUR_VOUCH_CHANNEL"

# Start command
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    username = message.from_user.username
    if not users_collection.find_one({"user_id": user_id}):
        users_collection.insert_one({
            "user_id": user_id,
            "username": username,
            "joined_at": message.date
        })
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("Available Commands", callback_data="show_commands"))
    keyboard.add(types.InlineKeyboardButton("☎️ Contact", callback_data="show_contact"))
    keyboard.row(
        types.InlineKeyboardButton("Instructions", callback_data="show_instructions"),
        types.InlineKeyboardButton("Terms", callback_data="show_terms")
    )
    keyboard.row(
        types.InlineKeyboardButton("Update Channel", url=UPDATE_CHANNEL_URL),
        types.InlineKeyboardButton("Vouch Channel", url=VOUCH_CHANNEL_URL)
    )
    bot.send_message(message.chat.id, "Your Trustworthy Telegram Escrow Service", reply_markup=keyboard)

# Handle /dd command
@bot.message_handler(commands=['dd'])
def start_deal(message):
    deals_collection.update_one(
        {"chat_id": message.chat.id},
        {"$set": {"dd_started": True}},
        upsert=True
    )
    bot.send_message(
        message.chat.id,
        "Hello there,\nKindly tell deal details i.e.\n\n"
        "Quantity -\nRate -\nConditions (if any) -\n\n"
        "Remember without it disputes wouldn’t be resolved. Once filled proceed with Specifications of the seller or buyer with /seller or /buyer [CRYPTO ADDRESS]"
    )

# Handle bot added to group
@bot.my_chat_member_handler()
def welcome_new_group(update):
    if update.new_chat_member.status == "member":
        chat_id = update.chat.id
        bot.send_message(
            chat_id,
            "📍 Hey there traders! Welcome to our escrow service.\n"
            "✅ Please start with /dd command and fill the DealInfo Form"
        )

# Handle callbacks for buttons
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.data == "show_commands":
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("Back 🔙", callback_data="back_start"))
        bot.edit_message_text(AVAILABLE_COMMANDS, call.message.chat.id, call.message.message_id, reply_markup=keyboard)
    elif call.data == "show_contact":
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("Back 🔙", callback_data="back_start"))
        bot.edit_message_text(CONTACT_TEXT, call.message.chat.id, call.message.message_id, reply_markup=keyboard)
    elif call.data == "show_instructions":
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("Back 🔙", callback_data="back_start"))
        bot.edit_message_text(INSTRUCTIONS_TEXT, call.message.chat.id, call.message.message_id, reply_markup=keyboard)
    elif call.data == "show_terms":
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("Back 🔙", callback_data="back_start"))
        bot.edit_message_text(TERMS_TEXT, call.message.chat.id, call.message.message_id, reply_markup=keyboard)
    elif call.data == "back_start":
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("Available Commands", callback_data="show_commands"))
        keyboard.add(types.InlineKeyboardButton("☎️ Contact", callback_data="show_contact"))
        keyboard.row(
            types.InlineKeyboardButton("Instructions", callback_data="show_instructions"),
            types.InlineKeyboardButton("Terms", callback_data="show_terms")
        )
        keyboard.row(
            types.InlineKeyboardButton("Update Channel", url=UPDATE_CHANNEL_URL),
            types.InlineKeyboardButton("Vouch Channel", url=VOUCH_CHANNEL_URL)
        )
        bot.edit_message_text("Your Trustworthy Telegram Escrow Service", call.message.chat.id, call.message.message_id, reply_markup=keyboard)

bot.polling()
