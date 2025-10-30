import re
import random
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from pymongo import MongoClient

# ==== CONFIG ====
BOT_TOKEN = "7643831340:AAGieuPJND4MekAutSf3xzta1qdoKo5mbZU"
MONGO_URI = "mongodb+srv://TRUSTLYTRANSACTIONBOT:TRUSTLYTRANSACTIONBOT@cluster0.t60mxb7.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
LOG_CHANNEL_ID = -1003067720865

OWNER_IDS = [6998916494]  # Add as many owners as needed

# ==== MONGO CONNECT ====
client = MongoClient(MONGO_URI)
db = client["escrow_bot"]
groups_col = db["groups"]
global_col = db["global"]
admins_col = db["admins"]

# Ensure global doc exists
if not global_col.find_one({"_id": "stats"}):
    global_col.insert_one({
        "_id": "stats",
        "total_deals": 0,
        "total_volume": 0,
        "total_fee": 0.0,
        "escrowers": {}
    })

# ==== HELPERS ====
async def is_admin(update: Update) -> bool:
    user_id = update.effective_user.id
    if user_id in OWNER_IDS:
        return True
    return admins_col.find_one({"user_id": user_id}) is not None

def init_group(chat_id: str):
    if not groups_col.find_one({"_id": chat_id}):
        groups_col.insert_one({
            "_id": chat_id,
            "deals": {},
            "total_deals": 0,
            "total_volume": 0,
            "total_fee": 0.0,
            "escrowers": {}
        })

def update_escrower_stats(group_id: str, escrower: str, amount: float):
    g = groups_col.find_one({"_id": group_id})
    g["total_deals"] += 1
    g["total_volume"] += amount
    g["escrowers"][escrower] = g["escrowers"].get(escrower, 0) + amount
    groups_col.update_one({"_id": group_id}, {"$set": g})

    global_data = global_col.find_one({"_id": "stats"})
    global_data["total_deals"] += 1
    global_data["total_volume"] += amount
    global_data["escrowers"][escrower] = global_data["escrowers"].get(escrower, 0) + amount
    global_col.update_one({"_id": "stats"}, {"$set": global_data})

def extract_username_from_user(user):
    return f"@{user.username}" if user.username else user.full_name

# ==== COMMANDS ====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "✨ <b>Welcome to Escrower Bot!</b> ✨\n\n"
        "• /add <code>amount</code> – Add a new deal\n"
        "• /complete <code>amount</code> – Complete a deal (reply-based)\n"
        "• /update <code>trade_id</code> – Complete deal by Trade ID (0% fee)\n"
        "• /status <code>trade_id</code> – Check deal status by Trade ID\n"
        "• /stats – Your personal stats\n"
        "• /gstats – Global stats (Admin only)\n"
        "• /allstats – All users stats (Admin only)\n"
        "• /pending – View pending deals\n"
        "• /addadmin <code>user_id</code> – Owner only\n"
        "• /removeadmin <code>user_id</code> – Owner only\n"
        "• /adminlist – Show all admins"
    )
    await update.message.reply_text(msg, parse_mode="HTML")

# ==== Add deal ====
async def add_deal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update):
        return
    try:
        await update.message.delete()
    except:
        pass

    if not update.message.reply_to_message:
        return await update.message.reply_text("❌ Reply to the DEAL INFO message!")

    if not context.args or not context.args[0].replace(".", "", 1).isdigit():
        return await update.message.reply_text("❌ Please provide amount like /add 50")

    amount = float(context.args[0])
    original_text = update.message.reply_to_message.text
    chat_id = str(update.effective_chat.id)
    reply_id = str(update.message.reply_to_message.message_id)
    init_group(chat_id)

    buyer_match = re.search(r"BUYER\s*:\s*(@\w+)", original_text, re.IGNORECASE)
    seller_match = re.search(r"SELLER\s*:\s*(@\w+)", original_text, re.IGNORECASE)

    buyer = buyer_match.group(1).strip() if buyer_match else "Unknown"
    seller = seller_match.group(1).strip() if seller_match else "Unknown"

    g = groups_col.find_one({"_id": chat_id})
    deals = g["deals"]

    escrower = extract_username_from_user(update.effective_user)
    trade_id = f"TID{random.randint(100000, 999999)}"

    # ✅ Added "escrower" field
    deals[reply_id] = {
        "trade_id": trade_id,
        "added_amount": amount,
        "completed": False,
        "buyer": buyer,
        "seller": seller,
        "escrower": escrower
    }

    g["deals"] = deals
    groups_col.update_one({"_id": chat_id}, {"$set": g})

    update_escrower_stats(chat_id, escrower, amount)

    msg = (
        f"✅ <b>Amount Received!</b>\n"
        "────────────────\n"
        f"👤 Buyer : {buyer}\n"
        f"👤 Seller : {seller}\n"
        f"💰 Amount : ₹{amount}\n"
        f"🆔 Trade ID : #{trade_id}\n"
        "────────────────\n"
        f"🛡️ Escrowed by {escrower}"
    )

    await update.effective_chat.send_message(
        msg,
        reply_to_message_id=update.message.reply_to_message.message_id,
        parse_mode="HTML"
    )
