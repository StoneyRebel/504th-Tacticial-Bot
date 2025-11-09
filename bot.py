import discord
from discord.ext import commands
import asyncio
import os
import logging
from config.settings import Settings

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

@bot.event
async def on_ready():
    logger.info(f"✅ Logged in as {bot.user}")
    logger.info(f"🌍 Environment: {Settings.ENVIRONMENT}")
    logger.info(f"🖼️ Using external assets: {Settings.USE_EXTERNAL_ASSETS}")
    logger.info(f"📁 Assets directory: {Settings.ASSETS_DIR}")
    
    # Show available assets (only in debug mode)
    if Settings.DEBUG:
        Settings.initialize_asset_cache()
        asset_count = len(Settings._asset_cache)
        logger.info(f"🎨 Cached {asset_count} asset files")
        if asset_count > 0:
            # Show first few assets as examples
            examples = list(Settings._asset_cache.keys())[:5]
            logger.info(f"   Examples: {', '.join(examples)}")
            if asset_count > 5:
                logger.info(f"   ... and {asset_count - 5} more")
    
    try:
        synced = await bot.tree.sync()
        logger.info(f"✅ Synced {len(synced)} command(s).")
        print(f"\n🎉 Bot is ready! Synced {len(synced)} commands.")
        print(f"🤖 Logged in as: {bot.user}")
        print(f"🏠 Connected to {len(bot.guilds)} guild(s)")
        print("📱 Bot is now online and responding to commands!")
        print("\n💡 Try these commands in Discord:")
        print("   /maps  - View tactical maps")
        print("   /tanks - View tank guides")
    except Exception as e:
        logger.error(f"❌ Error syncing commands: {e}")

@bot.event
async def on_error(event, *args, **kwargs):
    logger.error(f"Bot error in {event}: {args}")

@bot.event 
async def on_command_error(ctx, error):
    logger.error(f"Command error: {error}")

@bot.event
async def on_guild_join(guild):
    logger.info(f"📥 Joined guild: {guild.name} (ID: {guild.id})")

@bot.event
async def on_guild_remove(guild):
    logger.info(f"📤 Left guild: {guild.name} (ID: {guild.id})")

async def load_cogs():
    """Load all cogs from the cogs directory"""
    cogs_loaded = 0
    failed_cogs = []
    
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py') and not filename.startswith('__'):
            try:
                await bot.load_extension(f'cogs.{filename[:-3]}')
                logger.info(f"✅ Loaded {filename}")
                cogs_loaded += 1
            except Exception as e:
                logger.error(f"❌ Failed to load {filename}: {e}")
                failed_cogs.append(filename)
    
    logger.info(f"📦 Loaded {cogs_loaded} cogs total")
    if failed_cogs:
        logger.warning(f"⚠️ Failed to load: {failed_cogs}")
    
    return cogs_loaded, failed_cogs

def quick_setup_check():
    """Quick setup validation - less verbose than full setup"""
    issues = []
    
    # Check token
    if not Settings.DISCORD_TOKEN:
        issues.append("DISCORD_TOKEN not set")
    elif Settings.DISCORD_TOKEN == "your_bot_token_here":
        issues.append("DISCORD_TOKEN still set to placeholder")
    
    # Check basic directories exist
    if not Settings.ASSETS_DIR.exists():
        issues.append("Assets directory missing")
    
    if not Settings.DATA_DIR.exists():
        issues.append("Data directory missing")
    
    # Check for basic data files
    required_files = ['tanks.json', 'maps.json']
    for file in required_files:
        file_path = Settings.DATA_DIR / file
        if not file_path.exists():
            issues.append(f"Missing {file}")
    
    return issues

async def main():
    """Main bot startup function"""
    print("🚀 Starting Hell Let Loose Discord Bot...")
    print("=" * 50)
    
    # Quick setup check (less verbose than full validation)
    print("🔍 Checking configuration...")
    issues = quick_setup_check()
    if issues:
        print("❌ Setup issues found:")
        for issue in issues:
            print(f"   • {issue}")
        print("\n💡 Run 'python setup.py' for detailed setup validation")
        return
    
    print("✅ Configuration check passed")
    
    # Initialize asset cache
    print("📁 Initializing assets...")
    Settings.initialize_asset_cache()
    asset_count = len(Settings._asset_cache) if hasattr(Settings, '_asset_cache') else 0
    print(f"🎨 Loaded {asset_count} asset files")
    
    print("🔄 Loading command modules...")
    
    async with bot:
        # Load all cogs
        cogs_loaded, failed_cogs = await load_cogs()
        
        if cogs_loaded == 0:
            print("❌ No command modules loaded! Bot cannot function.")
            print("💡 Check that cogs/ directory exists and contains .py files")
            return
        
        print(f"📦 Successfully loaded {cogs_loaded} command modules")
        if failed_cogs:
            print(f"⚠️ Failed to load: {', '.join(failed_cogs)}")
        
        # Get bot token
        token = Settings.DISCORD_TOKEN
        if not token:
            print("❌ No Discord token found. Check your .env file.")
            return
        
        print("🔗 Connecting to Discord...")
        try:
            await bot.start(token)
        except discord.LoginFailure:
            print("❌ Invalid Discord token")
            print("💡 Check your DISCORD_TOKEN in .env file")
        except discord.PrivilegedIntentsRequired:
            print("❌ Bot missing required intents")
            print("💡 Enable Message Content Intent in Discord Developer Portal")
        except discord.HTTPException as e:
            print(f"❌ Discord API error: {e}")
        except Exception as e:
            logger.error(f"❌ Bot startup error: {e}")
            print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bot shutdown requested")
        logger.info("Bot shutdown by user")
    except Exception as e:
        print(f"\n💥 Critical error: {e}")
        logger.error(f"Critical error: {e}")
        print("\n💡 Try running 'python setup.py' to diagnose issues")
