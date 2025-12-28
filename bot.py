#!/usr/bin/env python3
"""
MWS - Audio Sync Bot
Professional audio-video synchronization with link support
@MuxingWorkStation
"""

import sys
import os
import asyncio
import subprocess
import shutil
import logging
import re
from pathlib import Path
from typing import Optional, Dict, Tuple
from datetime import datetime
import time

try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import (
        Application, CommandHandler, MessageHandler, 
        filters, ContextTypes, CallbackQueryHandler
    )
    from pymediainfo import MediaInfo
    import numpy as np
    from scipy.io import wavfile
    from scipy import signal
except ImportError:
    print("❌ Missing dependencies!")
    print("Run: pip install python-telegram-bot pymediainfo numpy scipy")
    sys.exit(1)

# ============================================================================
# CONFIGURATION
# ============================================================================
BOT_TOKEN = "7212124385:AAGWRwcGVahPwMK7qEfcfviNIGXJ5JepLzc"
ALLOWED_USERS = [6514133475]
OWNER_ID = 6514133475
CHANNEL_LINK = "https://t.me/MuxingWorkStation"
CHANNEL_USERNAME = "@MuxingWorkStation"

WORK_DIR = Path("./workspace")
TEMP_DIR = Path("./temp")
WORK_DIR.mkdir(exist_ok=True)
TEMP_DIR.mkdir(exist_ok=True)

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# DOWNLOAD MANAGER (Multi-protocol support)
# ============================================================================

