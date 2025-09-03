import re
import random
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from pymongo import MongoClient

# ==== CONFIG ====
BOT_TOKEN = "YOUR_BOT_TOKEN"
MONGO_URI = "YOUR_MONGO_URI"
LOG_CHANNEL_ID = -1002161414780

# Multiple owner IDs
OWNER_IDS = [6998916494]  # Add as many IDs as you want

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

# ==== COMMANDS ====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "✨ <b>Welcome to Escrower Bot!</b> ✨\n\n"
        "• /add <code>amount</code> – Add a new deal\n"
        "• /complete <code>amount</code> – Complete a deal\n"
        "• /stats – Group stats\n"
        "• /gstats – Global stats (Admin only)\n"
        "• /mystats – Your buyer/seller stats (Global)\n"
        "• /allstats – All users stats (Admin only)\n"
        "• /status <code>trade_id</code> – Check deal status (Admin only)\n"
        "• /addadmin <code>user_id</code> – Owner only\n"
        "• /removeadmin <code>user_id</code> – Owner only\n"
        "• /adminlist – Show all admins"
    )
    await update.message.reply_text(msg, parse_mode="HTML")

# ==== /add ====
async def add_deal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update):
        return
    try: await update.message.delete()
    except: pass

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
    trade_id = f"TID{random.randint(100000, 999999)}"
    escrower = f"@{update.effective_user.username}" if update.effective_user.username else update.effective_user.full_name

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
    await update.effective_chat.send_message(msg, reply_to_message_id=update.message.reply_to_message.message_id, parse_mode="HTML")

# ==== /complete ====
async def complete_deal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update): return
    try: await update.message.delete()
    except: pass

    if not update.message.reply_to_message:
        return await update.message.reply_text("❌ Reply to the DEAL INFO message!")
    if not context.args or not context.args[0].replace(".", "", 1).isdigit():
        return await update.message.reply_text("❌ Please provide amount like /complete 50")

    released = float(context.args[0])
    chat_id = str(update.effective_chat.id)
    reply_id = str(update.message.reply_to_message.message_id)
    g = groups_col.find_one({"_id": chat_id})
    deal_info = g["deals"].get(reply_id)

    if not deal_info: return await update.message.reply_text("❌ Deal not found!")
    if deal_info["completed"]: return await update.message.reply_text("⚠️ Already completed!")

    deal_info["completed"] = True
    deal_info["released"] = released
    added_amount = deal_info["added_amount"]
    fee = added_amount - released if added_amount > released else 0
    deal_info["fee"] = fee
    g["deals"][reply_id] = deal_info
    g["total_fee"] += fee
    groups_col.update_one({"_id": chat_id}, {"$set": g})

    global_data = global_col.find_one({"_id": "stats"})
    global_data["total_fee"] += fee
    global_col.update_one({"_id": "stats"}, {"$set": global_data})

    buyer = deal_info.get("buyer", "Unknown")
    seller = deal_info.get("seller", "Unknown")
    escrower = deal_info.get("escrower", "Unknown")
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

# ==== /status ====
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update):
        return await update.message.reply_text("❌ Only admins can use this command!")
    if not context.args:
        return await update.message.reply_text("❌ Usage: /status <Trade ID>")

    trade_id = context.args[0].replace("#", "").upper()
    found = None
    for g in groups_col.find({}):
        for deal in g.get("deals", {}).values():
            if deal.get("trade_id") == trade_id:
                found = deal
                break
        if found: break

    if not found: return await update.message.reply_text(f"❌ Trade ID {trade_id} not found!")

    buyer = found.get("buyer", "Unknown")
    seller = found.get("seller", "Unknown")
    amount = found.get("added_amount", 0)
    escrower = found.get("escrower", "Unknown")
    completed = found.get("completed", False)

    if completed:
        released = found.get("released", 0)
        fee = found.get("fee", 0)
        status_text = (
            f"📌 <b>Trade Status</b>\n\n"
            f"🆔 Trade ID : #{trade_id}\n"
            f"👤 Buyer    : {buyer}\n"
            f"👤 Seller   : {seller}\n"
            f"💰 Amount   : ₹{amount}\n"
            f"💸 Released : ₹{released}\n"
            f"💰 Fee      : ₹{fee}\n"
            f"🛡️ Escrowed by {escrower}\n"
            f"📊 Status   : ✅ Completed"
        )
    else:
        status_text = (
            f"📌 <b>Trade Status</b>\n\n"
            f"🆔 Trade ID : #{trade_id}\n"
            f"👤 Buyer    : {buyer}\n"
            f"👤 Seller   : {seller}\n"
            f"💰 Amount   : ₹{amount}\n"
            f"🛡️ Escrowed by {escrower}\n"
            f"📊 Status   : ⏳ Pending"
        )

    await update.message.reply_text(status_text, parse_mode="HTML")

