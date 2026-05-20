# Telegram Bot Deployment Guide

This guide describes how to configure, run, and host the Sigma Telegram Bot. The integration lets you interact with your financial database on a computer or VPS using the same commands you use in the terminal.

---

## 1. Prerequisites

### A. Create a Telegram Bot
1. Open Telegram and search for [@BotFather](https://t.me/BotFather).
2. Start a conversation and send the `/newbot` command.
3. Follow the prompts to name your bot and choose a username.
4. Copy the API Token (e.g., `123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ`).

### B. Get Your Telegram User ID
For security, the bot only responds to messages sent by authorized user IDs.
1. Message a bot like [@userinfobot](https://t.me/userinfobot) or [@IDBot](https://t.me/myidbot) on Telegram.
2. Send `/start` to retrieve your numerical User ID (e.g., `987654321`).

---

## 2. Configuration

Run the setup wizard from your command line:
```bash
sgm bot setup
```

You will be prompted to enter:
* **Telegram Bot Token**: Paste the token received from `@BotFather`.
* **Allowed Telegram User IDs**: Input your User ID (or a comma-separated list of IDs if you want to grant access to multiple people).

This updates your `~/.config/sgm/config.toml` to look like this:
```toml
[telegram]
token = "123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ"
allowed_users = [987654321]
```

---

## 3. Running Options

### Option A: Local Run (Foreground / Screen / Tmux)
Start the bot directly using the CLI:
```bash
sgm bot run
```
This is useful for testing or running inside a temporary terminal session like `tmux` or `screen`.

---

### Option B: Local Background Service (systemd / launchd)

For a persistent local installation, run the bot as a background service:

#### 1. Linux (systemd)
Create a service file at `/etc/systemd/system/sgm-bot.service` (adjusting `/youruser/` to your actual home directory):
```ini
[Unit]
Description=Sigma Telegram Bot Service
After=network.target

[Service]
Type=simple
User=youruser
ExecStart=/usr/local/bin/sgm bot run
Restart=on-failure
Environment=HOME=/home/youruser

[Install]
WantedBy=multi-user.target
```
Then enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable sgm-bot.service
sudo systemctl start sgm-bot.service
```

#### 2. macOS (launchd)
Create a plist file at `~/Library/LaunchAgents/com.sigma.bot.plist`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.sigma.bot</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/sgm</string>
        <string>bot</string>
        <string>run</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin</string>
    </dict>
</dict>
</plist>
```
Then load the agent:
```bash
launchctl load ~/Library/LaunchAgents/com.sigma.bot.plist
```

---

### Option C: Containerized Run (Docker Compose - Recommended for VPS)

Docker is the best choice for remote servers and VPS. It isolated dependencies and automatically restarts the bot on failure or reboot.

1. Install Docker and Docker Compose on your server.
2. In the Sigma project root directory, build and launch the container in the background:
   ```bash
   docker-compose up --build -d
   ```
3. Check the logs:
   ```bash
   docker logs -f sgm-telegram-bot
   ```

> [!TIP]
> **Database Syncing**
> The `docker-compose.yml` mounts the host's `~/.config/sgm` and `~/.local/share/sgm` folders into the container. Any transactions logged via Telegram will immediately update the local database on the host machine. You can run CLI commands (like `sgm status` or `sgm log`) on the host, and they will reflect changes made via the Telegram bot instantly!
