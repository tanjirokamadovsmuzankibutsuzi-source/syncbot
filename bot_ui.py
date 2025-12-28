from telegram import InlineKeyboardButton, InlineKeyboardMarkup

class BotUI:
    @staticmethod
    def progress_bar(percent):
        """Ek visual loading bar banata hai"""
        filled = int(percent / 10)
        empty = 10 - filled
        return f"[{'█' * filled}{'░' * empty}] {percent}%"

    @staticmethod
    def status_message(task_id, step, message):
        """Live Status Update Template"""
        return (
            f"📡 **SYNC SERVER v12** | `{task_id}`\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"⚙️ **Status:** {step}\n"
            f"📝 **Info:** {message}\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )

    @staticmethod
    def final_report(ref_meta, start_delay, end_delay, processing_time):
        """Final Report Card"""
        
        drift = end_delay - start_delay
        is_synced = abs(drift) < 50 # 50ms tolerance
        
        # Emoji Logic
        status_icon = "✅ MATCHED" if is_synced else "⚠️ DRIFT DETECTED"
        
        text = (
            f"🎬 **FINAL SYNC REPORT**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"⏱ **Time Taken:** `{processing_time:.1f}s`\n"
            f"🎞 **FPS:** `{ref_meta['fps']:.3f}`\n\n"
            
            f"📍 **Checkpoints:**\n"
            f"├─ Start: `{start_delay:.0f}ms`\n"
            f"└─ End:   `{end_delay:.0f}ms`\n\n"
            
            f"📉 **Drift Analysis:**\n"
            f"└─ Total Drift: `{drift:.0f}ms`\n"
            f"   **{status_icon}**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
        )
        
        # Logic for Commands
        if is_synced:
            # Simple Delay
            final_delay = int(start_delay)
            cmd = (
                f"🛠 **MUX COMMAND:**\n"
                f"`mkvmerge -o out.mkv video.mkv --sync 0:{final_delay} audio.m4a`"
            )
        else:
            # Drift Fix Calculation
            # Ratio = Duration / (Duration - Drift)
            ratio = ref_meta['duration'] / (ref_meta['duration'] - (drift/1000))
            cmd = (
                f"🛠 **FIX COMMANDS:**\n\n"
                f"**1. Fix Speed:**\n"
                f"`ffmpeg -i audio.m4a -af \"atempo={ratio:.6f}\" fixed.m4a`\n\n"
                f"**2. Mux:**\n"
                f"`mkvmerge ... --sync 0:{int(start_delay)} fixed.m4a`"
            )
            
        return text + cmd
