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

from datetime import datetime
import random, re
from telegram import Update
from telegram.ext import ContextTypes

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
from datetime import datetime

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

    # ✅ Calculate fee
    added_amount = deal_info["added_amount"]
    fee = added_amount - released if added_amount > released else 0

    # ✅ Mark deal completed, store fee & timestamp
    deal_info["completed"] = True
    deal_info["fee"] = fee
    deal_info["completed_at"] = datetime.utcnow().isoformat()

    # ✅ Re-save updated deal info
    g["deals"][reply_id] = deal_info

    # ✅ Update group & global stats
    g["total_fee"] += fee
    groups_col.update_one({"_id": chat_id}, {"$set": g})

    global_data = global_col.find_one({"_id": "stats"})
    global_data["total_fee"] += fee
    global_col.update_one({"_id": "stats"}, {"$set": global_data})

    buyer = deal_info.get("buyer", "Unknown")
    seller = deal_info.get("seller", "Unknown")
    escrower = extract_username_from_user(update.effective_user)
    trade_id = deal_info["trade_id"]

    # ✅ Send completion message
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
    await update.effective_chat.send_message(
        msg,
        reply_to_message_id=update.message.reply_to_message.message_id,
        parse_mode="HTML"
    )

    # ✅ Log to channel
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
            f"📆 Date: {datetime.utcnow().strftime('%d %b %Y, %H:%M UTC')}\n"
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

from datetime import datetime
from zoneinfo import ZoneInfo
import io
from PIL import Image, ImageDraw, ImageFont
from telegram import Update
from telegram.ext import ContextTypes

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

    # === Collect data from all groups ===
    for g in groups_col.find({}):
        for deal in g.get("deals", {}).values():
            if not deal:
                continue
            buyer = str(deal.get("buyer", "")).lower().strip()
            seller = str(deal.get("seller", "")).lower().strip()
            amount = float(deal.get("added_amount", 0))
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

    # === Rank Calculation ===
    sorted_users = sorted(all_users.items(), key=lambda x: x[1]["volume"], reverse=True)
    rank = next((i + 1 for i, (u, _) in enumerate(sorted_users) if u == user_check), "N/A")

    # === Text to Display ===
    lines = [
        f"# Participant Stats for {username}",
        "",
        f"•  Ranking: {rank}",
        f"•  Total Volume :  {total_volume:.1f} INR",
        f"•  Total Deals :  {total_deals}",
        f"•  Ongoing Deals :  {ongoing_deals}",
        f"•  Highest Deal :  {highest_deal:.1f} INR"
    ]

    # === High-resolution white image ===
    width, height = 2400, 1800
    bg_color = (255, 255, 255)
    font_color = (0, 0, 0)

    img = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(img)

    # Border
    border_color = (0, 0, 0)
    draw.rectangle([(20, 20), (width - 20, height - 20)], outline=border_color, width=10)

    # === Load crisp bold fonts ===
    try:
        title_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 100)
        font = ImageFont.truetype("DejaVuSans.ttf", 100)
    except:
        font = ImageFont.load_default()
        title_font = font

    # === Helper to make text bold/dark ===
    def draw_text_bold(draw, position, text, font, fill):
        x, y = position
        for dx in [-2, 0, 2]:
            for dy in [-2, 0, 2]:
                draw.text((x+dx, y+dy), text, font=font, fill=fill)
        draw.text((x, y), text, font=font, fill=fill)

    # === Draw text ===
    y_text = 130
    for i, line in enumerate(lines):
        if i == 0:
            draw_text_bold(draw, (150, y_text), line, title_font, font_color)
        else:
            draw_text_bold(draw, (200, y_text + 20), line, font, font_color)
        y_text += 130

    # === Footer ===
    date_str = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%d %b %Y, %H:%M IST")
    draw.text((150, height - 150), f"📅 Generated on {date_str}", font=font, fill=(100, 100, 100))

    # === Save to memory and send ===
    bio = io.BytesIO()
    img.save(bio, "PNG", optimize=True)
    bio.seek(0)

    await update.message.reply_photo(photo=bio, caption="📋 Your Escrow Stats Summary")

