import subprocess
import json
import logging
import numpy as np
from scipy.io import wavfile
from scipy import signal
from pathlib import Path
from config import PROCESS_TIMEOUT

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SyncEngine")

class SyncEngine:
    def __init__(self):
        self.temp_dir = Path("temp_work")
        self.temp_dir.mkdir(exist_ok=True)

    def _clean_url(self, url):
        """URL se spaces aur newline hatata hai"""
        return url.strip()

    def get_metadata(self, url):
        """File ki jankari nikalta hai bina download kiye"""
        url = self._clean_url(url)
        cmd = [
            'ffprobe', 
            '-v', 'error', 
            '-select_streams', 'v:0', 
            '-show_entries', 'stream=r_frame_rate,duration', 
            '-of', 'json', 
            url
        ]
        
        try:
            # 15 second ka timeout taaki latke nahi
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
            data = json.loads(result.stdout)
            
            stream = data['streams'][0]
            duration = float(stream.get('duration', 0))
            
            # FPS Calculation
            fps = 0.0
            if 'r_frame_rate' in stream:
                num, den = map(int, stream['r_frame_rate'].split('/'))
                if den > 0:
                    fps = num / den
            
            return {"duration": duration, "fps": fps}
        except Exception as e:
            logger.error(f"Metadata Fail: {e}")
            return None

    def extract_sample(self, url, start_time, output_file):
        """
        DIRECT STREAMING:
        Bina file download kiye, seedha URL se 20 second ka audio nikalta hai.
        """
        url = self._clean_url(url)
        
        # FFmpeg command jo network streams ke liye optimized hai
        cmd = [
            'ffmpeg', '-y', '-hide_banner', '-loglevel', 'error',
            '-ss', str(start_time),       # Seek to time
            '-i', url,                    # Input URL
            '-t', '20',                   # Sirf 20 second
            '-vn',                        # No Video
            '-acodec', 'pcm_s16le',       # Convert to WAV
            '-ar', '16000',               # 16kHz (Fast Processing)
            '-ac', '1',                   # Mono
            str(output_file)
        ]
        
        try:
            # Timeout zaroori hai agar link slow ho
            subprocess.run(cmd, timeout=PROCESS_TIMEOUT, check=True)
            return True
        except subprocess.TimeoutExpired:
            logger.error("FFmpeg Timed Out! (Link too slow)")
            return False
        except Exception as e:
            logger.error(f"Extraction Error: {e}")
            return False

    def calculate_offset(self, ref_wav, new_wav):
        """Do WAV files ko compare karke delay nikalta hai"""
        try:
            if not ref_wav.exists() or not new_wav.exists():
                return 0.0
                
            rate, r_data = wavfile.read(ref_wav)
            _, n_data = wavfile.read(new_wav)
            
            # Normalize Audio (Volume barabar karna)
            r_data = r_data.astype(float) - np.mean(r_data)
            n_data = n_data.astype(float) - np.mean(n_data)
            
            # Cross Correlation (The Math Magic)
            corr = signal.correlate(n_data, r_data, mode='valid')
            lag = np.argmax(corr)
            
            # Adjustment logic for valid mode
            final_lag = lag - (len(r_data) - len(n_data))
            
            # Samples to Milliseconds
            ms_delay = (final_lag / rate) * 1000
            
            # Agar correlation weak hai (Silence), toh 0 return karo
            if np.max(np.abs(corr)) < 1000: 
                return 0.0
                
            return ms_delay
        except Exception as e:
            logger.error(f"Math Error: {e}")
            return 0.0

    def cleanup(self):
        """Temp files delete karna"""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
            self.temp_dir.mkdir()
