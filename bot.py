from telebot import TeleBot, types
from pymongo import MongoClient

BOT_TOKEN = "6098583669:AAE64kFMI_JE6BpgUKyBszq13LdvTgfnsjY"
MONGO_URI = "mongodb+srv://afzal99550:afzal99550@cluster0.aqmbh9q.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

bot = TeleBot(BOT_TOKEN)
client = MongoClient(MONGO_URI)
db = client['escrow_bot']
users_collection = db['users']

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

CONTACT_TEXT = """☎️ CONTACT ARBITRATOR

💬 Type /dispute

💡 Incase you're not getting a response, you can reach out to @golgibody
"""

INSTRUCTIONS_TEXT = """📘 GUIDE “HOW TO USE (Escrow Bot)” FOR SAFE AND FASTEST HASSLE-FREE ESCROW 🚀

Step 1 : Use /escrow command in the DM of the Bot.  
( It will auto-create a safe escrow group and drop the link so that buyer and seller can join via that link. ) 🔗👥  

Step 2 : Use /dd command to initiate the process of escrow where you will get the format to express your deal and info.  
( It will include quantity, rate, TnC’s agreed upon by both parties. ) 📝🤝  

Step 3 : Use /buyer (your address) if you are a buyer 🛒 or /seller (your address) if you are a seller 🏪 to verify address and continue the deal.  
( Provide your crypto address which will be used in case of release or refund. ) 💳🔐  

Step 4 : Choose the token and network by /token command and then either party has to accept it. ✅💱  

Step 5 : Use /deposit command to deposit the asset within the bot.  
( Note : Bot will give the deposit address and it has a time limit to deposit ⏳, you have to deposit within that given time. ) ⏰💸  

Step 6 : Once verified by the bot, you can continue the deal.  
( Bot will send the real-time deposit details in the chat. ) 📊💬  

Step 7 : After a successful deal, you can release the asset to the party by using /release (amount/all).  
( Thus, the bot will itself release the asset to the party and send the verification in the chat. ) 🎉💼  

🚨 IN CASE OF ANY DISPUTE OR ISSUE, YOU CAN FEEL FREE TO USE /dispute COMMAND, AND SUPPORT WILL JOIN YOU SHORTLY. 🛎️👩‍💻
"""

UPDATE_CHANNEL_URL = "https://t.me/YOUR_UPDATE_CHANNEL"
VOUCH_CHANNEL_URL = "https://t.me/YOUR_VOUCH_CHANNEL"

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
    keyboard.add(types.InlineKeyboardButton("Instructions", callback_data="show_instructions"))
    keyboard.row(
        types.InlineKeyboardButton("Update Channel", url=UPDATE_CHANNEL_URL),
        types.InlineKeyboardButton("Vouch Channel", url=VOUCH_CHANNEL_URL)
    )
    bot.send_message(message.chat.id, "Your Trustworthy Telegram Escrow Service", reply_markup=keyboard)

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
    elif call.data == "back_start":
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("Available Commands", callback_data="show_commands"))
        keyboard.add(types.InlineKeyboardButton("☎️ Contact", callback_data="show_contact"))
        keyboard.add(types.InlineKeyboardButton("Instructions", callback_data="show_instructions"))
        keyboard.row(
            types.InlineKeyboardButton("Update Channel", url=UPDATE_CHANNEL_URL),
            types.InlineKeyboardButton("Vouch Channel", url=VOUCH_CHANNEL_URL)
        )
        bot.edit_message_text("Your Trustworthy Telegram Escrow Service", call.message.chat.id, call.message.message_id, reply_markup=keyboard)

bot.polling()