# === Top 20 Users (Text Output with 🥇🥈🥉 badges) ===
async def topuser(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update):
        return await update.message.reply_text("❌ Only admins can use this command!")

    users_data = {}
    for g in groups_col.find({}):
        for deal in g.get("deals", {}).values():
            if not deal:
                continue
            for user_key in ["buyer", "seller"]:
                user = str(deal.get(user_key, "")).strip()
                amount = float(deal.get("added_amount", 0))
                if user.startswith("@"):
                    users_data.setdefault(user, 0)
                    users_data[user] += amount

    if not users_data:
        return await update.message.reply_text("📊 No deals found.")

    # Sort users by total volume
    sorted_users = sorted(users_data.items(), key=lambda x: x[1], reverse=True)[:20]

    # Header
    msg = "🏆 <b>Top 20 Traders (by Volume)</b>\n"
    msg += "────────────────────────────\n"

    # Badge map for top 3
    badges = {1: "🥇", 2: "🥈", 3: "🥉"}

    # User list with badges
    for i, (user, volume) in enumerate(sorted_users, start=1):
        badge = badges.get(i, f"{i}.")
        msg += f"{badge} {user} — ₹{volume:.1f}\n"

    # Footer (IST)
    date_str = datetime.now().strftime("%d %b %Y, %I:%M %p") + " IST"
    msg += f"\n📅 Generated on {date_str}"

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
        return await update.message.reply_text("📊 There are currently no ongoing deals.")

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
        return await update.message.reply_text("🌱 No holding amounts right now!")

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
from telegram.ext import CallbackQueryHandler, CommandHandler

DEALS_PER_PAGE = 100  # number of completed deals per page
MAX_DEALS = 100      # show only latest 100 deals

async def mydeals(update, context, page=0):
    user = update.effective_user
    username = f"@{user.username}" if user.username else user.full_name

    # Collect user deals
    all_user_deals = []
    for g in groups_col.find({}):
        for deal in g.get("deals", {}).values():
            if deal.get("escrower") == username:
                all_user_deals.append(deal)

    if not all_user_deals:
        return await update.message.reply_text("🎉 You have no deals yet!")

    # Sort deals by trade_id (assuming trade_id increases over time)
    all_user_deals.sort(key=lambda x: x.get("trade_id"))

    # Keep only latest 100 deals
    latest_deals = all_user_deals[-MAX_DEALS:]

    # Separate pending & completed
    pending_deals = []
    completed_deals = []
    total_hold = 0
    completed_counter = 0  # for numbering 101, 102...

    for deal in latest_deals:
        trade_id = deal.get("trade_id", "Unknown")
        amount = float(deal.get("added_amount", 0))
        if deal.get("completed"):
            completed_counter += 1
            completed_deals.append(f"{completed_counter}. #{trade_id}")
        else:
            pending_deals.append(f"#{trade_id} → ₹{amount:.2f}")
            total_hold += amount

    # Build text
    text_lines = []

    # Active deals (only first page)
    if page == 0:
        if pending_deals:
            text_lines.append(f"🕒 Active Deals: ({len(pending_deals)})")
            text_lines.extend(pending_deals)
            text_lines.append(f"💼 Total Holding: ₹{total_hold:.2f}")
        else:
            text_lines.append("🕒 No active deals found.")
        text_lines.append("────────────────")

    # Completed deals pagination
    if completed_deals:
        total_pages = (len(completed_deals) + DEALS_PER_PAGE - 1) // DEALS_PER_PAGE
        start = page * DEALS_PER_PAGE
        end = start + DEALS_PER_PAGE
        chunk = completed_deals[start:end]

        if page == 0:
            text_lines.append(f"✅ Completed Deals ({len(completed_deals)}):")
        if chunk:
            text_lines.extend(chunk)
        else:
            text_lines.append("No more completed deals.")
    else:
        if page == 0:
            text_lines.append("✅ No completed deals yet.")

    text = "📜 <b>Your Deals Summary</b>\n────────────────\n" + "\n".join(text_lines)
    await update.message.reply_text(text, parse_mode="HTML")

from datetime import datetime, timedelta

