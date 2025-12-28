
import time

class UIBuilder:
    @staticmethod
    def progress_bar(percent, step_name):
        filled = int(percent / 10)
        bar = "▰" * filled + "▱" * (10 - filled)
        return (
            f"⏳ **Task Processing**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🚀 **Status:** {step_name}\n"
            f"{bar} {percent}%\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )

    @staticmethod
    def format_time(seconds):
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        return f"[{int(h):02d}:{int(m):02d}:{int(s):02d}]"

    @staticmethod
    def generate_report(ref, new, analysis, user_name, total_time):
        
        # --- Logic Extraction ---
        d_start = analysis['start']
        d_end = analysis['end']
        d_mid = analysis['mid']
        drift = d_end - d_start
        
        # --- Final Delay Calculation ---
        # Formula: Ref_Internal + (-1 * Waveform_Offset)
        final_mux_delay = int(ref['internal_delay'] + (-d_start))

        # --- FPS Matcher (v6.1 Logic) ---
        raw_ratio = 1.0
        fps_action = ""
        is_fps_issue = False
        is_cut_issue = analysis['cut_detected']
        
        if abs(drift) > 100 and not is_cut_issue:
            is_fps_issue = True
            # Ratio Calculation
            raw_ratio = ref['duration'] / (ref['duration'] - (drift/1000))
            
            # Standard Detection
            standards = {
                "24 -> 23.976": 1.001,
                "23.976 -> 24": 0.999,
                "25 -> 23.976": 1.0427,
                "23.976 -> 25": 0.9590
            }
            match_found = "Custom"
            for lbl, val in standards.items():
                if abs(raw_ratio - val) < 0.001:
                    match_found = lbl
                    break
            
            fps_action = f"1️⃣ **Convert Audio** : `{match_found}`\n"

        # --- STATUS HEADER ---
        if is_cut_issue:
            status_header = "❌ **CUT/JUMP DETECTED**"
        elif is_fps_issue:
            status_header = "⚠️ **ACTION REQUIRED**"
        else:
            status_header = "✅ **PERFECT MATCH**"

        # --- REPORT BUILD ---
        text = (
            f"**MEDIA SYNC REPORT**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🎬 **Video Stream**\n"
            f"   └─ FPS: `{ref['fps_str']}`  Dur: {UIBuilder.format_time(ref['duration'])}\n\n"
            f"🎧 **Audio Stream**\n"
            f"   └─ FPS: `{new['fps_str']}`  Dur: {UIBuilder.format_time(new['duration'])}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"**RAW DATA CHECK**\n"
            f"Stream        FPS       Delay(Int)\n"
            f"────────────  ────────  ──────────\n"
            f"Video       : {ref['fps_str']:<8}  {ref['internal_delay']}ms\n"
            f"Audio       : {new['fps_str']:<8}  -\n"
            f"Raw Diff    :           [{abs(drift):.0f}ms]\n"
            f"- - - - - - - - - - - - - - - - - -\n\n"
        )

        # --- ANALYSIS ---
        text += "**THREE-POINT ANALYSIS**\n"
        text += f"Delay (Start)  : {d_start:.1f} ms\n"
        text += f"Delay (Mid)    : {d_mid:.1f} ms\n"
        text += f"Delay (End)    : {d_end:.1f} ms\n"
        
        if is_cut_issue:
            text += f"🚨 **Jump Detected** (Midpoint Mismatch)\n"
        elif is_fps_issue:
            text += f"🚨 **Drift Detected** ({drift:.0f}ms)\n"
        else:
            text += f"✅ **Stable Sync**\n"
        
        text += f"- - - - - - - - - - - - - - - - - -\n\n"

        # --- ACTION ---
        text += f"**{status_header}**\n"
        
        if is_cut_issue:
            text += "1️⃣ **Manual Fix Required**\n"
            text += "   Audio has cuts or extra scenes."
        elif is_fps_issue:
            text += fps_action
            text += f"2️⃣ **Fix Drift** : `atempo={raw_ratio:.6f}`\n"
            text += f"3️⃣ **Final Mux** : `Delay {int(-d_start)} ms`"
        else:
            text += f"1️⃣ **Add Delay** : `{final_mux_delay} ms`\n"
            text += f"2️⃣ **Mux Directly**"

        text += f"\n━━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += f"👤 Req: {user_name}\n"
        text += f"⏱ Time: {total_time:.1f}s"

        return text
