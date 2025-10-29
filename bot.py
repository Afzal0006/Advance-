import re
import random
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from pymongo import MongoClient

# ---------------- CONFIG ----------------
BOT_TOKEN = "7643831340:AAGieuPJND4MekAutSf3xzta1qdoKo5mbZU"
MONGO_URI = "mongodb+srv://TRUSTLYTRANSACTIONBOT:TRUSTLYTRANSACTIONBOT@cluster0.t60mxb7.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
LOG_CHANNEL_ID = -1003067720865

# Multiple owner IDs
OWNER_IDS = [6998916494]  # Add other owner IDs as needed

# --------------- LOGGING ----------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --------------- MONGO ------------------
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

# --------------- HELPERS ----------------
async def is_admin(update: Update) -> bool:
    """Return True if user is owner or listed admin in DB."""
    if not update.effective_user:
        return False
    user_id = update.effective_user.id
    if user_id in OWNER_IDS:
        return True
    return admins_col.find_one({"user_id": user_id}) is not None

def init_group(chat_id: str):
    """Create group doc if missing."""
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
    """Update per-group and global stats (not fully atomic but OK for most uses)."""
    init_group(group_id)
    g = groups_col.find_one({"_id": group_id})
    # Update group stats
    g["total_deals"] = g.get("total_deals", 0) + 1
    g["total_volume"] = g.get("total_volume", 0) + amount
    escrowers = g.get("escrowers", {})
    escrowers[escrower] = escrowers.get(escrower, 0) + amount
    g["escrowers"] = escrowers
    groups_col.update_one({"_id": group_id}, {"$set": g})

    # Update global stats
    global_data = global_col.find_one({"_id": "stats"})
    global_data["total_deals"] = global_data.get("total_deals", 0) + 1
    global_data["total_volume"] = global_data.get("total_volume", 0) + amount
    g_esc = global_data.get("escrowers", {})
    g_esc[escrower] = g_esc.get(escrower, 0) + amount
    global_data["escrowers"] = g_esc
    global_col.update_one({"_id": "stats"}, {"$set": global_data})

def extract_username_from_user(user):
    """Return username or full name"""
    if not user:
        return "Unknown"
    if getattr(user, "username", None):
        return f"@{user.username}"
    return user.full_name or str(user.id)

# --------------- COMMANDS ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "✨ <b>Welcome to Escrower Bot!</b> ✨\n\n"
        "• /add <code>amount</code> – Add a new deal (reply to DEAL INFO message)\n"
        "• /complete <code>amount</code> – Complete a deal (reply to DEAL INFO message)\n"
        "• /status <code>trade_id</code> – Check deal status by Trade ID\n"
        "• /stats – Your personal stats\n"
        "• /gstats – Global stats (Admin only)\n"
        "• /allstats – All users stats (Admin only)\n"
        "• /addadmin <code>user_id</code> – Owner only\n"
        "• /removeadmin <code>user_id</code> – Owner only\n"
        "• /adminlist – Show all admins\n"
        "• /pending – Show pending deals (admins see all, users see their own)\n"
    )
    if update.message:
        await update.message.reply_text(msg, parse_mode="HTML")