# ==== Daily Summary ====
async def daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update):
        return await update.message.reply_text("❌ Only admins can use this command!")

    today = datetime.utcnow().date()
    start = datetime.combine(today, datetime.min.time())
    end = datetime.combine(today, datetime.max.time())

    total_deals = 0
    total_volume = 0.0
    total_fee = 0.0

    for g in groups_col.find({}):
        for deal in g.get("deals", {}).values():
            if not deal or not deal.get("completed"):
                continue

            dt = deal.get("completed_at")
            if not dt:
                continue

            # Convert to datetime if it's a string
            if isinstance(dt, str):
                try:
                    dt = datetime.fromisoformat(dt)
                except:
                    continue

            if start <= dt <= end:
                total_deals += 1
                total_volume += float(deal.get("added_amount", 0))  # ✅ fixed key
                total_fee += float(deal.get("fee", 0))

    if total_deals == 0:
        return await update.message.reply_text("📅 No deals completed today!")

    date_str = today.strftime("%d %b %Y")

    msg = (
        f"📅 <b>Today's Summary</b>\n"
        "────────────────\n"
        f"📊 Deals: {total_deals}\n"
        f"💰 Volume: ₹{total_volume}\n"
        f"💵 Total Fee: ₹{total_fee}\n"
        f"🗓 Date: {date_str}"
    )
    await update.message.reply_text(msg, parse_mode="HTML")


# ==== Weekly Summary ====
async def week(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update):
        return await update.message.reply_text("❌ Only admins can use this command!")

    today = datetime.utcnow().date()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    start = datetime.combine(start_of_week, datetime.min.time())
    end = datetime.combine(end_of_week, datetime.max.time())

    total_deals = 0
    total_volume = 0.0
    total_fee = 0.0

    for g in groups_col.find({}):
        for deal in g.get("deals", {}).values():
            if not deal or not deal.get("completed"):
                continue

            dt = deal.get("completed_at")
            if not dt:
                continue

            if isinstance(dt, str):
                try:
                    dt = datetime.fromisoformat(dt)
                except:
                    continue

            if start <= dt <= end:
                total_deals += 1
                total_volume += float(deal.get("added_amount", 0))  # ✅ fixed key
                total_fee += float(deal.get("fee", 0))

    if total_deals == 0:
        return await update.message.reply_text("📅 No deals completed this week!")

    msg = (
        f"🗓 <b>Weekly Summary</b>\n"
        "────────────────\n"
        f"📊 Deals: {total_deals}\n"
        f"💰 Volume: ₹{total_volume}\n"
        f"💵 Total Fee: ₹{total_fee}\n"
        f"📅 Week: {start_of_week.strftime('%d %b')} - {end_of_week.strftime('%d %b %Y')}"
    )
    await update.message.reply_text(msg, parse_mode="HTML")

import io, requests
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from telegram import Update
from telegram.ext import ContextTypes

