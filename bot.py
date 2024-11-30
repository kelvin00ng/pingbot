import json
import logging
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from ping3 import ping
import nest_asyncio
import datetime

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

VPS_FILE = "vps_data.json"
vps_data = {}

def load_vps_data():
    global vps_data
    try:
        with open(VPS_FILE, 'r') as f:
            vps_data = json.load(f)
            logger.info("VPS data loaded successfully.")
    except (FileNotFoundError, json.JSONDecodeError):
        vps_data = {}
        logger.warning("No valid VPS data found. Initialized with empty data.")
def save_vps_data():
    try:
        with open(VPS_FILE, 'w') as f:
            json.dump(vps_data, f, indent=4)
            logger.info("VPS data saved successfully.")
    except IOError as e:
        logger.error(f"Failed to save VPS data: {e}")

def ping_server(server):
    try:
        response_time = ping(server)  
        if response_time is not None and response_time < 1:
            return True, response_time  
        else:
            return False, response_time  
    except Exception as e:
        logger.error(f"Error pinging server {server}: {e}")
        return False, None  

async def auto_ping(context: ContextTypes.DEFAULT_TYPE):
    global vps_data
    chat_id = context.job.data
    message_parts = []
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    custom_message = "This is your VPS status update:" 
    message_parts.append(f"{custom_message}\nDate and Time: {current_time}\n")
    for server, data in vps_data.items():
        is_online, response_time = ping_server(server)  
        note = data.get("note", "No note available")
        if is_online:
            message_parts.append(f"✅ VPS {server} is online (Response Time: {response_time:.2f} seconds). Note: {note}")
            data["up_times"] += 1
        else:
            if response_time is not None:
                message_parts.append(f"❌ VPS {server} is offline (Last Response Time: {response_time:.2f} seconds). Note: {note}")
            else:
                message_parts.append(f"❌ VPS {server} is offline (Error while pinging). Note: {note}")
            data["down_times"] += 1
    if message_parts:
        full_message = "\n".join(message_parts)
        await context.bot.send_message(chat_id=chat_id, text=full_message)
    save_vps_data()

commands = [
    ("start", "Welcome message"),
    ("ping", "Check the status of all VPS servers"),
    ("list", "List all VPS servers"),
    ("add", "Add a new VPS server"),
    ("remove", "Remove an existing VPS server"),
    #("stats", "Show uptime statistics for all VPS servers"),
    ("start_auto_ping", "Start automatic pinging of VPS servers"),
    ("stop_auto_ping", "Stop automatic pinging of VPS servers")
]

async def set_bot_commands(bot):
    await bot.set_my_commands(commands)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Fuck Yo Mother la knnbpcb ur lanjiao smelly')

async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    results = {
        server: {
            "status": "Online" if (is_online := ping_server(server)[0]) else "Offline",
            "response_time": ping_server(server)[1],
            "note": data["note"]
        }
        for server, data in vps_data.items()
    }
    response = "\n".join([
        f"{server}: {status['status']}" +
        (f" (Response Time: {status['response_time']:.2f} seconds)" if status['response_time'] is not None else " (Response Time: Unavailable)") +
        f" (Note: {status['note']})"
        for server, status in results.items()
    ])
    await update.message.reply_text(response)

async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not vps_data:
        await update.message.reply_text("No VPS servers found.")
    else:
        #(Uptime: {calculate_uptime(server):.2f}%)
        response = "\n".join([f"{server}: {data['note']}" for server, data in vps_data.items()])
        await update.message.reply_text(response)

async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /add <ip> <note>")
        return
    ip, note = context.args[0], " ".join(context.args[1:])
    vps_data[ip] = {"note": note, "up_times": 0, "down_times": 0}
    save_vps_data()
    await update.message.reply_text(f"VPS {ip} added with note: {note}")

async def remove_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) < 1:
        await update.message.reply_text("Usage: /remove <ip>")
        return
    ip = context.args[0]
    if ip in vps_data:
        del vps_data[ip]
        save_vps_data()
        await update.message.reply_text(f"VPS {ip} has been removed.")
    else:
        await update.message.reply_text(f"VPS {ip} not found.")

# def calculate_uptime(server):
#     up_times, down_times = vps_data[server]["up_times"], vps_data[server]["down_times"]
#     if total_checks := up_times + down_times == 0:
#         return 100
#     return (up_times / total_checks) * 100

# async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
#     if not vps_data:
#         await update.message.reply_text("No VPS servers found.")
#     else:
#         response = "\n".join([f"{server}: Uptime: {calculate_uptime(server):.2f}%" for server in vps_data])
#         await update.message.reply_text(response)

chat_ids = []  
async def start_auto_ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat.id
    if chat_id not in chat_ids:
        chat_ids.append(chat_id)  
    context.job_queue.run_repeating(auto_ping, interval=60, first=60, data=chat_id)  # Use 'data' instead of 'context'
    await update.message.reply_text("Auto pinging has been started.")

async def stop_auto_ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat.id
    if chat_id in chat_ids:
        chat_ids.remove(chat_id)
        job_removed = context.job_queue.get_jobs_by_name(chat_id)
        for job in job_removed:
            job.schedule_removal()
        await update.message.reply_text("Auto pinging has been stopped.")
    else:
        await update.message.reply_text("Auto pinging was not running in this chat.")

async def main():
    load_vps_data()
    application = ApplicationBuilder().token("7656068459:AAFt8fL8nV25vrwBjHLz-USiDJpRWZYr4f0").build()
    handlers = [
        CommandHandler("start", start),
        CommandHandler("ping", ping_command),
        CommandHandler("list", list_command),
        CommandHandler("add", add_command),
        CommandHandler("remove", remove_command),
        #CommandHandler("stats", stats_command),
        CommandHandler("start_auto_ping", start_auto_ping),
        CommandHandler("stop_auto_ping", stop_auto_ping)]
    application.add_handlers(handlers)
    await set_bot_commands(application.bot)
    try:
        await application.run_polling()
    except Exception as e:
        logger.error(f"An error occurred while running bot polling: {e}")
    finally:
        await application.shutdown() 

import traceback
if __name__ == '__main__':
    try:
        nest_asyncio.apply()
        asyncio.run(main())
    except Exception as e:
        logger.error(f"An error occurred while starting the bot: {e}")
        logger.error(traceback.format_exc())