# ==== Complete deal (reply-based) ====
async def complete_deal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update):
        return
    try:
        await update.message.delete()
    except:
        pass
    if not update.message.reply_to_message:
        return await update.message.reply_text("❌ Reply to the DEAL INFO message!")

    if not context.args or not context.args[0].replace(".", "", 1).isdigit():
        return await update.message.reply_text("❌ Please provide amount like /complete 50")

    released = float(context.args[0])
    chat_id = str(update.effective_chat.id)
    reply_id = str(update.message.reply_to_message.message_id)
    g = groups_col.find_one({"_id": chat_id})
    deal_info = g["deals"].get(reply_id)

    if not deal_info:
        return await update.message.reply_text("❌ Deal not found!")
    if deal_info["completed"]:
        return await update.message.reply_text("⚠️ Already completed!")

    deal_info["completed"] = True
    g["deals"][reply_id] = deal_info

    added_amount = deal_info["added_amount"]
    fee = added_amount - released if added_amount > released else 0

    g["total_fee"] += fee
    groups_col.update_one({"_id": chat_id}, {"$set": g})

    global_data = global_col.find_one({"_id": "stats"})
    global_data["total_fee"] += fee
    global_col.update_one({"_id": "stats"}, {"$set": global_data})

    buyer = deal_info.get("buyer", "Unknown")
    seller = deal_info.get("seller", "Unknown")
    escrower = extract_username_from_user(update.effective_user)
    trade_id = deal_info["trade_id"]

    msg = (
        f"✅ <b>Deal Completed!</b>\n"
        "────────────────\n"
        f"👤 Buyer  : {buyer}\n"
        f"👤 Seller : {seller}\n"
        f"💸 Released : ₹{released}\n"
        f"🆔 Trade ID : #{trade_id}\n"
        f"💰 Fee     : ₹{fee}\n"
        "────────────────\n"
        f"🛡️ Escrowed by {escrower}"
    )
    await update.effective_chat.send_message(msg, reply_to_message_id=update.message.reply_to_message.message_id, parse_mode="HTML")

    # Log
    try:
        log_msg = (
            "📜 <b>Deal Completed (Log)</b>\n"
            "────────────────\n"
            f"👤 Buyer   : {buyer}\n"
            f"👤 Seller  : {seller}\n"
            f"💸 Released: ₹{released}\n"
            f"🆔 Trade ID: #{trade_id}\n"
            f"💰 Fee     : ₹{fee}\n"
            f"🛡️ Escrowed by {escrower}\n"
            f"📌 Group: {update.effective_chat.title} ({update.effective_chat.id})"
        )
        await context.bot.send_message(LOG_CHANNEL_ID, log_msg, parse_mode="HTML")
    except:
        pass

