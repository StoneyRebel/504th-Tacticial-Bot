import json
import os
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

class DataManager:
    """Centralized data management for all game content"""
    
    def __init__(self):
        self.data_dir = os.path.join(os.path.dirname(__file__))
        self._cache = {}
        logger.info(f"📂 Data directory: {self.data_dir}")
    
    def load_data(self, category: str) -> Dict[str, Any]:
        """Load data from JSON files with caching"""
        if category in self._cache:
            return self._cache[category]
        
        file_path = os.path.join(self.data_dir, f"{category}.json")
        if not os.path.exists(file_path):
            logger.warning(f"📄 Data file not found: {file_path}")
            return {}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self._cache[category] = data
            logger.info(f"✅ Loaded {category}.json")
            return data
        
        except Exception as e:
            logger.error(f"❌ Error loading {file_path}: {e}")
            return {}
    
    def get_factions(self, category: str) -> List[str]:
        """Get list of available factions for a category"""
        data = self.load_data(category)
        return list(data.keys())
    
    def get_items(self, category: str, faction: str = None) -> Dict[str, Any]:
        """Get items from a category, optionally filtered by faction"""
        data = self.load_data(category)
        if faction and faction in data:
            return data[faction]
        return data
    
    def get_item(self, category: str, item_key: str, faction: str = None) -> Dict[str, Any]:
        """Get a specific item"""
        items = self.get_items(category, faction)
        return items.get(item_key, {})

# Global data manager instance
data_manager = DataManager()