class DownloadManager:
    """Smart downloader supporting multiple protocols"""
    
    def __init__(self):
        self.downloaders = self._check_available_downloaders()
    
    def _check_available_downloaders(self) -> Dict[str, bool]:
        """Check which downloaders are available"""
        return {
            'aria2c': shutil.which('aria2c') is not None,
            'yt-dlp': shutil.which('yt-dlp') is not None,
            'gdown': shutil.which('gdown') is not None,
            'wget': shutil.which('wget') is not None,
            'curl': shutil.which('curl') is not None
        }
    
    def _extract_gdrive_id(self, url: str) -> Optional[str]:
        """Extract Google Drive file ID"""
        patterns = [
            r'/file/d/([a-zA-Z0-9_-]+)',
            r'[?&]id=([a-zA-Z0-9_-]+)',
            r'/d/([a-zA-Z0-9_-]+)'
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    async def download(self, url: str, output_path: Path, 
                      progress_callback=None) -> bool:
        """
        Smart download with automatic method selection
        Supports: Direct links, Google Drive, YouTube, etc.
        """
        try:
            # Google Drive detection
            gdrive_id = self._extract_gdrive_id(url)
            if gdrive_id:
                if self.downloaders['gdown']:
                    return await self._download_gdown(gdrive_id, output_path, progress_callback)
                else:
                    url = f"https://drive.google.com/uc?export=download&id={gdrive_id}"
            
            # YouTube/streaming platforms
            if 'youtube.com' in url or 'youtu.be' in url:
                if self.downloaders['yt-dlp']:
                    return await self._download_ytdlp(url, output_path, progress_callback)
            
            # Direct download (try in order of preference)
            if self.downloaders['aria2c']:
                return await self._download_aria2c(url, output_path, progress_callback)
            elif self.downloaders['wget']:
                return await self._download_wget(url, output_path, progress_callback)
            elif self.downloaders['curl']:
                return await self._download_curl(url, output_path, progress_callback)
            else:
                logger.error("No downloader available!")
                return False
        
        except Exception as e:
            logger.error(f"Download error: {e}")
            return False
    
    async def _download_aria2c(self, url: str, output: Path, callback) -> bool:
        """Download using aria2c (fast, resumable)"""
        cmd = [
            'aria2c',
            '--console-log-level=error',
            '--summary-interval=1',
            '-x', '16',
            '-s', '16',
            '-k', '1M',
            '-d', str(output.parent),
            '-o', output.name,
            url
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        
        if callback:
            asyncio.create_task(self._monitor_download(output, callback))
        
        await process.wait()
        return output.exists() and output.stat().st_size > 0
    
    async def _download_wget(self, url: str, output: Path, callback) -> bool:
        """Download using wget"""
        cmd = ['wget', '-q', '--show-progress', '-O', str(output), url]
        process = await asyncio.create_subprocess_exec(*cmd)
        await process.wait()
        return output.exists() and output.stat().st_size > 0
    
    async def _download_curl(self, url: str, output: Path, callback) -> bool:
        """Download using curl"""
        cmd = ['curl', '-L', '-o', str(output), url]
        process = await asyncio.create_subprocess_exec(*cmd)
        await process.wait()
        return output.exists() and output.stat().st_size > 0
    
    async def _download_gdown(self, file_id: str, output: Path, callback) -> bool:
        """Download from Google Drive using gdown"""
        cmd = ['gdown', '--id', file_id, '-O', str(output)]
        process = await asyncio.create_subprocess_exec(*cmd)
        await process.wait()
        return output.exists() and output.stat().st_size > 0
    
    async def _download_ytdlp(self, url: str, output: Path, callback) -> bool:
        """Download using yt-dlp"""
        cmd = [
            'yt-dlp',
            '-f', 'bestvideo+bestaudio',
            '-o', str(output),
            url
        ]
        process = await asyncio.create_subprocess_exec(*cmd)
        await process.wait()
        return output.exists() and output.stat().st_size > 0
    
    async def _monitor_download(self, file_path: Path, callback):
        """Monitor download progress"""
        prev_size = 0
        while True:
            await asyncio.sleep(2)
            if file_path.exists():
                size = file_path.stat().st_size
                if size > prev_size:
                    await callback(f"Downloading... {size / (1024**2):.1f} MB", 0)
                    prev_size = size
                else:
                    break
            else:
                break

# ============================================================================
# SYNC ENGINE (Your proven algorithm)
# ============================================================================

class SyncEngine:
    """Battle-tested sync detection"""
    
    def __init__(self):
        self.temp = TEMP_DIR
    
    def get_media_info(self, file_path: Path) -> Dict:
        """Extract comprehensive media info"""
        try:
            mi = MediaInfo.parse(str(file_path))
            
            info = {
                'filename': file_path.name,
                'size_gb': file_path.stat().st_size / (1024**3),
                'duration': 0,
                'fps': 'N/A',
                'codec': 'Unknown',
                'internal_delay': 0
            }
            
            if mi.general_tracks:
                gen = mi.general_tracks[0]
                if gen.duration:
                    info['duration'] = float(gen.duration) / 1000
            
            if mi.video_tracks:
                vid = mi.video_tracks[0]
                info['fps'] = vid.frame_rate or 'N/A'
                info['codec'] = vid.format or 'Unknown'
            
            if mi.audio_tracks:
                aud = mi.audio_tracks[0]
                if not info['duration'] and aud.duration:
                    info['duration'] = float(aud.duration) / 1000
                info['fps'] = aud.sampling_rate or info['fps']
                info['codec'] = aud.format or info['codec']
                
                # Internal delay
                if aud.delay_relative_to_video is not None:
                    info['internal_delay'] = int(aud.delay_relative_to_video)
                elif aud.delay is not None:
                    delay_str = str(aud.delay).replace('ms', '').strip()
                    info['internal_delay'] = int(float(delay_str))
            
            return info
        
        except Exception as e:
            logger.error(f"MediaInfo error: {e}")
            return {
                'filename': file_path.name,
                'size_gb': 0,
                'duration': 0,
                'fps': 'N/A',
                'codec': 'Unknown',
                'internal_delay': 0
            }
    
    def extract_sample(self, file: Path, start: float, duration: float, 
                      output: Path, stream: str = "0:a:0") -> bool:
        """Extract audio sample"""
        cmd = [
            'ffmpeg', '-y', '-hide_banner', '-loglevel', 'error',
            '-ss', str(start), '-i', str(file),
            '-map', stream, '-t', str(duration),
            '-vn', '-acodec', 'pcm_s16le', '-ar', '48000', '-ac', '2',
            str(output)
        ]
        
        result = subprocess.run(cmd, capture_output=True)
        return output.exists() and output.stat().st_size > 1000
    
    def correlate(self, ref_wav: Path, new_wav: Path) -> Optional[float]:
        """Calculate delay via cross-correlation"""
        try:
            ref_rate, ref_data = wavfile.read(ref_wav)
            new_rate, new_data = wavfile.read(new_wav)
            
            if ref_rate != new_rate:
                return None
            
            # Mono conversion
            if ref_data.ndim > 1:
                ref_data = ref_data[:, 0]
            if new_data.ndim > 1:
                new_data = new_data[:, 0]
            
            # Normalize
            ref_data = ref_data.astype(float) - np.mean(ref_data)
            new_data = new_data.astype(float) - np.mean(new_data)
            
            # Correlate
            corr = signal.correlate(new_data, ref_data, mode='full')
            lag = corr.argmax() - (len(ref_data) - 1)
            
            return (lag / ref_rate) * 1000
        
        except Exception as e:
            logger.error(f"Correlation error: {e}")
            return None
    
    def analyze(self, ref_file: Path, new_file: Path, 
               ref_stream: str = "0:a:0", 
               new_stream: str = "0:a:0") -> Dict:
        """Complete analysis"""
        start_time = time.time()
        
        try:
            # Get info
            ref_info = self.get_media_info(ref_file)
            new_info = self.get_media_info(new_file)
            
            # Sample duration
            min_duration = min(ref_info['duration'], new_info['duration'])
            sample_dur = 270 if min_duration > 600 else max(30, int(min_duration / 3))
            
            # Extract start samples
            logger.info("Extracting start samples...")
            ref_start = self.temp / "ref_start.wav"
            new_start = self.temp / "new_start.wav"
            
            if not self.extract_sample(ref_file, 0, sample_dur, ref_start, ref_stream):
                raise ValueError("Failed to extract reference sample")
            
            if not self.extract_sample(new_file, 0, sample_dur, new_start, new_stream):
                raise ValueError("Failed to extract audio sample")
            
            # Calculate start delay
            delay_start = self.correlate(ref_start, new_start)
            if delay_start is None:
                raise ValueError("Correlation failed")
            
            # Extract end samples
            delay_end = delay_start
            if min_duration > sample_dur * 2 + 10:
                logger.info("Extracting end samples...")
                end_pos = min_duration - sample_dur - 5
                
                ref_end = self.temp / "ref_end.wav"
                new_end = self.temp / "new_end.wav"
                
                if (self.extract_sample(ref_file, end_pos, sample_dur, ref_end, ref_stream) and
                    self.extract_sample(new_file, end_pos, sample_dur, new_end, new_stream)):
                    
                    delay_end_calc = self.correlate(ref_end, new_end)
                    if delay_end_calc is not None:
                        delay_end = delay_end_calc
            
            # Calculate drift
            drift = delay_end - delay_start
            
            # Atempo calculation
            atempo = None
            if abs(drift) > 100:
                duration_calc = min_duration if delay_end != delay_start else sample_dur
                atempo = duration_calc / (duration_calc - (drift / 1000.0))
                atempo = round(atempo, 6)
            
            # Final delay
            base_delay = int(round(-delay_start))
            final_delay = ref_info['internal_delay'] + base_delay
            
            # Cleanup
            for f in self.temp.glob('*.wav'):
                try:
                    f.unlink()
                except:
                    pass
            
            return {
                'success': True,
                'ref_info': ref_info,
                'new_info': new_info,
                'delay_start': delay_start,
                'delay_end': delay_end,
                'drift': drift,
                'atempo': atempo,
                'final_delay': final_delay,
                'processing_time': time.time() - start_time
            }
        
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            return {'success': False, 'error': str(e)}

# ============================================================================
# BOT CLASS
# ============================================================================

def check_access(func):
    """Access control"""
    async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id not in ALLOWED_USERS:
            keyboard = [[InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK)]]
            await update.message.reply_text(
                "🔒 **Access Denied**\n\n"
                f"Join {CHANNEL_USERNAME} for updates!",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
        return await func(self, update, context)
    return wrapper


class MWSAudioSyncBot:
    """MWS - Audio Sync Bot"""
    
    def __init__(self, token: str):
        self.token = token
        self.downloader = DownloadManager()
        self.engine = SyncEngine()
        self.user_data = {}
    
    def format_duration(self, seconds: float) -> str:
        """Format duration"""
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        return f"[{h:02d}:{m:02d}:{s:02d}]"
    
    def generate_report(self, result: Dict) -> str:
        """Beautiful report"""
        ref = result['ref_info']
        new = result['new_info']
        
        report = [
            "**MEDIA SYNC REPORT**",
            "━━━━━━━━━━━━━━━━━━━━━━━━",
            f"🎬 {ref['filename'][:50]}{'...' if len(ref['filename']) > 50 else ''} ({ref['size_gb']:.2f} GB)",
            f"   └─ Stream : {ref['fps']}  {self.format_duration(ref['duration'])}",
            "",
            f"🎧 {new['filename'][:50]}{'...' if len(new['filename']) > 50 else ''} ({new['size_gb']:.2f} GB)",
            f"   └─ Stream : {new['fps']}  {self.format_duration(new['duration'])}",
            "━━━━━━━━━━━━━━━━━━━━━━━━",
            "**RAW DATA CHECK**",
            f"{'Stream':<14}  {'FPS':<8}  {'Duration'}",
            "─" * 14 + "  " + "─" * 8 + "  " + "─" * 14,
            f"{'Video':<14}: {str(ref['fps']):<8}  {self.format_duration(ref['duration'])}",
            f"{'Audio (Raw)':<14}: {str(new['fps']):<8}  {self.format_duration(new['duration'])}",
            f"{'Raw Diff':<14}:           {self.format_duration(abs(ref['duration'] - new['duration']))}",
            "- - - - - - - - - - - - - - - - - -",
            "",
            "**WAVEFORM ANALYSIS**",
            f"Delay (Start)  : {result['delay_start']:+.1f} ms",
            f"Delay (End)    : {result['delay_end']:+.1f} ms",
        ]
        
        if abs(result['drift']) > 100:
            report.append(f"🚨 **Drift**    : {result['drift']:+.1f} ms")
        else:
            report.append(f"✅ **Stable**   : {result['drift']:+.1f} ms variation")
        
        report.extend([
            "- - - - - - - - - - - - - - - - - -",
            "",
            "**PROJECTED SYNC**",
            f"{'Stream':<14}  {'FPS':<8}  {'Duration'}",
            "─" * 14 + "  " + "─" * 8 + "  " + "─" * 14,
            f"{'Video Data':<14}: {str(ref['fps']):<8}  {self.format_duration(ref['duration'])}",
            f"{'Audio Data':<14}: {str(ref['fps']):<8}  {self.format_duration(new['duration'])}",
            f"{'Difference':<14}:           {self.format_duration(abs(ref['duration'] - new['duration']))}",
            "",
        ])
        
        if result['atempo']:
            report.extend([
                "**DRIFT FIX REQUIRED**",
                f"1️⃣ Fix Drift     : atempo={result['atempo']}",
                f"2️⃣ Add Delay     : {result['final_delay']} ms",
                "3️⃣ Mux Output",
            ])
        else:
            report.extend([
                "**PERFECT MATCH**",
                f"1️⃣ Add Delay     : {result['final_delay']} ms",
                "2️⃣ Mux Directly",
            ])
        
        report.extend([
            "━━━━━━━━━━━━━━━━━━━━━━━━",
            "",
            f"👤 Req: User",
            f"🔗 Source: {CHANNEL_USERNAME}",
            f"⏱ Time: {result['processing_time']:.1f}s"
        ])
        
        return "\n".join(report)
    
    def generate_commands(self, result: Dict) -> str:
        """Generate commands"""
        if result['atempo']:
            return (
                "**🔧 EXECUTION COMMANDS**\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "**Step 1: Fix Drift (Re-encode)**\n"
                "```\n"
                f"ffmpeg -i audio.m4a -af \"atempo={result['atempo']}\" -c:a aac -b:a 256k audio_fixed.m4a\n"
                "```\n\n"
                "**Step 2: Mux with Delay**\n"
                "```\n"
                f"mkvmerge -o output.mkv video.mkv --sync 0:{result['final_delay']} audio_fixed.m4a\n"
                "```\n\n"
                f"⚙️ **Atempo:** `{result['atempo']}`\n"
                f"⏱️ **Delay:** `{result['final_delay']}ms`\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━"
            )
        else:
            return (
                "**🔧 EXECUTION COMMAND**\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "```\n"
                f"mkvmerge -o output.mkv video.mkv --sync 0:{result['final_delay']} audio.m4a\n"
                "```\n\n"
                f"⏱️ **Delay:** `{result['final_delay']}ms`\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━"
            )
    
    @check_access
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Welcome screen"""
        keyboard = [
            [InlineKeyboardButton("📖 How to Use", callback_data='help'),
             InlineKeyboardButton("ℹ️ About", callback_data='about')],
            [InlineKeyboardButton("📢 Channel", url=CHANNEL_LINK)]
        ]
        
        await update.message.reply_text(
            "**━━━━━━━━━━━━━━━━━━━━━━**\n"
            "🎬 **MWS - AUDIO SYNC BOT**\n"
            "**━━━━━━━━━━━━━━━━━━━━━━**\n\n"
            "*Professional Audio Synchronization*\n\n"
            "**✨ Features:**\n"
            "├ Link support (Direct, GDrive, etc)\n"
            "├ File upload support\n"
            "├ Precise waveform analysis\n"
            "├ Drift detection & auto-fix\n"
            "└ Professional reports\n\n"
            "**📤 Usage:**\n"
            "Send reference video link/file\n"
            "Send new audio link/file\n"
            "Use `/sync` to analyze!\n\n"
            f"**━━━━━━━━━━━━━━━━━━━━━━**\n"
            f"{CHANNEL_USERNAME}",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def callback_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callbacks"""
        query = update.callback_query
        await query.answer()
        
        if query.data == 'help':
            text = (
                "**📖 HOW TO USE**\n\n"
                "**Method 1: Links**\n"
                "Send video link\n"
                "Send audio link\n"
                "`/sync`\n\n"
                "**Method 2: Files**\n"
                "Upload video file\n"
                "Upload audio file\n"
                "`/sync`\n\n"
                "**Supported:**\n"
                "✅ Direct HTTP links\n"
                "✅ Google Drive links\n"
                "✅ File uploads (document/media)\n\n"
                "**Commands:**\n"
                "/start - Welcome\n"
                "/sync - Analyze\n"
                "/clear - Clear data"
            )
        elif query.data == 'about':
            text = (
                "**ℹ️ ABOUT**\n\n"
                "**Technology:**\n"
                "├ Waveform correlation\n"
                "├ Multi-downloader support\n"
                "├ Professional accuracy\n"
                "└ Auto drift detection\n\n"
                "**Powered by:**\n"
                f"{CHANNEL_USERNAME}\n\n"
                "**Version:** 1.0 Production"
            )
        else:
            return
        
        await query.edit_message_text(text, parse_mode='Markdown')
    
    @check_access
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle links and files"""
        user_id = update.effective_user.id
        
        if user_id not in self.user_data:
            self.user_data[user_id] = {}
        
        # Check if it's a link
        if update.message.text and ('http://' in update.message.text or 'https://' in update.message.text):
            link = update.message.text.strip()
            
            if 'reference' not in self.user_data[user_id]:
                self.user_data[user_id]['reference'] = ('link', link)
                await update.message.reply_text(
                    f"✅ **Reference Link Received**\n\n"
                    f"`{link[:60]}...`\n\n"
                    f"Now send audio link/file"
                )
            else:
                self.user_data[user_id]['audio'] = ('link', link)
                await update.message.reply_text(
                    f"✅ **Audio Link Received**\n\n"
                    f"`{link[:60]}...`\n\n"
                    f"Ready! Use `/sync` to analyze"
                )
        
        # Handle document/media files
        elif update.message.document or update.message.video or update.message.audio:
            file_obj = update.message.document or update.message.video or update.message.audio
            
            # Download file
            file = await context.bot.get_file(file_obj.file_id)
            user_dir = WORK_DIR / str(user_id)
            user_dir.mkdir(exist_ok=True)
            
            file_path = user_dir / (file_obj.file_name or f"file_{file_obj.file_id}")
            await file.download_to_drive(file_path)
            
            # Determine type
            if 'reference' not in self.user_data[user_id]:
                self.user_data[user_id]['reference'] = ('file', file_path)
                await update.message.reply_text(
                    f"✅ **Reference File Received**\n\n"
                    f"Name: `{file_path.name}`\n"
                    f"Size: {file_obj.file_size / (1024**2):.1f} MB\n\n"
                    f"Now send audio link/file"
                )
            else:
                self.user_data[user_id]['audio'] = ('file', file_path)
                await update.message.reply_text(
                    f"✅ **Audio File Received**\n\n"
                    f"Name: `{file_path.name}`\n"
                    f"Size: {file_obj.file_size / (1024**2):.1f} MB\n\n"
                    f"Ready! Use `/sync` to analyze"
                )
    
    @check_access
    async def sync_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Main sync command"""
        user_id = update.effective_user.id
        
        if user_id not in self.user_data or len(self.user_data[user_id]) < 2:
            await update.message.reply_text(
                "❌ **Missing Data**\n\n"
                "Send:\n"
                "1️⃣ Reference video (link/file)\n"
                "2️⃣ New audio (link/file)\n\n"
                "Then use `/sync`"
            )
            return
        
        status = await update.message.reply_text(
            "⏳ **Processing Started**\n\n"
            "├ Preparing...\n"
            "└ Please wait..."
        )
        
        try:
            user_dir = WORK_DIR / str(user_id)
            user_dir.mkdir(exist_ok=True)
            
            ref_type, ref_data = self.user_data[user_id]['reference']
            audio_type, audio_data = self.user_data[user_id]['audio']
            
            # Download if links
            if ref_type == 'link':
                await status.edit_text("📥 Downloading reference...")
                ref_file = user_dir / "reference"
                if not await self.downloader.download(ref_data, ref_file):
                    await update.message.reply_text("❌ Reference download failed")
                    return
            else:
                ref_file = ref_data
            
            if audio_type == 'link':
                await status.edit_text("📥 Downloading audio...")
                audio_file = user_dir / "audio"
                if not await self.downloader.download(audio_data, audio_file):
                    await update.message.reply_text("❌ Audio download failed")
                    return
            else:
                audio_file = audio_data
            
            # Analyze
            await status.edit_text("🔬 Analyzing...")
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, self.engine.analyze, ref_file, audio_file
            )
            
            if not result['success']:
                await update.message.reply_text(f"❌ Analysis failed: {result['error']}")
                return
            
            # Send results
            report = self.generate_report(result)
            commands = self.generate_commands(result)
            
            await status.delete()
            await update.message.reply_text(report, parse_mode='Markdown')
            await update.message.reply_text(commands, parse_mode='Markdown')
            
            # Cleanup
            del self.user_data[user_id]
        
        except Exception as e:
            logger.error(f"Sync error: {e}", exc_info=True)
            await status.edit_text(f"❌ Error: {str(e)}")
    
    @check_access
    async def clear_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Clear user data"""
        user_id = update.effective_user.id
        
        if user_id in self.user_data:
            del self.user_data[user_id]
        
        user_dir = WORK_DIR / str(user_id)
        if user_dir.exists():
            shutil.rmtree(user_dir)
        
        await update.message.reply_text("🗑 **Data Cleared**")
    
    async def adduser_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Admin: add user"""
        if update.effective_user.id != OWNER_ID:
            return
        
        if context.args:
            try:
                new_id = int(context.args[0])
                ALLOWED_USERS.append(new_id)
                await update.message.reply_text(f"✅ Added: {new_id}")
            except:
                await update.message.reply_text("❌ Invalid ID")
    
    def run(self):
        """Start bot"""
        app = Application.builder().token(self.token).build()
        
        app.add_handler(CommandHandler("start", self.start_command))
        app.add_handler(CommandHandler("sync", self.sync_command))
        app.add_handler(CommandHandler("clear", self.clear_command))
        app.add_handler(CommandHandler("adduser", self.adduser_command))
        app.add_handler(CallbackQueryHandler(self.callback_handler))
        app.add_handler(MessageHandler(
            filters.TEXT | filters.Document.ALL | filters.VIDEO | filters.AUDIO,
            self.handle_message
        ))
        
        logger.info("🎬 MWS - Audio Sync Bot Started!")
        logger.info(f"Channel: {CHANNEL_USERNAME}")
        logger.info(f"Allowed: {ALLOWED_USERS}")
        
        app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("🎬 MWS - AUDIO SYNC BOT v1.0")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"Channel: {CHANNEL_USERNAME}")
    print(f"Access: {ALLOWED_USERS}")
    print("Status: Production Ready ✅\n")
    
    bot = MWSAudioSyncBot(BOT_TOKEN)
    bot.run()
