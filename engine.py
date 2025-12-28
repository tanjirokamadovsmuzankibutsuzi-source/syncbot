import subprocess
import json
import logging
import numpy as np
from scipy.io import wavfile
from scipy import signal
from pathlib import Path
from config import PROCESS_TIMEOUT

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SurgeonEngine")

class SurgeonEngine:
    def __init__(self):
        self.work_dir = Path("surgery_lab")
        self.work_dir.mkdir(exist_ok=True)

    def _clean_url(self, url):
        return url.strip()

    def get_metadata(self, url, stream_spec="0:a:0"):
        """
        Extracts Metadata & Internal Delay (Crucial for v6.1 accuracy)
        """
        url = self._clean_url(url)
        
        # Parse stream index from "0:a:1" -> stream index 1
        try:
            target_idx = int(stream_spec.split(':')[-1])
        except:
            target_idx = 0

        cmd = [
            'ffprobe', '-v', 'error', 
            '-show_streams', '-show_format', 
            '-print_format', 'json', 
            url
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
            data = json.loads(result.stdout)
            
            # Find the correct audio/video stream
            stream = None
            
            # Agar user ne specific audio track manga hai
            audio_streams = [s for s in data.get('streams', []) if s['codec_type'] == 'audio']
            video_streams = [s for s in data.get('streams', []) if s['codec_type'] == 'video']
            
            if ':v:' in stream_spec and video_streams:
                stream = video_streams[0] # Usually only 1 video
            elif audio_streams:
                if target_idx < len(audio_streams):
                    stream = audio_streams[target_idx]
                else:
                    stream = audio_streams[0]
            
            if not stream: return None

            # 1. Duration
            duration = float(stream.get('duration') or data['format'].get('duration', 0))
            
            # 2. Internal Delay (Start Time)
            start_time = float(stream.get('start_time', 0)) 
            internal_delay = int(start_time * 1000)

            # 3. FPS Logic
            fps = 0.0
            fps_str = "N/A"
            if 'r_frame_rate' in stream:
                n, d = map(int, stream['r_frame_rate'].split('/'))
                if d > 0: 
                    fps = n / d
                    fps_str = f"{fps:.3f}"

            return {
                "duration": duration,
                "fps": fps,
                "fps_str": fps_str,
                "internal_delay": internal_delay,
                "codec": stream.get('codec_name', 'unknown')
            }

        except Exception as e:
            logger.error(f"Metadata Error: {e}")
            return None

    def extract_sample(self, url, start_time, output_file, stream_idx=0):
        """
        Streams only the needed bytes (Fastest method)
        """
        url = self._clean_url(url)
        cmd = [
            'ffmpeg', '-y', '-hide_banner', '-loglevel', 'error',
            '-ss', str(start_time),
            '-i', url,
            '-map', f"0:a:{stream_idx}", # Specific Track
            '-t', '20',
            '-vn', '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1',
            str(output_file)
        ]
        try:
            subprocess.run(cmd, timeout=PROCESS_TIMEOUT, check=True)
            return True
        except Exception:
            return False

    def calculate_offset(self, ref_wav, new_wav):
        """
        Calculates Millisecond Delay between two WAVs
        """
        try:
            if not ref_wav.exists() or not new_wav.exists(): return None
            
            rate, r_data = wavfile.read(ref_wav)
            _, n_data = wavfile.read(new_wav)
            
            # Silence Check (Empty audio detection)
            if np.max(np.abs(r_data)) < 500 or np.max(np.abs(n_data)) < 500:
                return None 

            # Normalize
            r_data = r_data.astype(float) - np.mean(r_data)
            n_data = n_data.astype(float) - np.mean(n_data)
            
            # Correlate
            corr = signal.correlate(n_data, r_data, mode='valid')
            lag = np.argmax(corr)
            final_lag = lag - (len(r_data) - len(n_data))
            
            return (final_lag / rate) * 1000
        except Exception:
            return None

    def cleanup(self):
        import shutil
        if self.work_dir.exists():
            shutil.rmtree(self.work_dir)
            self.work_dir.mkdir()
