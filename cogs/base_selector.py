import discord
from discord.ext import commands
from discord import app_commands
from data.data_manager import data_manager
from config.settings import Settings
from typing import Dict, Any, List, Optional
import aiohttp
import io
import logging
import os

logger = logging.getLogger(__name__)

class BaseSelectorDropdown(discord.ui.Select):
    """Generic dropdown for selecting items from any category"""
    
    def __init__(self, category: str, faction: str = None, items: Dict[str, Any] = None):
        self.category = category
        self.faction = faction
        
        if items is None:
            items = data_manager.get_items(category, faction)
        
        if not items:
            logger.warning(f"No items found for category '{category}' with faction '{faction}'")
            # Create a placeholder option to prevent Discord errors
            options = [discord.SelectOption(
                label="No items available",
                value="none",
                description="No content found for this category"
            )]
        else:
            # Create options from items
            options = []
            for key, item in items.items():
                try:
                    label = item.get('display_name', key.title())
                    description = item.get('short_description', '')[:100]  # Discord limit
                    emoji = item.get('emoji', None)
                    
                    options.append(discord.SelectOption(
                        label=label,
                        value=key,
                        description=description,
                        emoji=emoji
                    ))
                except Exception as e:
                    logger.error(f"Error creating option for {key}: {e}")
                    # Add a fallback option
                    options.append(discord.SelectOption(
                        label=key.title(),
                        value=key,
                        description="Item details unavailable"
                    ))
        
        super().__init__(
            placeholder=f"Choose a {category.rstrip('s')}...",
            min_values=1,
            max_values=1,
            options=options[:25]  # Discord limit
        )
    
    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "none":
            await interaction.response.send_message(
                "❌ No content available for this category.",
                ephemeral=True
            )
            return
            
        selected_key = self.values[0]
        item_data = data_manager.get_item(self.category, selected_key, self.faction)
        
        if not item_data:
            logger.error(f"No data found for {self.category}/{selected_key}")
            await interaction.response.send_message(
                f"❌ Sorry, data for '{selected_key}' could not be found.",
                ephemeral=True
            )
            return
        
        logger.info(f"🔍 Processing {self.category} selection: {selected_key}")
        
        try:
            embed = self.create_embed(item_data, selected_key)
            files = await self.get_files(item_data, selected_key)
            
            logger.info(f"📎 Created {len(files)} file attachments")
            
            await interaction.response.send_message(
                embed=embed,
                files=files,
                ephemeral=True
            )
            logger.info(f"✅ Successfully sent {self.category} info for {selected_key}")
            
        except discord.errors.RequestEntityTooLarge:
            logger.error(f"❌ Files too large for {selected_key}, trying without attachments")
            try:
                embed = self.create_embed(item_data, selected_key, include_thumbnails=False)
                await interaction.response.send_message(
                    embed=embed,
                    ephemeral=True
                )
                logger.warning(f"⚠️ Sent {selected_key} without attachments (too large)")
            except Exception as e2:
                logger.error(f"❌ Complete failure sending {selected_key}: {e2}")
                await self._send_error_message(interaction, selected_key)
                
        except Exception as e:
            logger.error(f"❌ Error sending message for {selected_key}: {e}")
            await self._send_error_message(interaction, selected_key)
    
    async def _send_error_message(self, interaction: discord.Interaction, selected_key: str):
        """Send a fallback error message"""
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    f"❌ Sorry, there was an error loading '{selected_key}'. Please try again later.",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    f"❌ Sorry, there was an error loading '{selected_key}'. Please try again later.",
                    ephemeral=True
                )
        except Exception as e:
            logger.error(f"❌ Failed to send error message: {e}")
    
    def create_embed(self, item_data: Dict[str, Any], key: str, include_thumbnails: bool = True) -> discord.Embed:
        """Create embed from item data"""
        try:
            embed = discord.Embed(
                title=item_data.get('title', key.title()),
                color=int(item_data.get('color', '0x5865F2'), 16)
            )
        except ValueError:
            # Fallback if color is invalid
            embed = discord.Embed(
                title=item_data.get('title', key.title()),
                color=0x5865F2
            )
        
        # Add all fields from data
        field_count = 0
        for field_key, field_value in item_data.items():
            if field_key.startswith('field_') and field_count < 25:  # Discord embed limit
                try:
                    field_name = field_key.replace('field_', '').replace('_', ' ').title()
                    # Truncate field values if too long
                    if len(str(field_value)) > 1024:
                        field_value = str(field_value)[:1021] + "..."
                    
                    embed.add_field(
                        name=field_name,
                        value=field_value,
                        inline=item_data.get(f"{field_key}_inline", False)
                    )
                    field_count += 1
                except Exception as e:
                    logger.error(f"Error adding field {field_key}: {e}")
        
        # Set thumbnail if available and requested
        if include_thumbnails and 'thumbnail' in item_data:
            thumbnail_path = item_data['thumbnail']
            # Remove "attachment://" prefix if present
            if thumbnail_path.startswith('attachment://'):
                thumbnail_path = thumbnail_path.replace('attachment://', '')
            
            if Settings.USE_EXTERNAL_ASSETS:
                embed.set_thumbnail(url=Settings.get_asset_url(thumbnail_path))
            else:
                # For local assets - use attachment format
                embed.set_thumbnail(url=f"attachment://{thumbnail_path}")
                logger.info(f"🖼️ Set thumbnail to attachment://{thumbnail_path}")
        
        return embed
    
    async def get_files(self, item_data: Dict[str, Any], key: str) -> List[discord.File]:
        """Get files for the embed"""
        files = []
        
        if Settings.USE_EXTERNAL_ASSETS:
            logger.info("🌐 Using external assets, no files to attach")
            return files
        
        logger.info("📁 Using local assets, creating file attachments")
        
        # Local file handling - thumbnail
        if 'thumbnail' in item_data:
            thumbnail_file = item_data['thumbnail']
            # Remove "attachment://" prefix if present
            if thumbnail_file.startswith('attachment://'):
                thumbnail_file = thumbnail_file.replace('attachment://', '')
            
            logger.info(f"🔍 Looking for thumbnail: {thumbnail_file}")
            
            if Settings.DEBUG:
                Settings.debug_asset_loading(thumbnail_file)
            
            file_obj = Settings.get_asset_file(thumbnail_file)
            if file_obj:
                files.append(file_obj)
                logger.info(f"✅ Added thumbnail file: {thumbnail_file}")
            else:
                logger.warning(f"❌ Failed to load thumbnail: {thumbnail_file}")
        
        # Additional images for local hosting
        additional_images = item_data.get('additional_images', [])
        if additional_images:
            logger.info(f"🔍 Processing {len(additional_images)} additional images")
            
            for image in additional_images:
                logger.info(f"🔍 Looking for additional image: {image}")
                
                if Settings.DEBUG:
                    Settings.debug_asset_loading(image)
                
                file_obj = Settings.get_asset_file(image)
                if file_obj:
                    files.append(file_obj)
                    logger.info(f"✅ Added additional image: {image}")
                else:
                    logger.warning(f"❌ Failed to load additional image: {image}")
        
        # Check total file size to prevent Discord errors
        total_size = sum(file.fp.seek(0, 2) or file.fp.tell() for file in files)
        for file in files:
            file.fp.seek(0)  # Reset file pointer
        
        if total_size > 25 * 1024 * 1024:  # 25MB Discord limit
            logger.warning(f"⚠️ Total file size ({total_size / 1024 / 1024:.1f}MB) exceeds Discord limit")
            files = files[:3]  # Limit to first 3 files
            logger.info(f"📎 Reduced to {len(files)} files to stay under size limit")
        
        logger.info(f"📎 Total files prepared: {len(files)}")
        return files


