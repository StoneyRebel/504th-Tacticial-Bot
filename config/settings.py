import os
from dotenv import load_dotenv
import logging
from pathlib import Path
from typing import Optional, List

load_dotenv()

logger = logging.getLogger(__name__)

class Settings:
    """Configuration settings for the bot"""
    
    # Bot configuration
    DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
    ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
    DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'
    
    # Asset hosting configuration
    USE_EXTERNAL_ASSETS = os.getenv('USE_EXTERNAL_ASSETS', 'false').lower() == 'true'
    EXTERNAL_ASSET_BASE_URL = os.getenv('EXTERNAL_ASSET_BASE_URL', '')
    
    # Get the project root directory (where bot.py is located)
    PROJECT_ROOT = Path(__file__).parent.parent
    ASSETS_DIR = PROJECT_ROOT / 'assets'
    DATA_DIR = PROJECT_ROOT / 'data'
    
    # Asset cache to avoid repeated file system checks
    _asset_cache = {}
    _cache_initialized = False
    
    @classmethod
    def initialize_asset_cache(cls):
        """Initialize the asset cache for faster lookups"""
        if cls._cache_initialized:
            return
            
        if not cls.ASSETS_DIR.exists():
            logger.warning(f"Assets directory not found: {cls.ASSETS_DIR}")
            cls._cache_initialized = True
            return
        
        try:
            for file_path in cls.ASSETS_DIR.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in ['.png', '.jpg', '.jpeg', '.gif', '.webp']:
                    cls._asset_cache[file_path.name] = file_path
            
            logger.info(f"🎨 Cached {len(cls._asset_cache)} asset files")
            cls._cache_initialized = True
            
        except Exception as e:
            logger.error(f"Error initializing asset cache: {e}")
            cls._cache_initialized = True
    
    @classmethod
    def get_asset_url(cls, filename: str) -> str:
        """Get asset URL - for external hosting or attachment format"""
        if cls.USE_EXTERNAL_ASSETS and cls.EXTERNAL_ASSET_BASE_URL:
            return f"{cls.EXTERNAL_ASSET_BASE_URL.rstrip('/')}/{filename}"
        else:
            return f'attachment://{filename}'
    
    @classmethod
    def get_asset_file(cls, filename: str) -> Optional['discord.File']:
        """Get Discord file object for local assets"""
        if cls.USE_EXTERNAL_ASSETS:
            return None
        
        # Initialize cache if needed
        cls.initialize_asset_cache()
        
        # Check cache first
        if filename in cls._asset_cache:
            asset_path = cls._asset_cache[filename]
            try:
                import discord
                return discord.File(asset_path, filename=filename)
            except Exception as e:
                logger.error(f"❌ Error creating Discord file for {filename}: {e}")
                return None
        
        # If not in cache, try direct path lookup (fallback)
        asset_path = cls.ASSETS_DIR / filename
        if asset_path.exists() and asset_path.is_file():
            try:
                import discord
                # Add to cache for future use
                cls._asset_cache[filename] = asset_path
                return discord.File(asset_path, filename=filename)
            except Exception as e:
                logger.error(f"❌ Error creating Discord file for {filename}: {e}")
                return None
        
        # File not found
        if cls.DEBUG:
            logger.warning(f"⚠️ Asset not found: {filename}")
            # Suggest similar files
            similar_files = cls.find_similar_assets(filename)
            if similar_files:
                logger.info(f"💡 Similar assets found: {', '.join(similar_files[:3])}")
        
        return None
    
    @classmethod
    def find_similar_assets(cls, filename: str) -> List[str]:
        """Find assets with similar names (for debugging)"""
        cls.initialize_asset_cache()
        
        base_name = filename.lower().replace('.png', '').replace('.jpg', '').replace('.jpeg', '')
        similar = []
        
        for asset_name in cls._asset_cache.keys():
            asset_base = asset_name.lower().replace('.png', '').replace('.jpg', '').replace('.jpeg', '')
            if base_name in asset_base or asset_base in base_name:
                similar.append(asset_name)
        
        return similar
    
    @classmethod
    def list_available_assets(cls) -> List[str]:
        """List all available asset files"""
        cls.initialize_asset_cache()
        return sorted(cls._asset_cache.keys())
    
    @classmethod
    def get_asset_stats(cls) -> dict:
        """Get statistics about assets"""
        cls.initialize_asset_cache()
        
        stats = {
            'total_files': len(cls._asset_cache),
            'by_extension': {},
            'total_size': 0
        }
        
        for file_path in cls._asset_cache.values():
            try:
                ext = file_path.suffix.lower()
                stats['by_extension'][ext] = stats['by_extension'].get(ext, 0) + 1
                stats['total_size'] += file_path.stat().st_size
            except Exception:
                pass
        
        return stats
    
    @classmethod
    def verify_setup(cls) -> bool:
        """Verify the bot configuration is correct"""
        issues = []
        
        # Check token
        if not cls.DISCORD_TOKEN:
            issues.append("❌ DISCORD_TOKEN not set in .env file")
        elif cls.DISCORD_TOKEN == "your_bot_token_here":
            issues.append("❌ DISCORD_TOKEN still set to placeholder value")
        
        # Check assets directory
        if not cls.ASSETS_DIR.exists():
            issues.append(f"❌ Assets directory not found: {cls.ASSETS_DIR}")
        else:
            cls.initialize_asset_cache()
            asset_count = len(cls._asset_cache)
            if asset_count == 0:
                issues.append(f"⚠️ No image files found in {cls.ASSETS_DIR}")
            else:
                print(f"✅ Found {asset_count} asset files")
                if cls.DEBUG:
                    stats = cls.get_asset_stats()
                    print(f"   📊 Asset breakdown: {stats['by_extension']}")
                    print(f"   📏 Total size: {stats['total_size'] / 1024 / 1024:.1f} MB")
        
        # Check data files
        required_files = ['tanks.json', 'maps.json']
        
        for file in required_files:
            file_path = cls.DATA_DIR / file
            if not file_path.exists():
                issues.append(f"❌ Required data file missing: {file_path}")
            else:
                try:
                    import json
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    print(f"✅ {file} - valid JSON with {len(data)} entries")
                except json.JSONDecodeError as e:
                    issues.append(f"❌ {file} contains invalid JSON: {e}")
                except Exception as e:
                    issues.append(f"❌ Error reading {file}: {e}")
        
        # Check external asset configuration
        if cls.USE_EXTERNAL_ASSETS:
            if not cls.EXTERNAL_ASSET_BASE_URL:
                issues.append("⚠️ USE_EXTERNAL_ASSETS is true but EXTERNAL_ASSET_BASE_URL is not set")
            else:
                print(f"🌐 External assets enabled: {cls.EXTERNAL_ASSET_BASE_URL}")
        
        if issues:
            print("\n🚨 CONFIGURATION ISSUES:")
            for issue in issues:
                print(f"   {issue}")
            return False
        else:
            print("✅ Bot configuration looks good!")
            return True
    
    @classmethod
    def debug_asset_loading(cls, filename: str):
        """Debug helper to check asset loading"""
        if not cls.DEBUG:
            return
            
        cls.initialize_asset_cache()
        
        logger.info(f"🔍 Debug info for asset: {filename}")
        logger.info(f"🔍 Assets directory: {cls.ASSETS_DIR}")
        logger.info(f"🔍 Assets directory exists: {cls.ASSETS_DIR.exists()}")
        logger.info(f"🔍 File in cache: {filename in cls._asset_cache}")
        
        if filename in cls._asset_cache:
            asset_path = cls._asset_cache[filename]
            logger.info(f"🔍 Cached path: {asset_path}")
            logger.info(f"🔍 File exists: {asset_path.exists()}")
            logger.info(f"🔍 File size: {asset_path.stat().st_size} bytes")
            logger.info(f"🔍 File readable: {os.access(asset_path, os.R_OK)}")
        else:
            direct_path = cls.ASSETS_DIR / filename
            logger.info(f"🔍 Direct path: {direct_path}")
            logger.info(f"🔍 Direct path exists: {direct_path.exists()}")
            
            # Show similar files
            similar = cls.find_similar_assets(filename)
            if similar:
                logger.info(f"🔍 Similar files: {similar[:5]}")
            else:
                logger.info("🔍 No similar files found")
    
    @classmethod
    def refresh_asset_cache(cls):
        """Refresh the asset cache (useful for development)"""
        cls._cache_initialized = False
        cls._asset_cache.clear()
        cls.initialize_asset_cache()
        logger.info("🔄 Asset cache refreshed")
    
    @classmethod
    def validate_data_files(cls) -> dict:
        """Validate all data files and return report"""
        report = {
            'valid_files': [],
            'invalid_files': [],
            'missing_files': [],
            'total_entries': 0
        }
        
        if not cls.DATA_DIR.exists():
            report['error'] = f"Data directory not found: {cls.DATA_DIR}"
            return report
        
        # Check all JSON files in data directory
        for json_file in cls.DATA_DIR.glob('*.json'):
            try:
                import json
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                report['valid_files'].append({
                    'name': json_file.name,
                    'entries': len(data),
                    'size': json_file.stat().st_size
                })
                report['total_entries'] += len(data)
                
            except json.JSONDecodeError as e:
                report['invalid_files'].append({
                    'name': json_file.name,
                    'error': f"JSON error: {e}"
                })
            except Exception as e:
                report['invalid_files'].append({
                    'name': json_file.name,
                    'error': f"Read error: {e}"
                })
        
        return report