async def add_deal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update):
        return
    if not update.message:
        return
    try:
        await update.message.delete()
    except Exception:
        pass

    if not update.message.reply_to_message:
        return await update.message.reply_text("❌ Reply to the DEAL INFO message!")

    if not context.args or not context.args[0].replace(".", "", 1).isdigit():
        return await update.message.reply_text("❌ Please provide amount like /add 50")

    amount = float(context.args[0])
    original_text = update.message.reply_to_message.text or ""
    chat_id = str(update.effective_chat.id)
    reply_id = str(update.message.reply_to_message.message_id)
    init_group(chat_id)

    buyer_match = re.search(r"BUYER\s*:\s*(@\w+)", original_text, re.IGNORECASE)
    seller_match = re.search(r"SELLER\s*:\s*(@\w+)", original_text, re.IGNORECASE)

    buyer = buyer_match.group(1).strip() if buyer_match else "Unknown"
    seller = seller_match.group(1).strip() if seller_match else "Unknown"

    g = groups_col.find_one({"_id": chat_id})
    deals = g.get("deals", {}) or {}
    # generate trade id (no # stored)
    trade_id = f"TID{random.randint(100000, 999999)}"
    # Ensure uniqueness (try a few times)
    tries = 0
    while any(d.get("trade_id") == trade_id for d in deals.values()) and tries < 5:
        trade_id = f"TID{random.randint(100000, 999999)}"
        tries += 1

    deals[reply_id] = {
        "trade_id": trade_id,
        "added_amount": amount,
        "completed": False,
        "buyer": buyer,
        "seller": seller
    }

    g["deals"] = deals
    groups_col.update_one({"_id": chat_id}, {"$set": g})

    escrower = extract_username_from_user(update.effective_user)
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
    await update.effective_chat.send_message(msg,
                                            reply_to_message_id=update.message.reply_to_message.message_id,
                                            parse_mode="HTML")

async def complete_deal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update):
        return
    if not update.message:
        return
    try:
        await update.message.delete()
    except Exception:
        pass

    if not update.message.reply_to_message:
        return await update.message.reply_text("❌ Reply to the DEAL INFO message!")

    if not context.args or not context.args[0].replace(".", "", 1).isdigit():
        return await update.message.reply_text("❌ Please provide amount like /complete 50")

    released = float(context.args[0])

    chat_id = str(update.effective_chat.id)
    reply_id = str(update.message.reply_to_message.message_id)
    g = groups_col.find_one({"_id": chat_id}) or {}
    deal_info = g.get("deals", {}).get(reply_id)

    if not deal_info:
        return await update.message.reply_text("❌ Deal not found!")
    if deal_info.get("completed"):
        return await update.message.reply_text("⚠️ Already completed!")

    deal_info["completed"] = True
    g["deals"][reply_id] = deal_info

    added_amount = float(deal_info.get("added_amount", 0))
    fee = added_amount - released if added_amount > released else 0.0

    g["total_fee"] = g.get("total_fee", 0.0) + fee
    groups_col.update_one({"_id": chat_id}, {"$set": g})

    global_data = global_col.find_one({"_id": "stats"}) or {}
    global_data["total_fee"] = global_data.get("total_fee", 0.0) + fee
    global_col.update_one({"_id": "stats"}, {"$set": global_data})

    buyer = deal_info.get("buyer", "Unknown")
    seller = deal_info.get("seller", "Unknown")
    escrower = extract_username_from_user(update.effective_user)
    trade_id = deal_info.get("trade_id", "N/A")

    msg = (
        f"✅ <b>Deal Completed!</b>\n"
        "────────────────\n"
        f"👤 Buyer  : {buyer}\n"
        f"👤 Seller  : {seller}\n"
        f"💸 Released : ₹{released}\n"
        f"🆔 Trade ID : #{trade_id}\n"
        f"💰 Fee     : ₹{fee}\n"
        "────────────────\n"
        f"🛡️ Escrowed by {escrower}"
    )
    await update.effective_chat.send_message(msg,
                                            reply_to_message_id=update.message.reply_to_message.message_id,
                                            parse_mode="HTML")

    # Send a log to the private log channel (if set)
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
    except Exception as e:
        logger.warning("Failed to send log message: %s", e)

async def deal_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    if not context.args:
        return await update.message.reply_text("❌ Usage: /status <trade_id>")

    trade_id = context.args[0].strip().replace("#", "").upper()
    found = None

    # Search all groups for trade_id
    for g in groups_col.find({}):
        for deal in (g.get("deals") or {}).values():
            if deal and str(deal.get("trade_id", "")).upper() == trade_id:
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