# ==== TON Price Command ====
async def ton(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # === Fetch Toncoin Data from CoinGecko API ===
        r = requests.get("https://api.coingecko.com/api/v3/coins/toncoin")
        data = r.json()

        price = data["market_data"]["current_price"]["usd"]
        daily_change = data["market_data"]["price_change_percentage_24h"]
        weekly_change = data["market_data"]["price_change_percentage_7d"]

        # === Graph Data (last 7 days) ===
        chart_data = data["market_data"]["sparkline_7d"]["price"][-80:]  # 7-day small sparkline

        # === Create Image Canvas ===
        width, height = 1200, 600
        img = Image.new("RGB", (width, height), (0, 0, 0))
        draw = ImageDraw.Draw(img)

        # === Rounded Corners Background ===
        radius = 50
        mask = Image.new("L", (width, height), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.rounded_rectangle([(0, 0), (width, height)], radius, fill=255)
        bg = Image.new("RGB", (width, height), (10, 10, 10))
        bg.paste(img, mask=mask)

        # === Fonts ===
        try:
            font_big = ImageFont.truetype("DejaVuSans-Bold.ttf", 130)
            font_mid = ImageFont.truetype("DejaVuSans-Bold.ttf", 70)
            font_small = ImageFont.truetype("DejaVuSans.ttf", 45)
        except:
            font_big = font_mid = font_small = ImageFont.load_default()

        # === Price ===
        draw.text((70, 60), f"${price:.4f}", font=font_big, fill=(91, 173, 255))  # light blue

        # === Toncoin Label ===
        label_x = 950
        label_y = 80
        label_w, label_h = 200, 80
        draw.rounded_rectangle(
            [label_x, label_y, label_x + label_w, label_y + label_h],
            radius=30,
            fill=(230, 240, 255)
        )
        draw.text((label_x + 25, label_y + 15), "Toncoin", font=font_mid, fill=(0, 0, 0))

        # === Daily Change Box ===
        daily_color = (220, 0, 0) if daily_change < 0 else (0, 180, 0)
        daily_text = f"{daily_change:+.2f}%"
        draw.rounded_rectangle(
            [200, 250, 500, 350],
            radius=40,
            fill=(daily_color[0], daily_color[1], daily_color[2], 180)
        )
        draw.text((250, 275), daily_text, font=font_mid, fill=(255, 255, 255))
        draw.text((230, 380), "DAILY CHANGE", font=font_small, fill=(255, 255, 255))

        # === Weekly Change Box ===
        weekly_color = (0, 180, 0) if weekly_change > 0 else (220, 0, 0)
        weekly_text = f"{weekly_change:+.2f}%"
        draw.rounded_rectangle(
            [700, 250, 1000, 350],
            radius=40,
            fill=(weekly_color[0], weekly_color[1], weekly_color[2], 180)
        )
        draw.text((750, 275), weekly_text, font=font_mid, fill=(255, 255, 255))
        draw.text((720, 380), "WEEKLY CHANGE", font=font_small, fill=(255, 255, 255))

        # === Sparkline Graph ===
        graph_x, graph_y = 100, 470
        graph_w, graph_h = 1000, 100
        max_p, min_p = max(chart_data), min(chart_data)
        scale_y = graph_h / (max_p - min_p)

        for i in range(len(chart_data) - 1):
            x1 = graph_x + (i / len(chart_data)) * graph_w
            y1 = graph_y + graph_h - (chart_data[i] - min_p) * scale_y
            x2 = graph_x + ((i + 1) / len(chart_data)) * graph_w
            y2 = graph_y + graph_h - (chart_data[i + 1] - min_p) * scale_y
            draw.line((x1, y1, x2, y2), fill=(255, 0, 0), width=4)

        # === Dates ===
        today = datetime.utcnow()
        for i in range(7):
            day_label = (today - timedelta(days=6 - i)).strftime("%b %d")
            draw.text((graph_x + i * 150, graph_y + graph_h + 10), day_label, font=font_small, fill=(180, 180, 180))

        # === Save Image ===
        bio = io.BytesIO()
        img.save(bio, "PNG", optimize=True)
        bio.seek(0)

        # === Send to Telegram ===
        await update.message.reply_photo(photo=bio, caption="📈 Toncoin Price Tracker")

    except Exception as e:
        await update.message.reply_text(f"⚠️ Error fetching Toncoin data:\n`{e}`", parse_mode="Markdown")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_deal))
    app.add_handler(CommandHandler("complete", complete_deal))
    app.add_handler(CommandHandler("update", update_deal))
    app.add_handler(CommandHandler("status", deal_status))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("gstats", global_stats))
    app.add_handler(CommandHandler("topuser", topuser))
    app.add_handler(CommandHandler("ongoing", ongoing_deals))
    app.add_handler(CommandHandler("addadmin", add_admin))
    app.add_handler(CommandHandler("removeadmin", remove_admin))
    app.add_handler(CommandHandler("adminlist", admin_list))
    app.add_handler(CommandHandler("holding", holding))
    app.add_handler(CommandHandler("mydeals", mydeals))
    app.add_handler(CommandHandler("daily", daily))
    app.add_handler(CommandHandler("week", week))
    application.add_handler(CommandHandler("ton", ton))

    print("Bot started... ✅")
    app.run_polling()

if __name__ == "__main__":
    main()
