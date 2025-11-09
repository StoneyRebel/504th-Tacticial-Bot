#!/usr/bin/env python3
"""
Hell Let Loose Discord Bot Setup Script
This script helps you get the bot configured and running quickly.
"""

import os
import json
from pathlib import Path

def check_env_file():
    """Check if .env file exists and has required settings"""
    env_path = Path('.env')
    
    if not env_path.exists():
        print("❌ .env file not found!")
        return False
    
    print("✅ .env file found")
    
    # Check contents
    with open(env_path, 'r') as f:
        content = f.read()
    
    if 'your_bot_token_here' in content:
        print("⚠️  Please update DISCORD_TOKEN in .env file")
        return False
    
    if 'DISCORD_TOKEN=' not in content:
        print("❌ DISCORD_TOKEN not found in .env file")
        return False
    
    print("✅ .env file looks configured")
    return True

def check_assets():
    """Check assets directory and files"""
    assets_dir = Path('assets')
    
    if not assets_dir.exists():
        print("❌ assets/ directory not found!")
        return False
    
    # Count image files
    image_files = []
    for ext in ['.png', '.jpg', '.jpeg', '.gif']:
        image_files.extend(assets_dir.glob(f'*{ext}'))
    
    print(f"✅ Assets directory found with {len(image_files)} image files")
    
    # Check for key tank images
    tank_images = ['M8_Greyhound.png', 'M5A1_Stuart.png', 'M4A1_Sherman.png']
    missing_tanks = []
    for tank_img in tank_images:
        if not (assets_dir / tank_img).exists():
            missing_tanks.append(tank_img)
    
    if missing_tanks:
        print(f"⚠️  Missing tank images: {missing_tanks}")
    
    # Check for map images
    map_variants = list(assets_dir.glob('*_Grid.png'))
    print(f"✅ Found {len(map_variants)} map variants")
    
    return True

def check_data_files():
    """Check data JSON files"""
    data_dir = Path('data')
    
    if not data_dir.exists():
        print("❌ data/ directory not found!")
        return False
    
    required_files = ['tanks.json', 'maps.json']
    missing_files = []
    
    for filename in required_files:
        file_path = data_dir / filename
        if not file_path.exists():
            missing_files.append(filename)
        else:
            # Try to load and validate JSON
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                print(f"✅ {filename} - valid JSON with {len(data)} entries")
            except json.JSONDecodeError as e:
                print(f"❌ {filename} - invalid JSON: {e}")
                missing_files.append(filename)
    
    if missing_files:
        print(f"❌ Missing or invalid data files: {missing_files}")
        return False
    
    return True

def check_cogs():
    """Check cogs directory"""
    cogs_dir = Path('cogs')
    
    if not cogs_dir.exists():
        print("❌ cogs/ directory not found!")
        return False
    
    # Count Python files
    py_files = list(cogs_dir.glob('*.py'))
    py_files = [f for f in py_files if not f.name.startswith('__')]
    
    print(f"✅ Found {len(py_files)} cog files:")
    for py_file in py_files:
        print(f"   📄 {py_file.name}")
    
    return True

def create_env_template():
    """Create a template .env file"""
    template = """# Discord Bot Token (get from https://discord.com/developers/applications)
DISCORD_TOKEN=your_bot_token_here

# Environment Configuration
ENVIRONMENT=development
DEBUG=true

# Asset Configuration - Use local files from assets/ folder
USE_EXTERNAL_ASSETS=false
"""
    
    with open('.env', 'w') as f:
        f.write(template)
    
    print("✅ Created .env template file")
    print("📝 Please edit .env and add your Discord bot token")

def main():
    print("🚀 Hell Let Loose Discord Bot Setup")
    print("=" * 50)
    
    all_good = True
    
    # Check .env file
    if not check_env_file():
        create_env_template()
        all_good = False
    
    # Check assets
    if not check_assets():
        all_good = False
    
    # Check data files
    if not check_data_files():
        all_good = False
    
    # Check cogs
    if not check_cogs():
        all_good = False
    
    print("\n" + "=" * 50)
    
    if all_good:
        print("🎉 Setup complete! Your bot is ready to run.")
        print("\nTo start the bot:")
        print("   python bot.py")
    else:
        print("❌ Setup incomplete. Please fix the issues above.")
        print("\nSteps to complete setup:")
        print("1. Get Discord bot token from https://discord.com/developers/applications")
        print("2. Update DISCORD_TOKEN in .env file")
        print("3. Make sure all required files are in place")
    
    print("\n📚 Commands your bot will support:")
    print("   /tanks    - View tank guides")
    print("   /maps     - View map information") 
    print("   /weapons  - View weapon guides")
    print("   /roles    - View role guides")
    print("   /vehicles - View vehicle guides")
    print("   /tips     - View gameplay tips")

if __name__ == "__main__":
    main()
