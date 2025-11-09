#!/usr/bin/env python3
"""
Data Validator for Hell Let Loose Discord Bot
Validates JSON data files and checks for asset references
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Set
from config.settings import Settings

logger = logging.getLogger(__name__)

class DataValidator:
    """Validates bot data files and asset references"""
    
    def __init__(self):
        self.data_dir = Settings.DATA_DIR
        self.assets_dir = Settings.ASSETS_DIR
        self.errors = []
        self.warnings = []
        
    def validate_all(self) -> Dict[str, Any]:
        """Validate all data files and return comprehensive report"""
        report = {
            'valid': True,
            'files_checked': 0,
            'errors': [],
            'warnings': [],
            'asset_issues': [],
            'recommendations': []
        }
        
        self.errors = []
        self.warnings = []
        
        print("🔍 Starting data validation...")
        
        # Validate each JSON file
        for json_file in self.data_dir.glob('*.json'):
            try:
                file_report = self.validate_json_file(json_file)
                report['files_checked'] += 1
                
                if not file_report['valid']:
                    report['valid'] = False
                
                report['errors'].extend(file_report['errors'])
                report['warnings'].extend(file_report['warnings'])
                
            except Exception as e:
                error_msg = f"Failed to validate {json_file.name}: {e}"
                report['errors'].append(error_msg)
                report['valid'] = False
        
        # Check for missing assets
        asset_report = self.validate_asset_references()
        report['asset_issues'] = asset_report['issues']
        report['recommendations'] = asset_report['recommendations']
        
        if asset_report['issues']:
            report['warnings'].extend([f"Asset issue: {issue}" for issue in asset_report['issues']])
        
        return report
    
    def validate_json_file(self, file_path: Path) -> Dict[str, Any]:
        """Validate a single JSON file"""
        report = {
            'file': file_path.name,
            'valid': True,
            'errors': [],
            'warnings': [],
            'entries': 0
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            report['entries'] = len(data)
            
            # File-specific validation
            if file_path.name == 'tanks.json':
                self._validate_tanks_data(data, report)
            elif file_path.name == 'maps.json':
                self._validate_maps_data(data, report)
            else:
                self._validate_generic_data(data, report)
                
        except json.JSONDecodeError as e:
            report['valid'] = False
            report['errors'].append(f"Invalid JSON in {file_path.name}: {e}")
        except Exception as e:
            report['valid'] = False
            report['errors'].append(f"Error reading {file_path.name}: {e}")
        
        return report
    
    def _validate_tanks_data(self, data: Dict[str, Any], report: Dict[str, Any]):
        """Validate tanks.json structure"""
        required_fields = ['display_name', 'title']
        recommended_fields = ['field_nation', 'field_class', 'field_crew']
        
        for faction, tanks in data.items():
            if not isinstance(tanks, dict):
                report['errors'].append(f"Faction '{faction}' should contain a dictionary of tanks")
                report['valid'] = False
                continue
            
            for tank_key, tank_data in tanks.items():
                if not isinstance(tank_data, dict):
                    report['errors'].append(f"Tank '{tank_key}' in faction '{faction}' should be a dictionary")
                    report['valid'] = False
                    continue
                
                # Check required fields
                for field in required_fields:
                    if field not in tank_data:
                        report['errors'].append(f"Tank '{tank_key}' missing required field: {field}")
                        report['valid'] = False
                
                # Check recommended fields
                for field in recommended_fields:
                    if field not in tank_data:
                        report['warnings'].append(f"Tank '{tank_key}' missing recommended field: {field}")
                
                # Validate asset references
                self._check_asset_reference(tank_data.get('thumbnail'), f"Tank {tank_key} thumbnail", report)
                
                for img in tank_data.get('additional_images', []):
                    self._check_asset_reference(img, f"Tank {tank_key} additional image", report)
    
    def _validate_maps_data(self, data: Dict[str, Any], report: Dict[str, Any]):
        """Validate maps.json structure"""
        required_fields = ['title', 'terrain', 'points', 'infantry', 'armor']
        
        for map_key, map_data in data.items():
            if not isinstance(map_data, dict):
                report['errors'].append(f"Map '{map_key}' should be a dictionary")
                report['valid'] = False
                continue
            
            # Check required fields
            for field in required_fields:
                if field not in map_data:
                    report['errors'].append(f"Map '{map_key}' missing required field: {field}")
                    report['valid'] = False
                elif not map_data[field].strip():
                    report['warnings'].append(f"Map '{map_key}' has empty field: {field}")
            
            # Check for old thumbnail references (should be removed)
            if 'thumbnail' in map_data:
                report['warnings'].append(f"Map '{map_key}' has deprecated thumbnail field - remove this as maps use variants")
    
    def _validate_generic_data(self, data: Dict[str, Any], report: Dict[str, Any]):
        """Validate generic data structure"""
        if not isinstance(data, dict):
            report['errors'].append("Root data should be a dictionary")
            report['valid'] = False
            return
        
        # Check for empty entries
        for key, value in data.items():
            if not value:
                report['warnings'].append(f"Entry '{key}' is empty or null")
    
    def _check_asset_reference(self, asset_path: str, context: str, report: Dict[str, Any]):
        """Check if an asset reference is valid"""
        if not asset_path:
            return
        
        # Remove attachment:// prefix if present
        clean_path = asset_path.replace('attachment://', '')
        
        # Check if asset exists
        full_path = self.assets_dir / clean_path
        if not full_path.exists():
            report['warnings'].append(f"{context}: Asset '{clean_path}' not found")
    
    def validate_asset_references(self) -> Dict[str, Any]:
        """Check all asset references and find orphaned assets"""
        report = {
            'issues': [],
            'recommendations': [],
            'referenced_assets': set(),
            'available_assets': set(),
            'orphaned_assets': [],
            'missing_assets': []
        }
        
        # Get all available assets
        if self.assets_dir.exists():
            for asset in self.assets_dir.glob('*'):
                if asset.is_file() and asset.suffix.lower() in ['.png', '.jpg', '.jpeg', '.gif', '.webp']:
                    report['available_assets'].add(asset.name)
        
        # Find all asset references in data files
        for json_file in self.data_dir.glob('*.json'):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                self._extract_asset_references(data, report['referenced_assets'])
                
            except Exception as e:
                report['issues'].append(f"Error reading {json_file.name} for asset validation: {e}")
        
        # Find missing and orphaned assets
        report['missing_assets'] = list(report['referenced_assets'] - report['available_assets'])
        report['orphaned_assets'] = list(report['available_assets'] - report['referenced_assets'])
        
        # Generate recommendations
        if report['missing_assets']:
            report['recommendations'].append(f"Add missing assets: {', '.join(report['missing_assets'])}")
        
        if report['orphaned_assets']:
            report['recommendations'].append(f"Consider removing unused assets: {', '.join(report['orphaned_assets'][:5])}{'...' if len(report['orphaned_assets']) > 5 else ''}")
        
        return report
    
    def _extract_asset_references(self, data: Any, asset_set: Set[str]):
        """Recursively extract asset references from data"""
        if isinstance(data, dict):
            for key, value in data.items():
                if key in ['thumbnail', 'image', 'icon']:
                    if isinstance(value, str):
                        clean_path = value.replace('attachment://', '')
                        asset_set.add(clean_path)
                elif key == 'additional_images' and isinstance(value, list):
                    for img in value:
                        if isinstance(img, str):
                            asset_set.add(img)
                else:
                    self._extract_asset_references(value, asset_set)
        elif isinstance(data, list):
            for item in data:
                self._extract_asset_references(item, asset_set)
    
    def generate_report(self, report: Dict[str, Any]) -> str:
        """Generate a human-readable validation report"""
        lines = []
        lines.append("📋 DATA VALIDATION REPORT")
        lines.append("=" * 50)
        
        if report['valid']:
            lines.append("✅ All data files are valid!")
        else:
            lines.append("❌ Validation failed - issues found")
        
        lines.append(f"\n📊 Summary:")
        lines.append(f"   Files checked: {report['files_checked']}")
        lines.append(f"   Errors: {len(report['errors'])}")
        lines.append(f"   Warnings: {len(report['warnings'])}")
        lines.append(f"   Asset issues: {len(report['asset_issues'])}")
        
        if report['errors']:
            lines.append(f"\n❌ Errors:")
            for error in report['errors']:
                lines.append(f"   • {error}")
        
        if report['warnings']:
            lines.append(f"\n⚠️  Warnings:")
            for warning in report['warnings']:
                lines.append(f"   • {warning}")
        
        if report['recommendations']:
            lines.append(f"\n💡 Recommendations:")
            for rec in report['recommendations']:
                lines.append(f"   • {rec}")
        
        return "\n".join(lines)


def main():
    """Run validation from command line"""
    import sys
    
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    # Initialize and run validation
    validator = DataValidator()
    report = validator.validate_all()
    
    # Print report
    print(validator.generate_report(report))
    
    # Exit with error code if validation failed
    if not report['valid']:
        sys.exit(1)


if __name__ == "__main__":
    main()