# ==== Update by Trade ID (0% Fee, tag original message) ====
async def update_deal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update):
        return await update.message.reply_text("❌ Only admins can use this command!")

    if not context.args:
        return await update.message.reply_text("❌ Usage: /update <trade_id>")

    trade_id = context.args[0].strip().replace("#", "").upper()
    found = None
    chat_id = None
    reply_id = None

    # Search all groups for the trade_id
    for g in groups_col.find({}):
        for rid, deal in (g.get("deals") or {}).items():
            if deal and str(deal.get("trade_id", "")).upper() == trade_id:
                found = deal
                chat_id = g["_id"]
                reply_id = rid
                break
        if found:
            break

    if not found:
        return await update.message.reply_text("⚠️ No deal found with this Trade ID!")

    if found.get("completed"):
        return await update.message.reply_text("⚠️ Already completed!")

    # Complete deal with 0% fee
    found["completed"] = True
    g = groups_col.find_one({"_id": chat_id})
    g["deals"][reply_id] = found
    groups_col.update_one({"_id": chat_id}, {"$set": g})

    buyer = found.get("buyer", "Unknown")
    seller = found.get("seller", "Unknown")
    released = found.get("added_amount", 0)
    escrower = extract_username_from_user(update.effective_user)

    msg = (
        f"✅ <b>Deal Completed!</b> (0% Fee)\n"
        "────────────────\n"
        f"👤 Buyer  : {buyer}\n"
        f"👤 Seller : {seller}\n"
        f"💸 Released : ₹{released}\n"
        f"🆔 Trade ID : #{trade_id}\n"
        f"💰 Fee     : ₹0\n"
        "────────────────\n"
        f"🛡️ Escrowed by {escrower}"
    )

    # Send message as reply if original message exists
    try:
        if reply_id:
            await context.bot.send_message(
                chat_id=int(chat_id),
                text=msg,
                parse_mode="HTML",
                reply_to_message_id=int(reply_id)
            )
        else:
            await update.message.reply_text(msg, parse_mode="HTML")
    except:
        await update.message.reply_text(msg, parse_mode="HTML")

    # Optional log
    try:
        log_msg = (
            "📜 <b>Deal Completed by Trade ID (0% Fee)</b>\n"
            "────────────────\n"
            f"👤 Buyer  : {buyer}\n"
            f"👤 Seller : {seller}\n"
            f"💸 Released : ₹{released}\n"
            f"🆔 Trade ID : #{trade_id}\n"
            f"💰 Fee     : ₹0\n"
            f"🛡️ Escrowed by {escrower}\n"
        )
        await context.bot.send_message(LOG_CHANNEL_ID, log_msg, parse_mode="HTML")
    except:
        pass

# ==== Status by Trade ID ====
async def deal_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("❌ Usage: /status <trade_id>")

    trade_id = context.args[0].strip().replace("#", "").upper()
    found = None

    for g in groups_col.find({}):
        for deal in g.get("deals", {}).values():
            if deal and deal.get("trade_id", "").upper() == trade_id:
                found = deal
                break
        if found:
            break

    if not found:
        return await update.message.reply_text("⚠️ No deal found with this Trade ID!")

    status = "✅ Completed" if found.get("completed") else "⌛ Pending"
    msg = (
        f"📌 <b>Deal Status</b>\n"
        f"🆔 Trade ID: #{found.get('trade_id')}\n"
        f"👤 Buyer: {found.get('buyer', 'Unknown')}\n"
        f"👤 Seller: {found.get('seller', 'Unknown')}\n"
        f"💰 Amount: ₹{found.get('added_amount', 0)}\n"
        f"📊 Status: {status}"
    )
    await update.message.reply_text(msg, parse_mode="HTML")

# ==== Global stats ====
async def global_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update):
        return
    g = global_col.find_one({"_id": "stats"})
    escrowers_text = "\n".join([f"{name} = ₹{amt}" for name, amt in g["escrowers"].items()]) or "No deals yet"
    msg = (
        f"🌍 Global Stats\n\n"
        f"{escrowers_text}\n\n"
        f"🔹 Total Deals: {g['total_deals']}\n"
        f"💰 Total Volume: ₹{g['total_volume']}\n"
        f"💸 Total Fee: ₹{g['total_fee']}"
    )
    await update.message.reply_text(msg)

# ==== Personal stats ====
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    username = f"@{user.username}" if user.username else user.full_name
    user_check = username.lower().strip()

    total_deals = 0
    total_volume = 0
    ongoing_deals = 0
    highest_deal = 0
    all_users = {}

    for g in groups_col.find({}):
        for deal in g.get("deals", {}).values():
            if not deal:
                continue
            buyer = str(deal.get("buyer", "")).lower().strip()
            seller = str(deal.get("seller", "")).lower().strip()
            amount = deal.get("added_amount", 0)
            completed = deal.get("completed", False)

            if user_check == buyer or user_check == seller:
                total_deals += 1
                total_volume += amount
                highest_deal = max(highest_deal, amount)
                if not completed:
                    ongoing_deals += 1

            for u in [buyer, seller]:
                if u.startswith("@"):
                    if u not in all_users:
                        all_users[u] = {"volume": 0}
                    all_users[u]["volume"] += amount

    if total_deals == 0:
        return await update.message.reply_text("📊 No deals found for you.")

    sorted_users = sorted(all_users.items(), key=lambda x: x[1]["volume"], reverse=True)
    rank = next((i + 1 for i, (u, _) in enumerate(sorted_users) if u == user_check), "N/A")

    msg = (
        f"📊 <b>Participant Stats for {username}</b>\n\n"
        f"👑 Ranking: {rank}\n"
        f"📈 Total Volume: ₹{total_volume}\n"
        f"🧳 Total Deals: {total_deals}\n"
        f"🧿 Ongoing Deals: {ongoing_deals}\n"
        f"💳 Highest Deal - ₹{highest_deal}"
    )
    await update.message.reply_text(msg, parse_mode="HTML")

