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
/start - Start interacting
/whatisescrow - Learn about escrow
/instructions - Guide
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
/token - Select token
/deposit - Deposit address
/verify - Verify wallet
/balance - Check balance
/release - Release funds
/refund - Refund funds
/seller - Set seller
/buyer - Set buyer
/setfee - Set custom fee
/save - Save addresses
/saved - Check saved addresses
/referral - Check referrals
"""

CONTACT_TEXT = """☎️ CONTACT ARBITRATOR
💬 Type /dispute
💡 Reach out to @golgibody if no response
"""

INSTRUCTIONS_TEXT = """📘 GUIDE “HOW TO USE (Escrow Bot)” 🚀

1. Use /escrow command in DM
2. /dd to initiate escrow
3. /buyer or /seller to verify address
4. /token to choose token/network
5. /deposit to deposit asset
6. Continue deal after verification
7. /release to release asset
🚨 Use /dispute if any issue
"""

TERMS_TEXT = """📜 TERMS
🎟 Fees 1.0% for P2P & OTC Flat
1️⃣ Record testing screenshots
2️⃣ Learn what you buy
3️⃣ Release funds only after receiving item
4️⃣ Use trusted wallets
5️⃣ Fees taken from wallet balance
6️⃣ Ensure coin/network match
"""

UPDATE_CHANNEL_URL = "https://t.me/YOUR_UPDATE_CHANNEL"
VOUCH_CHANNEL_URL = "https://t.me/YOUR_VOUCH_CHANNEL"

# ================= HELPERS =================

def tag_user(message):
    return f"<a href='tg://user?id={message.from_user.id}'>{message.from_user.first_name}</a>"

# ================= START =================

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    username = message.from_user.username
    if not users_collection.find_one({"user_id": user_id}):
        users_collection.insert_one({"user_id": user_id, "username": username, "joined_at": message.date})

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("Available Commands", callback_data="show_commands"))
    kb.add(types.InlineKeyboardButton("☎️ Contact", callback_data="show_contact"))
    kb.row(types.InlineKeyboardButton("Instructions", callback_data="show_instructions"),
           types.InlineKeyboardButton("Terms", callback_data="show_terms"))
    kb.row(types.InlineKeyboardButton("Update Channel", url=UPDATE_CHANNEL_URL),
           types.InlineKeyboardButton("Vouch Channel", url=VOUCH_CHANNEL_URL))
    bot.send_message(message.chat.id, "Your Trustworthy Telegram Escrow Service", reply_markup=kb)

# ================= /dd =================

@bot.message_handler(commands=['dd'])
def dd(message):
    user_tag = tag_user(message)
    deals_collection.update_one(
        {"chat_id": message.chat.id},
        {"$set": {"dd_started": True, "user_id": message.from_user.id}},
        upsert=True
    )
    bot.send_message(
        message.chat.id,
        f"Hello {user_tag},\nKindly tell deal details:\nQuantity -\nRate -\nConditions (if any) -\n\n"
        "Once filled, proceed with /seller or /buyer [CRYPTO ADDRESS]",
        parse_mode="HTML",
        reply_to_message_id=message.message_id
    )

# ================= /seller =================

@bot.message_handler(commands=['seller'])
def seller(message):
    user_tag = tag_user(message)
    args = message.text.split()
    if len(args) < 2:
        bot.send_message(message.chat.id,
                         f"{user_tag} ❌ Provide wallet. Example: /seller {{BEP20_ADDRESS}}",
                         parse_mode="HTML", reply_to_message_id=message.message_id)
        return

    seller_address = args[1]
    if not re.match(r"^0x[a-fA-F0-9]{40}$", seller_address):
        bot.send_message(message.chat.id,
                         f"{user_tag} ❌ Invalid BEP20 address!",
                         parse_mode="HTML", reply_to_message_id=message.message_id)
        return

    deal = deals_collection.find_one({"chat_id": message.chat.id})
    if deal and deal.get("seller_address"):
        bot.send_message(message.chat.id,
                         f"{user_tag} ❌ Seller already set!",
                         parse_mode="HTML", reply_to_message_id=message.message_id)
        return
    if deal and deal.get("buyer_id") == message.from_user.id:
        bot.send_message(message.chat.id,
                         f"{user_tag} ❌ Already buyer! Cannot be seller.",
                         parse_mode="HTML", reply_to_message_id=message.message_id)
        return
    if deal and (deal.get("seller_address") == seller_address or deal.get("buyer_address") == seller_address):
        bot.send_message(message.chat.id,
                         f"{user_tag} ❌ Wallet already used!",
                         parse_mode="HTML", reply_to_message_id=message.message_id)
        return

    deals_collection.update_one(
        {"chat_id": message.chat.id},
        {"$set": {"seller_id": message.from_user.id, "seller_address": seller_address}},
        upsert=True
    )
    buyer_address = deal.get("buyer_address") if deal else None
    msg = (f"📍ESCROW-ROLE DECLARATION\n\n⚡️ SELLER {user_tag}\nUser ID {message.from_user.id}\n\n"
           f"✅ SELLER WALLET\n{seller_address}\n\n"
           f"{'Buyer already set: ' + buyer_address if buyer_address else 'Please set buyer using /buyer [DEPOSIT ADDRESS]'}")
    bot.send_message(message.chat.id, msg, parse_mode="HTML", reply_to_message_id=message.message_id)

# ================= /buyer =================

@bot.message_handler(commands=['buyer'])
def buyer(message):
    user_tag = tag_user(message)
    args = message.text.split()
    if len(args) < 2:
        bot.send_message(message.chat.id,
                         f"{user_tag} ❌ Provide wallet. Example: /buyer {{BEP20_ADDRESS}}",
                         parse_mode="HTML", reply_to_message_id=message.message_id)
        return

    buyer_address = args[1]
    if not re.match(r"^0x[a-fA-F0-9]{40}$", buyer_address):
        bot.send_message(message.chat.id,
                         f"{user_tag} ❌ Invalid BEP20 address!",
                         parse_mode="HTML", reply_to_message_id=message.message_id)
        return

    deal = deals_collection.find_one({"chat_id": message.chat.id})
    if deal and deal.get("buyer_address"):
        bot.send_message(message.chat.id,
                         f"{user_tag} ❌ Buyer already set!",
                         parse_mode="HTML", reply_to_message_id=message.message_id)
        return
    if deal and deal.get("seller_id") == message.from_user.id:
        bot.send_message(message.chat.id,
                         f"{user_tag} ❌ Already seller! Cannot be buyer.",
                         parse_mode="HTML", reply_to_message_id=message.message_id)
        return
    if deal and (deal.get("seller_address") == buyer_address or deal.get("buyer_address") == buyer_address):
        bot.send_message(message.chat.id,
                         f"{user_tag} ❌ Wallet already used!",
                         parse_mode="HTML", reply_to_message_id=message.message_id)
        return

    deals_collection.update_one(
        {"chat_id": message.chat.id},
        {"$set": {"buyer_id": message.from_user.id, "buyer_address": buyer_address}},
        upsert=True
    )
    seller_address = deal.get("seller_address") if deal else None
    msg = (f"📍ESCROW-ROLE DECLARATION\n\n⚡️ BUYER {user_tag}\nUser ID {message.from_user.id}\n\n"
           f"✅ BUYER WALLET\n{buyer_address}\n\n"
           f"{'Seller already set: ' + seller_address if seller_address else 'Seller should set /seller [ADDRESS]'}")
    bot.send_message(message.chat.id, msg, parse_mode="HTML", reply_to_message_id=message.message_id)

# ================= GROUP WELCOME =================

@bot.message_handler(content_types=['new_chat_members'])
def new_member(message):
    for user in message.new_chat_members:
        bot.send_message(message.chat.id,
                         f"👋 Welcome {user.first_name}!\n\n📍 Please start with /dd to fill Deal Info Form.")

# ================= BUTTON CALLBACKS =================

@bot.callback_query_handler(func=lambda call: True)
def callbacks(call):
    if call.data == "show_commands":
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("Back 🔙", callback_data="back_start"))
        bot.edit_message_text(AVAILABLE_COMMANDS, call.message.chat.id, call.message.message_id, reply_markup=kb)
    elif call.data == "show_contact":
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("Back 🔙", callback_data="back_start"))
        bot.edit_message_text(CONTACT_TEXT, call.message.chat.id, call.message.message_id, reply_markup=kb)
    elif call.data == "show_instructions":
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("Back 🔙", callback_data="back_start"))
        bot.edit_message_text(INSTRUCTIONS_TEXT, call.message.chat.id, call.message.message_id, reply_markup=kb)
    elif call.data == "show_terms":
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("Back 🔙", callback_data="back_start"))
        bot.edit_message_text(TERMS_TEXT, call.message.chat.id, call.message.message_id, reply_markup=kb)
    elif call.data == "back_start":
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("Available Commands", callback_data="show_commands"))
        kb.add(types.InlineKeyboardButton("☎️ Contact", callback_data="show_contact"))
        kb.row(types.InlineKeyboardButton("Instructions", callback_data="show_instructions"),
               types.InlineKeyboardButton("Terms", callback_data="show_terms"))
        kb.row(types.InlineKeyboardButton("Update Channel", url=UPDATE_CHANNEL_URL),
               types.InlineKeyboardButton("Vouch Channel", url=VOUCH_CHANNEL_URL))
        bot.edit_message_text("Your Trustworthy Telegram Escrow Service", call.message.chat.id, call.message.message_id, reply_markup=kb)

# ================= POLLING =================

bot.polling(non_stop=True, allowed_updates=["message", "callback_query"])
