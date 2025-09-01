from telebot import TeleBot, types
from pymongo import MongoClient
import re
from datetime import datetime, timedelta

# ================= CONFIG =================
BOT_TOKEN = "6098583669:AAE64kFMI_JE6BpgUKyBszq13LdvTgfnsjY"
MONGO_URI = "mongodb+srv://afzal99550:afzal99550@cluster0.aqmbh9q.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

bot = TeleBot(BOT_TOKEN, parse_mode="HTML")
client = MongoClient(MONGO_URI)
db = client['escrow_bot']
users_collection = db['users']
deals_collection = db['deals']

# ================= HELPERS =================
def tag_user_by_id(user_id, first_name):
    return f"<a href='tg://user?id={user_id}'>{first_name}</a>"

def get_indian_time():
    return datetime.utcnow() + timedelta(hours=5, minutes=30)

# ================= /seller =================
@bot.message_handler(commands=['seller'])
def seller(message):
    user_tag = tag_user_by_id(message.from_user.id, message.from_user.first_name)
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

    deal = deals_collection.find_one({"chat_id": message.chat.id}) or {}
    if deal.get("seller_address"):
        bot.send_message(message.chat.id,
                         f"{user_tag} ❌ Seller already set!",
                         parse_mode="HTML", reply_to_message_id=message.message_id)
        return

    deals_collection.update_one({"chat_id": message.chat.id},
                                {"$set": {"seller_id": message.from_user.id, "seller_address": seller_address}},
                                upsert=True)
    bot.send_message(message.chat.id,
                     f"{user_tag} ✅ Seller set successfully!\n\nNow use /use_token to choose crypto.",
                     parse_mode="HTML",
                     reply_to_message_id=message.message_id)

# ================= /buyer =================
@bot.message_handler(commands=['buyer'])
def buyer(message):
    user_tag = tag_user_by_id(message.from_user.id, message.from_user.first_name)
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

    deal = deals_collection.find_one({"chat_id": message.chat.id}) or {}
    if deal.get("buyer_address"):
        bot.send_message(message.chat.id,
                         f"{user_tag} ❌ Buyer already set!",
                         parse_mode="HTML", reply_to_message_id=message.message_id)
        return

    deals_collection.update_one({"chat_id": message.chat.id},
                                {"$set": {"buyer_id": message.from_user.id, "buyer_address": buyer_address}},
                                upsert=True)
    bot.send_message(message.chat.id,
                     f"{user_tag} ✅ Buyer set successfully!\n\nNow use /use_token to choose crypto.",
                     parse_mode="HTML",
                     reply_to_message_id=message.message_id)

# ================= /use_token =================
@bot.message_handler(commands=['use_token'])
def use_token(message):
    deal = deals_collection.find_one({"chat_id": message.chat.id})
    if not deal or not deal.get("seller_address") or not deal.get("buyer_address"):
        bot.send_message(message.chat.id,
                         "Both Seller and Buyer must be set before choosing token.",
                         reply_to_message_id=message.message_id)
        return

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("BEP20 ✅", callback_data="token_bep20"))
    bot.send_message(message.chat.id, "Choose your crypto token:", reply_markup=kb)

# ================= BUTTON CALLBACK =================
@bot.callback_query_handler(func=lambda call: True)
def callbacks(call):
    if call.data == "token_bep20":
        deal = deals_collection.find_one({"chat_id": call.message.chat.id})
        if not deal:
            bot.answer_callback_query(call.id, "Deal not found!")
            return

        deals_collection.update_one({"chat_id": call.message.chat.id},
                                    {"$set": {"token": "BEP20", "bep20_agree": False}},
                                    upsert=True)

        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("Agree ✅", callback_data="bep20_agree"))
        bot.edit_message_text("BEP20 selected. Waiting for both parties to agree:", call.message.chat.id, call.message.message_id, reply_markup=kb)

    elif call.data == "bep20_agree":
        deal = deals_collection.find_one({"chat_id": call.message.chat.id})
        if not deal:
            bot.answer_callback_query(call.id, "Deal not found!")
            return

        # Mark this user as agreed
        if "agreed_users" not in deal:
            deal["agreed_users"] = []
        if call.from_user.id not in deal["agreed_users"]:
            deal["agreed_users"].append(call.from_user.id)
            deals_collection.update_one({"chat_id": call.message.chat.id}, {"$set": {"agreed_users": deal["agreed_users"]}})

        if len(deal["agreed_users"]) < 2:
            bot.answer_callback_query(call.id, "Waiting for the other party to agree.")
        else:
            # Both agreed, send Transaction Info
            seller_tag = tag_user_by_id(deal["seller_id"], bot.get_chat(deal["seller_id"]).first_name)
            buyer_tag = tag_user_by_id(deal["buyer_id"], bot.get_chat(deal["buyer_id"]).first_name)
            indian_time = get_indian_time().strftime("%d-%m-%Y %H:%M:%S")
            msg = (f"📍 TRANSACTION INFORMATION\n\n"
                   f"⚡️ SELLER\n{seller_tag}\n{deal['seller_address']}\n\n"
                   f"⚡️ BUYER\n{buyer_tag}\n{deal['buyer_address']}\n\n"
                   f"⏰ Trade Start Time: {indian_time}\n\n"
                   f"⚠️ IMPORTANT: Make sure to finalise and agree each-others terms before depositing.\n\n"
                   f"🗒 Please use /deposit command to generate a deposit address for your trade.")
            bot.edit_message_text(msg, call.message.chat.id, call.message.message_id)