# ==== /stats ====
async def group_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    init_group(chat_id)
    g = groups_col.find_one({"_id": chat_id})
    escrowers_text = "\n".join([f"{name} = ₹{amt}" for name, amt in g["escrowers"].items()]) or "No deals yet"
    msg = (
        f"📊 Group Stats\n\n"
        f"{escrowers_text}\n\n"
        f"🔹 Total Deals: {g['total_deals']}\n"
        f"💰 Total Volume: ₹{g['total_volume']}\n"
        f"💸 Total Fee: ₹{g['total_fee']}"
    )
    await update.message.reply_text(msg)

# ==== /gstats ====
async def global_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update): return
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

# ==== /mystats ====
async def my_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = f"@{update.effective_user.username}" if update.effective_user.username else update.effective_user.full_name
    total_buyer, total_seller = 0, 0
    for g in groups_col.find({}):
        for d in g.get("deals", {}).values():
            if d.get("buyer") == user:
                total_buyer += d.get("added_amount", 0)
            if d.get("seller") == user:
                total_seller += d.get("added_amount", 0)
    msg = (
        f"📊 My Stats\n\n"
        f"🛒 As Buyer : ₹{total_buyer}\n"
        f"🏷️ As Seller: ₹{total_seller}"
    )
    await update.message.reply_text(msg)

# ==== /allstats ====
async def all_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update): return
    stats = {}
    for g in groups_col.find({}):
        for d in g.get("deals", {}).values():
            buyer, seller = d.get("buyer", "Unknown"), d.get("seller", "Unknown")
            stats[buyer] = stats.get(buyer, 0) + d.get("added_amount", 0)
            stats[seller] = stats.get(seller, 0) + d.get("added_amount", 0)
    text = "\n".join([f"{u}: ₹{amt}" for u, amt in stats.items()]) or "No deals yet"
    await update.message.reply_text(f"📊 All Users Stats\n\n{text}")

# ==== Admin system (/addadmin, /removeadmin, /adminlist) ====
async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in OWNER_IDS:
        return await update.message.reply_text("❌ Only owners can add admins!")
    if not context.args: return await update.message.reply_text("Usage: /addadmin user_id")
    uid = int(context.args[0])
    admins_col.update_one({"user_id": uid}, {"$set": {"user_id": uid}}, upsert=True)
    await update.message.reply_text(f"✅ Added {uid} as admin.")

async def remove_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in OWNER_IDS:
        return await update.message.reply_text("❌ Only owners can remove admins!")
    if not context.args: return await update.message.reply_text("Usage: /removeadmin user_id")
    uid = int(context.args[0])
    admins_col.delete_one({"user_id": uid})
    await update.message.reply_text(f"✅ Removed {uid} from admins.")

async def admin_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admins = [str(a["user_id"]) for a in admins_col.find({})]
    text = "\n".join(admins) or "No admins yet"
    await update.message.reply_text(f"👮 Admins:\n{text}")

# ==== MAIN ====
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_deal))
    app.add_handler(CommandHandler("complete", complete_deal))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("stats", group_stats))
    app.add_handler(CommandHandler("gstats", global_stats))
    app.add_handler(CommandHandler("mystats", my_stats))
    app.add_handler(CommandHandler("allstats", all_stats))
    app.add_handler(CommandHandler("addadmin", add_admin))
    app.add_handler(CommandHandler("removeadmin", remove_admin))
    app.add_handler(CommandHandler("adminlist", admin_list))
    print("Bot started... ✅")
    app.run_polling()

if __name__ == "__main__":
    main()