class FactionSelectorDropdown(discord.ui.Select):
    """Dropdown for selecting faction when needed"""
    
    def __init__(self, category: str, factions: List[str]):
        self.category = category
        
        options = []
        faction_config = {
            'us': {'name': 'United States', 'emoji': '🇺🇸'},
            'german': {'name': 'Germany', 'emoji': '🇩🇪'},
            'soviet': {'name': 'Soviet Union', 'emoji': '🇷🇺'},
            'british': {'name': 'United Kingdom', 'emoji': '🇬🇧'},
            'ussr': {'name': 'Soviet Union', 'emoji': '🇷🇺'},  # Alternative naming
        }
        
        for faction in factions:
            config = faction_config.get(faction.lower(), {'name': faction.title(), 'emoji': None})
            options.append(discord.SelectOption(
                label=config['name'],
                value=faction,
                emoji=config['emoji']
            ))
        
        super().__init__(
            placeholder="Choose a faction...",
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        selected_faction = self.values[0]
        items = data_manager.get_items(self.category, selected_faction)
        
        if not items:
            await interaction.response.send_message(
                f"❌ No {self.category} found for {selected_faction.title()}.",
                ephemeral=True
            )
            return
        
        view = BaseSelectorView(self.category, selected_faction, items)
        await interaction.response.send_message(
            f"🎯 Selected {selected_faction.title()}. Choose an item:",
            view=view,
            ephemeral=True
        )


class BaseSelectorView(discord.ui.View):
    """Generic view for item selection"""
    
    def __init__(self, category: str, faction: str = None, items: Dict[str, Any] = None):
        super().__init__(timeout=300)
        
        if items is None:
            items = data_manager.get_items(category, faction)
        
        self.add_item(BaseSelectorDropdown(category, faction, items))
    
    async def on_timeout(self):
        """Handle view timeout"""
        for item in self.children:
            item.disabled = True


class GenericSelector(commands.Cog):
    """Generic cog that can handle any content type"""
    
    def __init__(self, bot, category: str, command_name: str, description: str):
        self.bot = bot
        self.category = category
        self.command_name = command_name
        self.description = description
    
    def create_command(self):
        """Dynamically create the slash command"""
        
        @app_commands.command(name=self.command_name, description=self.description)
        async def generic_command(interaction: discord.Interaction):
            logger.info(f"🚀 {self.command_name} command triggered by {interaction.user}")
            
            try:
                factions = data_manager.get_factions(self.category)
                
                if len(factions) <= 1:
                    # Single faction or no factions, go directly to items
                    items = data_manager.get_items(self.category)
                    logger.info(f"📋 Found {len(items)} items in {self.category}")
                    
                    if not items:
                        await interaction.response.send_message(
                            f"❌ No {self.category} data available at this time.",
                            ephemeral=True
                        )
                        return
                    
                    view = BaseSelectorView(self.category, None, items)
                    await interaction.response.send_message(
                        f"🎯 Select a {self.category.rstrip('s')}:",
                        view=view,
                        ephemeral=True
                    )
                else:
                    # Multiple factions, show faction selector first
                    logger.info(f"🏴 Found {len(factions)} factions for {self.category}")
                    
                    view = discord.ui.View(timeout=300)
                    view.add_item(FactionSelectorDropdown(self.category, factions))
                    await interaction.response.send_message(
                        f"🎯 Select a faction for {self.category}:",
                        view=view,
                        ephemeral=True
                    )
                    
            except Exception as e:
                logger.error(f"❌ Error in {self.command_name} command: {e}")
                await interaction.response.send_message(
                    f"❌ Sorry, there was an error loading {self.category}. Please try again later.",
                    ephemeral=True
                )
        
        # Add the command to the bot's tree
        self.bot.tree.add_command(generic_command)

async def setup(bot):
    # This cog is imported by content_manager, no direct setup needed
    pass
