import logging
import asyncio
import time
import random
import string
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from config import BOT_TOKEN, OWNER_ID
from engine import SyncEngine
from bot_ui import BotUI

# Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Engine
engine = SyncEngine()
ui = BotUI()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start Command"""
    await update.message.reply_text(
        "👋 **Namaste! Sync Server v12 Online.**\n\n"
        "Usage:\n`/asc video_link audio_link`\n\n"
        "⚡ *Powered by Direct FFmpeg Streaming*"
    )

async def asc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main Sync Command"""
    user = update.effective_user
    
    # Security Check
    if user.id != OWNER_ID:
        await update.message.reply_text("🔒 Access Denied. Yeh private bot hai.")
        return

    if len(context.args) < 2:
        await update.message.reply_text("❌ Usage: `/asc video_link audio_link`")
        return

    # Generate Random Task ID
    task_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    
    # Initial Message
    msg = await update.message.reply_text(
        ui.status_message(task_id, "Connecting...", "Initializing Engine")
    )

    try:
        start_time = time.time()
        
        ref_link = context.args[0]
        new_link = context.args[1]

        # Step 1: Metadata (Progress 10%)
        await msg.edit_text(ui.status_message(task_id, ui.progress_bar(10), "Fetching Metadata..."))
        
        ref_meta = engine.get_metadata(ref_link)
        if not ref_meta:
            await msg.edit_text("❌ **Error:** Video Link Access Nahi Hua.")
            return

        duration = ref_meta['duration']
        
        # Paths define karo
        r_start = engine.temp_dir / f"r_s_{task_id}.wav"
        n_start = engine.temp_dir / f"n_s_{task_id}.wav"
        r_end = engine.temp_dir / f"r_e_{task_id}.wav"
        n_end = engine.temp_dir / f"n_e_{task_id}.wav"

        # Step 2: Extract Start (Progress 30%)
        await msg.edit_text(ui.status_message(task_id, ui.progress_bar(30), "Streaming Start (0s)..."))
        
        # Parallel extraction using asyncio
        loop = asyncio.get_event_loop()
        
        # Start Extraction
        t1 = loop.run_in_executor(None, engine.extract_sample, ref_link, 0, r_start)
        t2 = loop.run_in_executor(None, engine.extract_sample, new_link, 0, n_start)
        await asyncio.gather(t1, t2)

        # Step 3: Extract End (Progress 60%)
        end_seek = duration - 30 # End se 30 sec pehle
        await msg.edit_text(ui.status_message(task_id, ui.progress_bar(60), f"Streaming End ({int(end_seek)}s)..."))
        
        t3 = loop.run_in_executor(None, engine.extract_sample, ref_link, end_seek, r_end)
        t4 = loop.run_in_executor(None, engine.extract_sample, new_link, end_seek, n_end)
        await asyncio.gather(t3, t4)

        # Step 4: Calculation (Progress 90%)
        await msg.edit_text(ui.status_message(task_id, ui.progress_bar(90), "Calculating Delays..."))
        
        start_delay = engine.calculate_offset(r_start, n_start)
        end_delay = engine.calculate_offset(r_end, n_end)

        # Final Report
        total_time = time.time() - start_time
        report = ui.final_report(ref_meta, start_delay, end_delay, total_time)
        
        await msg.edit_text(report, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Critical Error: {e}")
        await msg.edit_text(f"❌ **Critical Error:** {str(e)}")
    
    finally:
        # Cleanup
        engine.cleanup()

def main():
    """Bot Start Function"""
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("asc", asc))
    
    print("✅ Bot v12 Started...")
    app.run_polling()

if __name__ == "__main__":
    main()
