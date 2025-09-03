import re
import random
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from pymongo import MongoClient

# ==== CONFIG ====
BOT_TOKEN = "7095431388:AAEbznnr85faroUd4IdYtLVXPw7zGD8Jj4Q"
MONGO_URI = "mongodb+srv://TRUSTLYTRANSACTIONBOT:TRUSTLYTRANSACTIONBOT@cluster0.t60mxb7.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
LOG_CHANNEL_ID = -1002826823679

# Multiple owner IDs
OWNER_IDS = [6998916494]

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
        "escrowers": {}  # ye holding balance ke liye use hoga
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
            "escrowers": {}  # group wise holding balance
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
        "• /add <code>amount</code> – Add a new deal (hold money)\n"
        "• /complete <code>amount</code> – Complete a deal (release money)\n"
        "• /holding – Show escrower holding balances\n"
        "• /gstats – Global stats (Admin only)\n"
        "• /addadmin <code>user_id</code> – Owner only\n"
        "• /removeadmin <code>user_id</code> – Owner only\n"
        "• /adminlist – Show all admins"
    )
    await update.message.reply_text(msg, parse_mode="HTML")

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

    buyer = buyer_match.group(1) if buyer_match else "Unknown"
    seller = seller_match.group(1) if seller_match else "Unknown"

    g = groups_col.find_one({"_id": chat_id})
    deals = g["deals"]
    trade_id = f"TID{random.randint(100000, 999999)}"
    deals[reply_id] = {
        "trade_id": trade_id,
        "added_amount": amount,
        "completed": False
    }

    g["deals"] = deals
    groups_col.update_one({"_id": chat_id}, {"$set": g})

    escrower = f"@{update.effective_user.username}" if update.effective_user.username else update.effective_user.full_name
    update_escrower_stats(chat_id, escrower, amount)

    msg = (
        f"✅ <b>Amount Received & On Hold!</b>\n"
        "────────────────\n"
        f"👤 Buyer : {buyer}\n"
        f"👤 Seller : {seller}\n"
        f"💰 Amount : ₹{amount}\n"
        f"🆔 Trade ID : #{trade_id}\n"
        "────────────────\n"
        f"🛡️ Escrowed by {escrower}"
    )
    await update.effective_chat.send_message(msg, reply_to_message_id=update.message.reply_to_message.message_id, parse_mode="HTML")

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

    # ✅ Calculate fee
    added_amount = deal_info["added_amount"]
    fee = added_amount - released if added_amount > released else 0
    g["total_fee"] += fee
    groups_col.update_one({"_id": chat_id}, {"$set": g})

    global_data = global_col.find_one({"_id": "stats"})
    global_data["total_fee"] += fee

    # ✅ Holding se release amount minus karna
    escrower = f"@{update.effective_user.username}" if update.effective_user.username else update.effective_user.full_name
    if escrower in g["escrowers"]:
        g["escrowers"][escrower] = max(0, g["escrowers"][escrower] - released)
    if escrower in global_data["escrowers"]:
        global_data["escrowers"][escrower] = max(0, global_data["escrowers"][escrower] - released)

    groups_col.update_one({"_id": chat_id}, {"$set": g})
    global_col.update_one({"_id": "stats"}, {"$set": global_data})

    buyer_match = re.search(r"BUYER\s*:\s*(@\w+)", update.message.reply_to_message.text, re.IGNORECASE)
    seller_match = re.search(r"SELLER\s*:\s*(@\w+)", update.message.reply_to_message.text, re.IGNORECASE)
    buyer = buyer_match.group(1) if buyer_match else "Unknown"
    seller = seller_match.group(1) if seller_match else "Unknown"
    trade_id = deal_info["trade_id"]

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
    await update.effective_chat.send_message(msg, reply_to_message_id=update.message.reply_to_message.message_id, parse_mode="HTML")

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

async def holding(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    g = groups_col.find_one({"_id": chat_id})
    if not g or not g.get("escrowers"):
        return await update.message.reply_text("⚠️ No holdings in this group yet.")

    escrowers_text = "\n".join([f"{name} = ₹{amt}" for name, amt in g["escrowers"].items()]) or "No deals yet"
    total_holding = sum(g["escrowers"].values())

    msg = (
        f"📊 <b>Holding Balances</b>\n\n"
        f"{escrowers_text}\n\n"
        f"🔹 Total Holding: ₹{total_holding}"
    )
    await update.message.reply_text(msg, parse_mode="HTML")

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

# ==== ADMIN COMMANDS ====
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

# ==== MAIN ====
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_deal))
    app.add_handler(CommandHandler("complete", complete_deal))
    app.add_handler(CommandHandler("holding", holding))
    app.add_handler(CommandHandler("gstats", global_stats))
    app.add_handler(CommandHandler("addadmin", add_admin))
    app.add_handler(CommandHandler("removeadmin", remove_admin))
    app.add_handler(CommandHandler("adminlist", admin_list))
    print("Bot started... ✅")
    app.run_polling()

if __name__ == "__main__":
    main()
