# 🚀 Complete Setup Guide

## System Setup

### Ubuntu/Debian

```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install FFmpeg & MediaInfo
sudo apt-get install -y ffmpeg mediainfo

# Install downloaders
sudo apt-get install -y aria2 wget curl

# Install Python dependencies
sudo apt-get install -y python3-pip python3-dev

# Optional: Install yt-dlp (for YouTube support)
sudo wget https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -O /usr/local/bin/yt-dlp
sudo chmod a+rx /usr/local/bin/yt-dlp

# Optional: Install gdown (for Google Drive)
pip3 install gdown
```

### CentOS/RHEL

```bash
# Enable EPEL
sudo yum install -y epel-release

# Install packages
sudo yum install -y ffmpeg mediainfo aria2 wget curl python3-pip
```

## Bot Setup

### 1. Clone Repository

```bash
cd ~
git clone https://github.com/tanjirokamadovsmuzankibutsuzi-source/syncbot.git
cd syncbot
```

### 2. Install Python Dependencies

```bash
# Using pip
pip3 install -r requirements.txt

# Or using virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Get Bot Token

1. Open Telegram
2. Search for @BotFather
3. Send `/newbot`
4. Follow instructions
5. Copy your bot token

### 4. Get Your User ID

1. Search @userinfobot on Telegram
2. Send any message
3. Bot will reply with your user ID
4. Copy the number

### 5. Configure Bot

Edit `bot.py`:

```bash
nano bot.py
```

Find and update these lines:

```python
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
ALLOWED_USERS = [YOUR_USER_ID_HERE]
OWNER_ID = YOUR_USER_ID_HERE
```

Save: `Ctrl+O`, Enter, `Ctrl+X`

### 6. Test Run

```bash
python3 bot.py
```

You should see:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎬 MWS - AUDIO SYNC BOT v1.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Channel: @MuxingWorkStation
Access: [YOUR_ID]
Status: Production Ready ✅
```

Press `Ctrl+C` to stop.

## Running in Production

### Method 1: nohup (Simple)

```bash
nohup python3 bot.py > bot.log 2>&1 &
```

Check status:
```bash
tail -f bot.log
```

Stop:
```bash
pkill -f bot.py
```

### Method 2: screen (Better)

```bash
# Start new screen
screen -S syncbot

# Run bot
python3 bot.py

# Detach: Ctrl+A then D

# Reattach later
screen -r syncbot

# List screens
screen -ls
```

### Method 3: systemd (Best)

Create service file:
```bash
sudo nano /etc/systemd/system/syncbot.service
```

Add:
```ini
[Unit]
Description=MWS Audio Sync Bot
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/home/YOUR_USERNAME/syncbot
ExecStart=/usr/bin/python3 /home/YOUR_USERNAME/syncbot/bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable syncbot
sudo systemctl start syncbot
```

Check status:
```bash
sudo systemctl status syncbot
```

View logs:
```bash
sudo journalctl -u syncbot -f
```

## Troubleshooting

### Bot not starting

**Check Python version:**
```bash
python3 --version  # Should be 3.8+
```

**Check dependencies:**
```bash
pip3 list | grep -E "telegram|numpy|scipy|pymediainfo"
```

**Reinstall if needed:**
```bash
pip3 install --upgrade -r requirements.txt
```

### FFmpeg not found

```bash
# Check installation
ffmpeg -version

# Install if missing
sudo apt-get install ffmpeg
```

### aria2c not found

```bash
# Check
aria2c --version

# Install
sudo apt-get install aria2
```

### Download fails

**Check network:**
```bash
ping google.com
```

**Test download manually:**
```bash
aria2c "YOUR_LINK" -d /tmp
```

**Check if link is accessible:**
```bash
curl -I "YOUR_LINK"
```

### Permission denied

```bash
chmod +x bot.py
chmod 755 workspace/ temp/
```

### Out of space

```bash
# Check disk space
df -h

# Clean workspace
rm -rf workspace/*
rm -rf temp/*
```

## Monitoring

### Check if bot is running

```bash
ps aux | grep bot.py
```

### View logs

```bash
# If using nohup
tail -f bot.log

# If using systemd
sudo journalctl -u syncbot -f

# Last 100 lines
tail -100 bot.log
```

### Check resource usage

```bash
# Memory
free -h

# Disk
df -h

# CPU
top
```

## Maintenance

### Update bot

```bash
cd ~/syncbot
git pull origin main
pip3 install --upgrade -r requirements.txt

# Restart
sudo systemctl restart syncbot
# Or kill and restart manually
```

### Clean old files

```bash
# Clean workspace (older than 1 day)
find workspace/ -type f -mtime +1 -delete

# Clean temp files
rm -rf temp/*

# Clean logs (keep last 1000 lines)
tail -1000 bot.log > bot.log.tmp && mv bot.log.tmp bot.log
```

### Backup configuration

```bash
# Backup bot.py
cp bot.py bot.py.backup

# Backup with timestamp
cp bot.py bot.py.backup.$(date +%Y%m%d)
```

## Adding More Users

### Get their User ID

Ask them to:
1. Message @userinfobot
2. Send you their user ID

### Add to bot

**Method 1: Edit bot.py**
```python
ALLOWED_USERS = [123456, 789012, 345678]
```

**Method 2: Use command** (you must be owner)
```
/adduser 789012
```

## Performance Tuning

### For more users

Increase workers in bot.py:
```python
# Not yet implemented, single-threaded for now
# Future: Add worker pool
```

### For faster downloads

```bash
# Configure aria2c
mkdir -p ~/.config/aria2
nano ~/.config/aria2/aria2.conf
```

Add:
```
max-connection-per-server=16
split=16
min-split-size=1M
continue=true
```

### For large files

Increase sample duration in bot.py:
```python
sample_dur = 450  # Instead of 270
```

## Security

### Restrict access

Only add trusted users to `ALLOWED_USERS`

### Update regularly

```bash
cd ~/syncbot
git pull
```

### Monitor logs

Check for unusual activity:
```bash
grep "ERROR" bot.log
grep "Unauthorized" bot.log
```

## Getting Help

1. Check logs: `tail -f bot.log`
2. Check GitHub issues
3. Ask in @MuxingWorkStation

---

Happy Syncing! 🎬