# ==== All stats (Top users) ====
async def all_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update):
        return await update.message.reply_text("❌ Only admins can use this command!")

    users_data = {}
    for g in groups_col.find({}):
        for deal in g.get("deals", {}).values():
            if not deal:
                continue
            for user_key in ["buyer", "seller"]:
                user = str(deal.get(user_key, "")).strip()
                amount = deal.get("added_amount", 0)
                if user.startswith("@"):
                    if user not in users_data:
                        users_data[user] = {"deals": 0, "volume": 0, "highest": 0}
                    users_data[user]["deals"] += 1
                    users_data[user]["volume"] += amount
                    users_data[user]["highest"] = max(users_data[user]["highest"], amount)

    if not users_data:
        return await update.message.reply_text("📊 No deals found.")

    sorted_users = sorted(users_data.items(), key=lambda x: x[1]["volume"], reverse=True)
    ranking_text = "🏆 <b>Top 5 Traders (by Volume)</b>\n\n"
    for i, (user, stats) in enumerate(sorted_users[:5], start=1):
        ranking_text += f"{i}. {user} → ₹{stats['volume']} ({stats['deals']} deals)\n"

    msg_parts = []
    for user, stats in sorted_users:
        msg_parts.append(
            f"👤 User: {user}\n"
            f"💰 Total Volume: ₹{stats['volume']}\n"
            f"🔹 Total Deals: {stats['deals']}\n"
            f"🏆 Highest Deal: ₹{stats['highest']}\n"
            "────────────────"
        )

    msg = "📊 <b>All Users Stats</b>\n\n" + ranking_text + "\n" + "\n".join(msg_parts)
    await update.message.reply_text(msg, parse_mode="HTML")

# ==== Admin commands ====
async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in OWNER_IDS:
        return await update.message.reply_text("❌ Only owners can add admins!")

    if not context.args or not context.args[0].isdigit():
        return await update.message.reply_text("❌ Provide a valid user_id, e.g. /addadmin 123456789")

    new_admin_id = int(context.args[0])
    if admins_col.find_one({"user_id": new_admin_id}):
        return await update.message.reply_text("⚠️ Already an admin!")

    admins_col.insert_one({"user_id": new_admin_id})
    await update.message.reply_text(f"✅ Added as admin: <code>{new_admin_id}</code>", parse_mode="HTML")

async def remove_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in OWNER_IDS:
        return await update.message.reply_text("❌ Only owners can remove admins!")

    if not context.args or not context.args[0].isdigit():
        return await update.message.reply_text("❌ Provide a valid user_id, e.g. /removeadmin 123456789")

    remove_id = int(context.args[0])
    if not admins_col.find_one({"user_id": remove_id}):
        return await update.message.reply_text("⚠️ This user is not an admin!")

    admins_col.delete_one({"user_id": remove_id})
    await update.message.reply_text(f"✅ Removed admin: <code>{remove_id}</code>", parse_mode="HTML")

async def admin_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update):
        return
    admins = list(admins_col.find({}, {"_id": 0, "user_id": 1}))
    owners = [f"⭐ Owner: <code>{oid}</code>" for oid in OWNER_IDS]
    admins_text = "\n".join([f"👮 Admin: <code>{a['user_id']}</code>" for a in admins]) or "No extra admins added."
    msg = "📋 <b>Admin List</b>\n\n" + "\n".join(owners) + "\n" + admins_text
    await update.message.reply_text(msg, parse_mode="HTML")

