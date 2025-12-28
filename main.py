
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
    Smart Link Parser:
    1. Tracks ID (link:2)
    2. GDrive Conversion (auto-detect)
    """
    track = 0
    link = arg
    
    # 1. Track ID Extraction
    if re.search(r':\d+$', arg):
        parts = arg.rsplit(':', 1)
        link = parts[0]
        track = int(parts[1])
    
    # 2. GDrive Converter
    # Agar link GDrive ka hai (view, open, id, etc)
    gdrive_pattern = r"(?:/d/|id=|file/d/)([a-zA-Z0-9_-]+)"
    match = re.search(gdrive_pattern, link)
    
    if match and "drive.google.com" in link:
        # Convert to Index Worker
        link = f"{INDEX_WORKER}/direct.aspx?id={match.group(1)}"
        
    return link, track

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "**🩺 Audio Sync Surgeon v13**\n\n"
        "**Usage:**\n"
        "`/asc video_link audio_link`\n"
        "`/asc video_link:1 audio_link:0` (With Track IDs)\n\n"
        "⚡ **Features:**\n"
        "• Internal Delay (v6.1)\n"
        "• 3-Point Check (Start/Mid/End)\n"
        "• Auto GDrive Conversion"
    )

async def asc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != OWNER_ID: 
        await update.message.reply_text("🔒 Access Denied.")
        return

    if len(context.args) < 2:
        await update.message.reply_text("❌ Usage: `/asc video audio`")
        return

    task_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    
    msg = await update.message.reply_text(
        f"⏳ **Task Processing** | {task_id}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🚀 **Status:** Analyzing Links...\n"
        f"▱▱▱▱▱▱▱▱▱▱ 0%"
    )
    
    start_time = time.time()

    try:
        # 1. Parse Links & Tracks
        ref_link, ref_track = parse_link(context.args[0])
        new_link, new_track = parse_link(context.args[1])

        # 2. Metadata (Internal Delay & FPS)
        await msg.edit_text(ui.progress_bar(15, "Reading Metadata..."))
        
        # Video stream info try karo pehle
        ref_meta = engine.get_metadata(ref_link, f"0:v:0") 
        if not ref_meta:
            # Fallback to audio stream if no video
            ref_meta = engine.get_metadata(ref_link, f"0:a:{ref_track}")
            
        new_meta = engine.get_metadata(new_link, f"0:a:{new_track}")

        if not ref_meta or not new_meta:
            await msg.edit_text(f"❌ Metadata Failed.\n\nChecked Link: `{ref_link}`")
            return

        # 3. Extraction (Start, Mid, End)
        duration = min(ref_meta['duration'], new_meta['duration'])
        
        # Points define karo
        points = {
            "start": 0,
            "mid": duration / 2,
            "end": duration - 30
        }
        
        files = {}
        tasks = []
        loop = asyncio.get_event_loop()

        await msg.edit_text(ui.progress_bar(40, "Streaming Samples (Start/Mid/End)..."))
        
        for key, seek in points.items():
            # Skip Mid/End if file is short (< 2 min)
            if duration < 120 and key != "start": continue

            r_f = engine.work_dir / f"r_{key}_{task_id}.wav"
            n_f = engine.work_dir / f"n_{key}_{task_id}.wav"
            files[key] = (r_f, n_f)
            
            # Extract Async
            tasks.append(loop.run_in_executor(None, engine.extract_sample, ref_link, seek, r_f, ref_track))
            tasks.append(loop.run_in_executor(None, engine.extract_sample, new_link, seek, n_f, new_track))
        
        await asyncio.gather(*tasks)

        # 4. Calculation
        await msg.edit_text(ui.progress_bar(80, "Running Cross-Correlation..."))
        
        delays = {}
        for key, (r_f, n_f) in files.items():
            delay = engine.calculate_offset(r_f, n_f)
            delays[key] = delay if delay is not None else 0.0

        # 5. Smart Logic (Cut vs Drift)
        d_start = delays.get('start', 0.0)
        d_mid = delays.get('mid', d_start)
        d_end = delays.get('end', d_start)
        
        drift_total = d_end - d_start
        cut_detected = False
        
        # Cut Logic: Agar Drift linear nahi hai
        if abs(drift_total) > 100:
            expected_mid = d_start + (drift_total / 2)
            # Tolerance 200ms
            if abs(d_mid - expected_mid) > 200:
                cut_detected = True

        # 6. Report Generation
        analysis = {
            'start': d_start,
            'mid': d_mid,
            'end': d_end,
            'cut_detected': cut_detected
        }
        
        report = ui.generate_report(ref_meta, new_meta, analysis, user.first_name, time.time() - start_time)
        await msg.edit_text(report, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Error: {e}")
        await msg.edit_text(f"❌ Error: {e}")
    
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
