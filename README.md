# 🎬 MWS - Audio Sync Bot

Professional Telegram bot for audio-video synchronization with multi-protocol download support.

**Channel:** [@MuxingWorkStation](https://t.me/MuxingWorkStation)

## ✨ Features

- 🔗 **Link Support** - Direct HTTP, Google Drive, YouTube, etc.
- 📤 **File Upload** - Document & Media files supported
- 🎯 **Precise Analysis** - Waveform correlation with sub-ms accuracy
- 📊 **Drift Detection** - Automatic speed mismatch identification
- 🔧 **Auto-Fix** - Ready-to-use mkvmerge & ffmpeg commands
- 🎨 **Beautiful UI** - Modern interface with inline buttons

## 🚀 Quick Start

### Installation

```bash
git clone https://github.com/tanjirokamadovsmuzankibutsuzi-source/syncbot.git
cd syncbot

# Install Python dependencies
pip install -r requirements.txt

# Install system packages
sudo apt-get update
sudo apt-get install -y ffmpeg mediainfo aria2 wget curl

# Optional: Install additional downloaders
pip install yt-dlp gdown
```

### Configuration

Edit `bot.py`:

```python
BOT_TOKEN = "YOUR_BOT_TOKEN"      # From @BotFather
ALLOWED_USERS = [YOUR_USER_ID]    # Your Telegram user ID
OWNER_ID = YOUR_USER_ID           # Admin ID
```

### Run

```bash
python bot.py
```

## 📖 Usage

### Method 1: Links

```
1. Send reference video link
2. Send new audio link  
3. /sync
```

### Method 2: File Upload

```
1. Upload reference video
2. Upload new audio file
3. /sync
```

### Supported Link Types

- ✅ Direct HTTP/HTTPS
- ✅ Google Drive
- ✅ YouTube (with yt-dlp)
- ✅ Any aria2c supported protocol

### Supported File Types

**Upload:**
- Documents (any file as document)
- Video files (as media)
- Audio files (as media)

## 🛠 Download Methods

Bot automatically selects best downloader:

1. **aria2c** (Primary) - Fast, multi-connection
2. **yt-dlp** - For YouTube/streaming sites
3. **gdown** - For Google Drive
4. **wget** - Fallback #1
5. **curl** - Fallback #2

## 🎯 Commands

- `/start` - Welcome screen
- `/sync` - Analyze uploaded/linked files
- `/clear` - Clear your data
- `/adduser <id>` - (Admin) Add user

## 📊 Output Example

```
**MEDIA SYNC REPORT**
━━━━━━━━━━━━━━━━━━━━━━━━
🎬 video.mkv (3.79 GB)
   └─ Stream : 23.976  [00:22:57]

🎧 audio.m4a (1.56 GB)
   └─ Stream : 48000  [00:22:55]

**WAVEFORM ANALYSIS**
Delay (Start)  : -833.6 ms
Delay (End)    : -824.9 ms
✅ Stable      : +8.7 ms variation

**PERFECT MATCH**
1️⃣ Add Delay     : 834 ms
2️⃣ Mux Directly

⏱ Time: 66.9s
```

## 🔧 System Requirements

### Minimum
- Python 3.8+
- 2GB RAM
- 10GB disk space
- FFmpeg
- MediaInfo

### Recommended
- Python 3.10+
- 4GB RAM
- 50GB disk space
- aria2c installed
- yt-dlp installed

## 📝 License

MIT License - See LICENSE file

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create feature branch
3. Make changes
4. Submit pull request

## 📧 Support

- **Channel:** [@MuxingWorkStation](https://t.me/MuxingWorkStation)
- **Issues:** [GitHub Issues](https://github.com/tanjirokamadovsmuzankibutsuzi-source/syncbot/issues)

## ⭐ Credits

Built with ❤️ by MWS Team

---

**[@MuxingWorkStation](https://t.me/MuxingWorkStation)**
