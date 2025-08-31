from telebot import TeleBot, types
from pymongo import MongoClient
import re

# ================= CONFIG =================
BOT_TOKEN = "6098583669:AAE64kFMI_JE6BpgUKyBszq13LdvTgfnsjY"
MONGO_URI = "mongodb+srv://afzal99550:afzal99550@cluster0.aqmbh9q.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

bot = TeleBot(BOT_TOKEN, parse_mode="HTML")
client = MongoClient(MONGO_URI)
db = client['escrow_bot']
users_collection = db['users']
deals_collection = db['deals']

# ================= TEXTS =================
AVAILABLE_COMMANDS = """📌 AVAILABLE COMMANDS

/start - Start interacting with the bot
/whatisescrow - Learn about escrow
/instructions - Guide for using bot
/terms - Bot TOS
/dispute - Contact admins
/menu - Show menu
/contact - Admin contact
/commands - Commands list
/stats - User stats
/vouch - Vouch for bot
/newdeal - Start new deal
/tradeid - Get trade ID
/dd - Add deal details
/escrow - Escrow group link
/token - Select token for escrow
/deposit - Deposit address
/verify - Verify wallet
/balance - Check balance
/release - Release funds
/refund - Refund funds
/seller - Set seller
/buyer - Set buyer
/setfee - Set custom fee
/save - Save default addresses
/saved - Check saved addresses
/referral - Check referrals
"""

CONTACT_TEXT = """☎️ CONTACT ARBITRATOR

💬 Type /dispute

💡 Incase you're not getting a response, reach out to @golgibody
"""

INSTRUCTIONS_TEXT = """📘 GUIDE “HOW TO USE (Escrow Bot)” FOR SAFE AND FASTEST HASSLE-FREE ESCROW 🚀

Step 1 : Use /escrow command in the DM of the Bot.  
Step 2 : Use /dd command to initiate escrow.  
Step 3 : Use /buyer or /seller to verify address.  
Step 4 : Choose token/network with /token.  
Step 5 : Use /deposit to deposit the asset.  
Step 6 : Once verified, continue the deal.  
Step 7 : After success, release asset with /release.  

🚨 Use /dispute if any issue arises.
"""

TERMS_TEXT = """📜 TERMS

Our terms of usage are simple.

🎟 Fees
1.0% for P2P and 1.0% for OTC Flat. Transactions fee applies.

1️⃣ Record testing or screenshots to provide evidence.  
2️⃣ Learn what you are buying.  
3️⃣ Buyer should release funds only after receiving the item.  
4️⃣ Use trusted wallets to avoid issues.  
5️⃣ Fees are taken from wallet balance.  
6️⃣ Ensure coin/network match for buyer and seller.
"""

UPDATE_CHANNEL_URL = "https://t.me/YOUR_UPDATE_CHANNEL"
VOUCH_CHANNEL_URL = "https://t.me/YOUR_VOUCH_CHANNEL"

# ================= HELPERS =================
def tag_user(message):
    return f"<a href='tg://user?id={message.from_user.id}'>{message.from_user.first_name}</a>"

# ================= START COMMAND =================
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

# ================= /dd COMMAND =================
@bot.message_handler(commands=['dd'])
def start_deal(message):
    user_tag = tag_user(message)
    deals_collection.update_one(
        {"chat_id": message.chat.id},
        {"$set": {"dd_started": True, "user_id": message.from_user.id}},
        upsert=True
    )
    bot.send_message(
        message.chat.id,
        f"Hello {user_tag},\nKindly tell deal details i.e.\n\n"
        "Quantity -\nRate -\nConditions (if any) -\n\n"
        "Remember without it disputes wouldn’t be resolved. Once filled, proceed with /seller or /buyer [CRYPTO ADDRESS]"
    )

# ================= /seller COMMAND =================
@bot.message_handler(commands=['seller'])
def set_seller(message):
    user_tag = tag_user(message)
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, f"{user_tag} ❌ Provide your wallet. Example: /seller {{BEP20_ADDRESS}}")
        return
    seller_address = args[1]

    if not re.match(r"^0x[a-fA-F0-9]{40}$", seller_address):
        bot.reply_to(message, f"{user_tag} ❌ Invalid BEP20 address!")
        return

    deal = deals_collection.find_one({"chat_id": message.chat.id})
    if deal and deal.get("seller_address"):
        bot.reply_to(message, f"{user_tag} ❌ Seller address already set for this group!")
        return

    deals_collection.update_one(
        {"chat_id": message.chat.id},
        {"$set": {"seller_id": message.from_user.id, "seller_address": seller_address}},
        upsert=True
    )

    buyer_address = deal.get("buyer_address") if deal else None

    bot.send_message(
        message.chat.id,
        f"📍ESCROW-ROLE DECLARATION\n\n⚡️ SELLER {message.from_user.first_name}\n"
        f"User ID {message.from_user.id}\n\n✅ SELLER WALLET\n{seller_address}\n\n"
        f"{'Buyer already set: ' + buyer_address if buyer_address else 'Please set buyer using /buyer [DEPOSIT ADDRESS]'}",
        parse_mode="HTML"
    )

# ================= /buyer COMMAND =================
@bot.message_handler(commands=['buyer'])
def set_buyer(message):
    user_tag = tag_user(message)
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, f"{user_tag} ❌ Provide buyer wallet. Example: /buyer {{BEP20_ADDRESS}}")
        return
    buyer_address = args[1]

    if not re.match(r"^0x[a-fA-F0-9]{40}$", buyer_address):
        bot.reply_to(message, f"{user_tag} ❌ Invalid BEP20 address!")
        return

    deal = deals_collection.find_one({"chat_id": message.chat.id})
    if deal and deal.get("buyer_address"):
        bot.reply_to(message, f"{user_tag} ❌ Buyer address already set for this group!")
        return

    deals_collection.update_one(
        {"chat_id": message.chat.id},
        {"$set": {"buyer_id": message.from_user.id, "buyer_address": buyer_address}},
        upsert=True
    )

    bot.send_message(
        message.chat.id,
        f"📍ESCROW-ROLE DECLARATION\n\n⚡️ BUYER {message.from_user.first_name}\n"
        f"User ID {message.from_user.id}\n\n✅ BUYER WALLET\n{buyer_address}\n\n"
        "Seller should already be set using /seller [ADDRESS]",
        parse_mode="HTML"
    )

# ================= GROUP WELCOME =================
@bot.my_chat_member_handler()
def welcome_new_group(update):
    if update.new_chat_member.status == "member":
        chat_id = update.chat.id
        bot.send_message(
            chat_id,
            "📍 Hey there traders! Welcome to our escrow service.\n"
            "✅ Please start with /dd command and fill the DealInfo Form"
        )

# ================= CALLBACKS FOR BUTTONS =================
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

# ================= POLLING =================
bot.polling(non_stop=True, allowed_updates=["message", "callback_query", "my_chat_member"])