async def global_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update):
        return
    g = global_col.find_one({"_id": "stats"}) or {}
    escrowers_text = "\n".join([f"{name} = ₹{amt}" for name, amt in g.get("escrowers", {}).items()]) or "No deals yet"
    msg = (
        f"🌍 Global Stats\n\n"
        f"{escrowers_text}\n\n"
        f"🔹 Total Deals: {g.get('total_deals', 0)}\n"
        f"💰 Total Volume: ₹{g.get('total_volume', 0)}\n"
        f"💸 Total Fee: ₹{g.get('total_fee', 0.0)}"
    )
    await update.message.reply_text(msg)

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    user = update.effective_user
    username = f"@{user.username}" if user.username else user.full_name
    user_check = username.lower().strip()

    total_deals = 0
    total_volume = 0
    ongoing_deals = 0
    highest_deal = 0

    all_users = {}

    for g in groups_col.find({}):
        for deal in (g.get("deals") or {}).values():
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

async def all_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update):
        return await update.message.reply_text("❌ Only admins can use this command!")

    users_data = {}

    for g in groups_col.find({}):
        for deal in (g.get("deals") or {}).values():
            if not deal:
                continue

            buyer = str(deal.get("buyer", "")).strip()
            seller = str(deal.get("seller", "")).strip()
            amount = deal.get("added_amount", 0)

            if buyer.startswith("@"):
                if buyer not in users_data:
                    users_data[buyer] = {"deals": 0, "volume": 0, "highest": 0}
                users_data[buyer]["deals"] += 1
                users_data[buyer]["volume"] += amount
                users_data[buyer]["highest"] = max(users_data[buyer]["highest"], amount)

            if seller.startswith("@"):
                if seller not in users_data:
                    users_data[seller] = {"deals": 0, "volume": 0, "highest": 0}
                users_data[seller]["deals"] += 1
                users_data[seller]["volume"] += amount
                users_data[seller]["highest"] = max(users_data[seller]["highest"], amount)

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

# --------------- ADMIN CONTROLS -------------
async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
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
    if not update.message:
        return
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

# --------------- PENDING DEALS -------------
async def pending_deals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    user = update.effective_user
    username = f"@{user.username}" if user.username else user.full_name
    user_check = username.lower().strip()
    isAdmin = await is_admin(update)

    chat_id = str(update.effective_chat.id)
    g = groups_col.find_one({"_id": chat_id})

    if not g or not g.get("deals"):
        return await update.message.reply_text("🎉 No pending deals found in this group!")

    pending_list = []

    for reply_id, deal in (g.get("deals") or {}).items():
        if not deal: 
            continue
        if deal.get("completed"):
            continue

        buyer = str(deal.get("buyer", "")).lower()
        seller = str(deal.get("seller", "")).lower()

        # Admin sees all pending in this group; normal user sees only their deals
        if isAdmin or (user_check == buyer or user_check == seller):
            pending_list.append(deal)

    if not pending_list:
        return await update.message.reply_text("🎉 No pending deals found for you!")

    text = "🔄 <b>Pending Deals (this group)</b>\n\n"

    for i, deal in enumerate(pending_list[:50], start=1):  # show up to 50
        text += (
            f"{i}. 🆔 #{deal['trade_id']} — ₹{deal['added_amount']}\n"
            f"👤 Buyer: {deal['buyer']}\n"
            f"👤 Seller: {deal['seller']}\n"
            "────────────────\n"
        )

    await update.message.reply_text(text, parse_mode="HTML")

# --------------- MAIN --------------------
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_deal))
    app.add_handler(CommandHandler("complete", complete_deal))
    app.add_handler(CommandHandler("status", deal_status))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("gstats", global_stats))
    app.add_handler(CommandHandler("allstats", all_stats))
    app.add_handler(CommandHandler("addadmin", add_admin))
    app.add_handler(CommandHandler("removeadmin", remove_admin))
    app.add_handler(CommandHandler("adminlist", admin_list))
    app.add_handler(CommandHandler("pending", pending_deals))
    # you can register more handlers here...

    logger.info("Bot started... ✅")
    app.run_polling()

if __name__ == "__main__":
    main()
