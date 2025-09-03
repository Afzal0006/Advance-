import re
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from pymongo import MongoClient

# ==== CONFIG ====
BOT_TOKEN = "7095431388:AAFcFJwTVT5r5f0K1NQempMh_zEfU8ICquA"
MONGO_URI = "mongodb+srv://afzal99550:afzal99550@cluster0.aqmbh9q.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
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

# ==== START WITH MENU ====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Step 1: Send Photo + hello caption
    photo_url = "https://i.ibb.co/cKR3sXfT/x.jpg"
    await update.message.reply_photo(
        photo=photo_url,
        caption="Hello! I'm Manual Escrower Bot. How can I assist you with your escrow needs today?"
    )

    # Step 2: Show main menu buttons
    keyboard = [
        [InlineKeyboardButton("🤖 Bot command", callback_data="bot_commands")],
        [InlineKeyboardButton("📞 Contact", callback_data="contact")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Choose an option below 👇", reply_markup=reply_markup)

# ==== BUTTON HANDLER ====
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "bot_commands":
        # Full command list
        text = (
            "✨ Welcome to Escrower Bot! ✨\n\n"
            "• /add amount – Add a new deal\n"
            "• /complete amount – Complete a deal\n"
            "• /status trade_id – Check deal status by Trade ID\n"
            "• /stats – Group stats\n"
            "• /gstats – Global stats (Admin only)\n"
            "• /mystats – Your buyer/seller stats (Global)\n"
            "• /allstats – All users stats (Admin only)\n"
            "• /addadmin user_id – Owner only\n"
            "• /removeadmin user_id – Owner only\n"
            "• /adminlist – Show all admins"
        )
        keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data="main_menu")]]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "contact":
        keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data="main_menu")]]
        await query.edit_message_text("📞 Contact: @golgibody", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "main_menu":
        keyboard = [
            [InlineKeyboardButton("🤖 Bot command", callback_data="bot_commands")],
            [InlineKeyboardButton("📞 Contact", callback_data="contact")]
        ]
        await query.edit_message_text("Choose an option below 👇", reply_markup=InlineKeyboardMarkup(keyboard))

# ==== BAQI SARE COMMANDS ====
# add_deal, complete_deal, deal_status, group_stats, global_stats,
# my_stats, all_stats, add_admin, remove_admin, admin_list
# Ye sab aapke original file ke commands rahenge, unhe touch nahi kiya gaya.

# ==== MAIN ====
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(CommandHandler("add", add_deal))
    app.add_handler(CommandHandler("complete", complete_deal))
    app.add_handler(CommandHandler("status", deal_status))
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