# ==== ongoing deals (Fixed, top 100) ====
async def ongoing_deals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    username = f"@{user.username}" if user.username else user.full_name
    user_check = username.lower().strip()
    isAdmin = await is_admin(update)

    # 🚫 Restrict access
    if not isAdmin:
        return await update.message.reply_text("❌ Only admins can view pending deals!")

    ongoing_list = []

    for g in groups_col.find({}):
        deals = g.get("deals") or {}
        for rid, deal in deals.items():
            if not deal:
                continue
            if deal.get("completed"):
                continue
            ongoing_list.append(deal)

    if not ongoing_list:
        return await update.message.reply_text("🎉 No ongoing deals found!")

    text = "🔄 <b>ongoing Deals (Top 100)</b>\n\n"
    for i, deal in enumerate(ongoing_list[:100], start=1):
        text += (
            f"{i}. 🆔 #{deal.get('trade_id', 'N/A')} — ₹{deal.get('added_amount', 0)}\n"
            f"👤 Buyer: {deal.get('buyer', 'Unknown')}\n"
            f"👤 Seller: {deal.get('seller', 'Unknown')}\n"
            "────────────────\n"
        )

    await update.message.reply_text(text, parse_mode="HTML")

async def holding(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    isAdmin = await is_admin(update)

    # ✅ Sirf admin hi use kar sake
    if not isAdmin:
        return await update.message.reply_text("❌ Only admins can use this command!")

    holdings = {}

    # 🔍 Har group ke deals check karte hain
    for g in groups_col.find({}):
        for deal in g.get("deals", {}).values():
            if deal and not deal.get("completed"):
                escrower = deal.get("escrower", "Unknown")
                amount = float(deal.get("added_amount", 0))
                holdings[escrower] = holdings.get(escrower, 0) + amount

    if not holdings:
        return await update.message.reply_text("🎉 No holdings found!")

    # 📊 Format output
    text = "💼 <b>Current Holdings (Pending Amounts)</b>\n\n"
    total = 0
    for i, (escrower, amount) in enumerate(sorted(holdings.items(), key=lambda x: x[1], reverse=True), start=1):
        text += f"{i}. {escrower} → ₹{amount:.2f}\n"
        total += amount

    text += f"\n────────────────\n🏦 <b>Total Hold:</b> ₹{total:.2f}"

    await update.message.reply_text(text, parse_mode="HTML")

# ==== My Deals (Simple View) ====
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler

DEALS_PER_PAGE = 50

async def mydeals(update, context, page=0):
    user = update.effective_user
    username = f"@{user.username}" if user.username else user.full_name

    # Collect all deals for user
    user_deals = []
    for g in groups_col.find({}):
        for deal in g.get("deals", {}).values():
            if deal.get("escrower") == username:
                trade_id = deal.get("trade_id", "Unknown")
                amount = float(deal.get("added_amount", 0))
                status = "✅" if deal.get("completed") else "🕒"
                user_deals.append(f"{status} #{trade_id} → ₹{amount:.2f}")

    if not user_deals:
        return await update.message.reply_text("🎉 You have no deals yet!")

    # Pagination
    start = page * DEALS_PER_PAGE
    end = start + DEALS_PER_PAGE
    deals_page = user_deals[start:end]

    text = f"📜 <b>Your Deals (Page {page+1})</b>\n────────────────\n"
    text += "\n".join(deals_page)

    # Inline buttons
    buttons = []
    if start > 0:
        buttons.append(InlineKeyboardButton("⏮️ Prev", callback_data=f"mydeals:{page-1}"))
    if end < len(user_deals):
        buttons.append(InlineKeyboardButton("Next ⏭️", callback_data=f"mydeals:{page+1}"))

    reply_markup = InlineKeyboardMarkup([buttons]) if buttons else None

    await update.message.reply_text(text, parse_mode="HTML", reply_markup=reply_markup)

# Callback for pagination
async def mydeals_callback(update, context):
    query = update.callback_query
    await query.answer()
    page = int(query.data.split(":")[1])
    await mydeals(update, context, page=page)
# ==== MAIN ====
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_deal))
    app.add_handler(CommandHandler("complete", complete_deal))
    app.add_handler(CommandHandler("update", update_deal))
    app.add_handler(CommandHandler("status", deal_status))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("gstats", global_stats))
    app.add_handler(CommandHandler("allstats", all_stats))
    app.add_handler(CommandHandler("ongoing", ongoing_deals))
    app.add_handler(CommandHandler("addadmin", add_admin))
    app.add_handler(CommandHandler("removeadmin", remove_admin))
    app.add_handler(CommandHandler("adminlist", admin_list))
    app.add_handler(CommandHandler("holding", holding))
    app.add_handler(CommandHandler("mydeals", mydeals))

    print("Bot started... ✅")
    app.run_polling()

if __name__ == "__main__":
    main()
