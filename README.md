# 504th Tactical Discord Bot

Hell Let Loose tactical information bot for the 504th Devils Network Discord server.

## Features

- 🗺️ **Interactive Maps Browser** - Persistent embed with all HLL maps and variants
- 🚜 **Tank Guides** - Comprehensive tank information by faction
- 🎯 **Personal Responses** - All map views are private (ephemeral)
- 👥 **Multi-user Support** - Designed for 900+ member servers
- 🔄 **Auto-restart** - Systemd service with auto-recovery

## Setup

1. **Clone the repository:**
```bash
   git clone https://github.com/StoneyRebel/504th-Tacticial-Bot.git
   cd 504th-Tacticial-Bot
```

2. **Install dependencies:**
```bash
   pip install -r requirements.txt
```

3. **Create .env file:**
```bash
   cp .env.example .env
   nano .env
```
   Add your Discord bot token:
```
   DISCORD_TOKEN=your_bot_token_here
   ENVIRONMENT=production
   DEBUG=false
   USE_EXTERNAL_ASSETS=false
```

4. **Run the bot:**
```bash
   python3 bot.py
```

## Commands

- `/maps-setup` - Create persistent maps browser (requires Manage Messages)
- `/maps` - Personal temporary maps view
- `/tanks` - View tank guides

## Systemd Service (Linux)

Run as background service:
```bash
sudo systemctl enable hll-bot.service
sudo systemctl start hll-bot.service
```

## File Structure
```
504th-Tacticial-Bot/
├── bot.py              # Main bot file
├── config/
│   └── settings.py     # Configuration settings
├── cogs/
│   ├── maps_command.py # Maps functionality
│   ├── content_manager.py
│   └── base_selector.py
├── data/
│   ├── maps.json       # Map data
│   └── tanks.json      # Tank data
├── assets/             # Map images and assets
└── requirements.txt
```

## License

Private bot for 504th Devils Network

## Credits

Created by stoney7912 for the 504th Devils Network community
