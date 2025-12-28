import logging
import asyncio
import time
import random
import string
import re
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from config import BOT_TOKEN, OWNER_ID, INDEX_WORKER
from engine import SurgeonEngine
from ui_builder import UIBuilder

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

engine = SurgeonEngine()
ui = UIBuilder()

def parse_link(arg):
    """
    Splits Link and Track ID.
    Input: "link:2" -> ("link", 2)
    Input: "link" -> ("link", 0)
    """
    track = 0
    link = arg
    # Check for track syntax
    if re.search(r':\d+$', arg):
        parts = arg.rsplit(':', 1)
        link = parts[0]
        track = int(parts[1])
    
    # GDrive Conversion
    if "drive.google.com" in link:
        # Extract ID
        match = re.search(r"(?:/d/|id=|file/d/)([a-zA-Z0-9_-]+)", link)
        if match:
            link = f"{INDEX_WORKER}/direct.aspx?id={match.group(1)}"
            
    return link, track

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "**🩺 Audio Sync Surgeon v13**\n\n"
        "**Usage:**\n"
        "`/asc video_link audio_link`\n"
        "`/asc video_link:1 audio_link:0` (With Track IDs)\n\n"
        "⚡ **Features:**\n"
        "• Internal Delay Detection\n"
        "• 3-Point Drift Check\n"
        "• Auto GDrive Conversion"
    )

async def asc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != OWNER_ID: return

    if len(context.args) < 2:
        await update.message.reply_text("❌ Usage: `/asc video audio`")
        return

    # Random Task ID
    task_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    
    msg = await update.message.reply_text(
        f"⏳ **Task Processing** | {task_id}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🚀 **Status:** Analyzing Links...\n"
        f"▱▱▱▱▱▱▱▱▱▱ 0%"
    )
    
    start_time = time.time()

    try:
        # 1. Parse Inputs
        ref_link, ref_track = parse_link(context.args[0])
        new_link, new_track = parse_link(context.args[1])

        # 2. Metadata (v6.1 Logic)
        await msg.edit_text(ui.progress_bar(15, "Reading Metadata (Internal Delay)..."))
        
        ref_meta = engine.get_metadata(ref_link, f"0:v:0") # Video info
        if not ref_meta:
            # Fallback to audio stream if video stream missing info
            ref_meta = engine.get_metadata(ref_link, f"0:a:{ref_track}")
            
        new_meta = engine.get_metadata(new_link, f"0:a:{new_track}")

        if not ref_meta or not new_meta:
            await msg.edit_text("❌ Metadata Failed. Links check karein.")
            return

        # 3. Extraction (Start & End)
        duration = min(ref_meta['duration'], new_meta['duration'])
        
        # Paths
        r_start = engine.work_dir / f"r_s_{task_id}.wav"
        n_start = engine.work_dir / f"n_s_{task_id}.wav"
        r_end = engine.work_dir / f"r_e_{task_id}.wav"
        n_end = engine.work_dir / f"n_e_{task_id}.wav"

        await msg.edit_text(ui.progress_bar(40, "Streaming Samples..."))
        
        loop = asyncio.get_event_loop()
        tasks = []
        
        # Start Sample (0s)
        tasks.append(loop.run_in_executor(None, engine.extract_sample, ref_link, 0, r_start, ref_track))
        tasks.append(loop.run_in_executor(None, engine.extract_sample, new_link, 0, n_start, new_track))
        
        # End Sample (Last 30s) if file long enough
        check_drift = False
        if duration > 120:
            check_drift = True
            end_seek = duration - 30
            tasks.append(loop.run_in_executor(None, engine.extract_sample, ref_link, end_seek, r_end, ref_track))
            tasks.append(loop.run_in_executor(None, engine.extract_sample, new_link, end_seek, n_end, new_track))
        
        await asyncio.gather(*tasks)

        # 4. Calculation
        await msg.edit_text(ui.progress_bar(80, "Running Cross-Correlation..."))
        
        d_start = engine.calculate_offset(r_start, n_start)
        d_end = 0.0
        
        if check_drift:
            res_end = engine.calculate_offset(r_end, n_end)
            d_end = res_end if res_end is not None else d_start
        else:
            d_end = d_start

        if d_start is None:
            await msg.edit_text("❌ Correlation Failed (Silence/No Audio).")
            return

        # 5. Report
        analysis = {
            'start': d_start,
            'end': d_end
        }
        
        report = ui.generate_report(ref_meta, new_meta, analysis, user.first_name, time.time() - start_time)
        await msg.edit_text(report, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Error: {e}")
        await msg.edit_text(f"❌ Critical Error: {e}")
    
    finally:
        engine.cleanup()

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("asc", asc))
    print("✅ Surgeon v13 Started...")
    app.run_polling()

if __name__ == "__main__":
    main()
