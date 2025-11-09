import discord
from discord.ext import commands
from discord import app_commands
from data.data_manager import data_manager
from config.settings import Settings
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Mapping for maps where JSON key doesn't match filename
MAP_NAME_FIXES = {
    'sme': 'SME',
    'elalamein': 'ElAlamein',
    'hurtgen': 'HurtgenV2',
    'phl': 'PHL',
    'smdmv2': 'SMDMV2',
    'elsenborn': 'ElsenbornRidge',
}

class PersonalVariantButton(discord.ui.Button):
    """Variant button that sends personal responses only"""
    def __init__(self, label, suffix, map_key, map_info):
        # Different styles for different variants
        style_map = {
            "Grid": discord.ButtonStyle.primary,
            "NoGrid": discord.ButtonStyle.secondary,
            "SP_NoHQ": discord.ButtonStyle.success,
            "defaultgarries": discord.ButtonStyle.danger
        }
        style = style_map.get(suffix, discord.ButtonStyle.secondary)
        
        super().__init__(label=label, style=style)
        self.suffix = suffix
        self.map_key = map_key
        self.map_info = map_info

    async def callback(self, interaction: discord.Interaction):
        try:
            # Fix map name if needed
            actual_map_name = MAP_NAME_FIXES.get(self.map_key, self.map_key.title())
            
            # Generate filename
            image_filename = f"{actual_map_name}_{self.suffix}.png"
            
            logger.info(f"🗺️ Loading map: {self.map_key} → {actual_map_name} → {image_filename} for {interaction.user}")
            
            # Create embed with user info
            embed = self.create_map_embed(actual_map_name, self.map_info, interaction.user)
            
            # Handle asset loading - ALWAYS EPHEMERAL
            if Settings.USE_EXTERNAL_ASSETS:
                # Use external URL
                image_url = Settings.get_asset_url(image_filename)
                embed.set_image(url=image_url)
                await interaction.response.send_message(embed=embed, ephemeral=True)
                logger.info(f"✅ Sent map {actual_map_name} with external image to {interaction.user}")
                
            else:
                # Use local file
                logger.info(f"📁 Looking for local asset: {image_filename}")
                
                if Settings.DEBUG:
                    Settings.debug_asset_loading(image_filename)
                
                file_obj = Settings.get_asset_file(image_filename)
                if file_obj:
                    embed.set_image(url=f"attachment://{image_filename}")
                    await interaction.response.send_message(embed=embed, file=file_obj, ephemeral=True)
                    logger.info(f"✅ Sent map {actual_map_name} with local image to {interaction.user}")
                else:
                    # No image found, send embed only with warning
                    embed.add_field(
                        name="⚠️ Image Not Available", 
                        value=f"Map image `{image_filename}` could not be loaded.",
                        inline=False
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    logger.warning(f"⚠️ No image found for {image_filename}, sent text only to {interaction.user}")
                    
        except discord.HTTPException as e:
            if "Request entity too large" in str(e).lower():
                logger.error(f"❌ Image too large for {image_filename}")
                embed = self.create_map_embed(actual_map_name, self.map_info, interaction.user)
                embed.add_field(
                    name="⚠️ Image Too Large", 
                    value="The map image is too large to display. Try the external assets option.",
                    inline=False
                )
                try:
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                except Exception as e2:
                    logger.error(f"❌ Failed to send fallback message: {e2}")
            else:
                logger.error(f"❌ HTTP error loading map {self.map_key}: {e}")
                try:
                    error_embed = discord.Embed(
                        title=f"❌ Error Loading {actual_map_name}",
                        description=f"Sorry, there was an error loading the map. Please try again later.",
                        color=0xff0000
                    )
                    await interaction.response.send_message(embed=error_embed, ephemeral=True)
                except Exception as e2:
                    logger.error(f"❌ Failed to send error message: {e2}")
                
        except Exception as e:
            logger.error(f"❌ Error loading map {self.map_key}: {e}")
            try:
                error_embed = discord.Embed(
                    title=f"❌ Error Loading {actual_map_name}",
                    description=f"Sorry, there was an error loading the map. Please try again later.",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=error_embed, ephemeral=True)
            except Exception as e2:
                logger.error(f"❌ Failed to send error message: {e2}")
    
    def create_map_embed(self, map_name: str, map_info: Dict[str, Any], user: discord.User) -> discord.Embed:
        """Create a formatted embed for map information"""
        embed = discord.Embed(
            title=map_info.get("title", f"{map_name} — Tactical Map Briefing"),
            color=0x5865F2
        )
        
        # Add fields with proper formatting
        fields = [
            ("🌍 Terrain", map_info.get("terrain", "No terrain info available")),
            ("🎯 Key Points", map_info.get("points", "No key points info available")),
            ("👥 Infantry Strategy", map_info.get("infantry", "No infantry strategy available")),
            ("🚗 Armor Strategy", map_info.get("armor", "No armor strategy available"))
        ]
        
        for name, value in fields:
            # Truncate if too long
            if len(value) > 1024:
                value = value[:1021] + "..."
            embed.add_field(name=name, value=value, inline=False)
        
        # Add footer with variant info
        embed.set_footer(text=f"Map Variant: {self.suffix} | Personal View for {user.display_name}")
        
        return embed


class PersonalVariantView(discord.ui.View):
    """Personal view for map variants - sent as ephemeral response"""
    def __init__(self, map_key: str, map_info: Dict[str, Any]):
        super().__init__(timeout=300)  # Personal views can have timeout
        
        # Define variants with their display names
        variants = {
            "🗺️ Grid": "Grid",
            "🌍 No Grid": "NoGrid", 
            "⚔️ SP No HQ": "SP_NoHQ",
            "🏠 Default Garries": "defaultgarries"
        }
        
        # Check which variants actually exist for this map
        available_variants = self.check_available_variants(map_key, variants)
        
        if not available_variants:
            # If no variants found, add all as fallback
            available_variants = variants
        
        for label, suffix in available_variants.items():
            self.add_item(PersonalVariantButton(label, suffix, map_key, map_info))
    
    def check_available_variants(self, map_key: str, variants: Dict[str, str]) -> Dict[str, str]:
        """Check which map variants actually exist in assets"""
        if Settings.USE_EXTERNAL_ASSETS:
            # Can't check external assets, return all
            return variants
        
        actual_map_name = MAP_NAME_FIXES.get(map_key, map_key.title())
        available = {}
        
        for label, suffix in variants.items():
            filename = f"{actual_map_name}_{suffix}.png"
            if Settings.get_asset_file(filename) is not None:
                available[label] = suffix
        
        return available
    
    async def on_timeout(self):
        """Handle view timeout"""
        for item in self.children:
            item.disabled = True


class PersistentMapDropdown(discord.ui.Select):
    """Static dropdown that sends personal responses only"""
    def __init__(self):
        # Load maps data each time to ensure freshness
        maps_data = data_manager.load_data('maps')
        
        if not maps_data:
            options = [discord.SelectOption(
                label="No maps available",
                value="none",
                description="No map data found"
            )]
        else:
            # Create options with proper character limits
            options = []
            for map_key, map_info in maps_data.items():
                # Get a short description from terrain info
                description = map_info.get('terrain', '')
                if len(description) > 94:
                    truncate_at = 94
                    for i in range(94, max(60, len(description) - 20), -1):
                        if description[i] in [' ', '.', ',', ';']:
                            truncate_at = i
                            break
                    description = description[:truncate_at].rstrip() + "..."
                elif not description:
                    description = "Tactical map information available"
                
                description = description[:100]
                
                # Clean up map name for display
                display_name = self.get_display_name(map_key)
                
                options.append(discord.SelectOption(
                    label=display_name,
                    value=map_key,
                    description=description,
                    emoji="🗺️"
                ))
        
        super().__init__(
            placeholder="🎯 Select a map to view tactical information...", 
            min_values=1, 
            max_values=1, 
            options=options,
            custom_id="persistent_map_select"
        )
    
    def get_display_name(self, map_key: str) -> str:
        """Get proper display name for map"""
        display_name = map_key.title().replace('_', ' ')
        name_map = {
            'sme': 'Sainte-Mère-Église',
            'phl': 'Purple Heart Lane',
            'smdmv2': 'Saint-Marie-du-Mont V2',
            'elalamein': 'El Alamein'
        }
        return name_map.get(map_key.lower(), display_name)

    async def callback(self, interaction: discord.Interaction):
        # Get fresh data for each interaction
        maps_data = data_manager.load_data('maps')
        
        if self.values[0] == "none" or not maps_data:
            await interaction.response.send_message(
                "❌ No map data available at this time.",
                ephemeral=True
            )
            return
            
        selected = self.values[0]
        map_info = maps_data.get(selected)
        
        if not map_info:
            await interaction.response.send_message(
                f"❌ Map data for '{selected}' not found.",
                ephemeral=True
            )
            return
        
        logger.info(f"🗺️ Map selected: {selected} by {interaction.user}")

        try:
            # Create personal variant view
            view = PersonalVariantView(selected, map_info)
            
            # Create map selection embed - PERSONAL RESPONSE
            map_embed = discord.Embed(
                title=f"🗺️ {self.get_display_name(selected)}",
                description="Choose a map variant below to view detailed tactical information.",
                color=0x5865F2
            )
            
            # Add map info preview
            if map_info.get('terrain'):
                map_embed.add_field(
                    name="🌍 Terrain Overview",
                    value=map_info['terrain'][:300] + ("..." if len(map_info['terrain']) > 300 else ""),
                    inline=False
                )
            
            map_embed.add_field(
                name="📋 Available Variants",
                value="• **🗺️ Grid** - Map with coordinate grid overlay\n"
                      "• **🌍 No Grid** - Clean map without grid\n" 
                      "• **⚔️ SP No HQ** - Special variant without HQ markers\n"
                      "• **🏠 Default Garries** - Map showing default garrison positions",
                inline=False
            )
            
            map_embed.set_footer(
                text=f"Personal map view for {interaction.user.display_name} • Expires in 5 minutes"
            )
            
            # Send EPHEMERAL response
            await interaction.response.send_message(
                embed=map_embed,
                view=view,
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"❌ Error creating map selection for {selected}: {e}")
            await interaction.response.send_message(
                f"❌ Error loading map options for '{selected}'. Please try again.",
                ephemeral=True
            )


class StaticMapView(discord.ui.View):
    """Static view that never changes - only sends personal responses"""
    def __init__(self):
        super().__init__(timeout=None)  # Persistent
        self.add_item(PersistentMapDropdown())
        
        # Add info button
        info_button = discord.ui.Button(
            label="ℹ️ How to Use",
            style=discord.ButtonStyle.secondary,
            custom_id="maps_info"
        )
        info_button.callback = self.show_info
        self.add_item(info_button)
    
    async def show_info(self, interaction: discord.Interaction):
        """Show usage information"""
        info_embed = discord.Embed(
            title="🧭 How to Use the Maps Browser",
            color=0x5865F2
        )
        
        info_embed.add_field(
            name="🎯 Quick Start",
            value="1. Select a map from the dropdown above\n"
                  "2. Choose your preferred variant (Grid, No Grid, etc.)\n"
                  "3. View detailed tactical information\n"
                  "4. Only you will see your responses!",
            inline=False
        )
        
        info_embed.add_field(
            name="🗺️ Map Variants Explained",
            value="• **Grid** - Shows coordinate grid for callouts\n"
                  "• **No Grid** - Clean view without overlays\n"
                  "• **SP No HQ** - Special Operations variant\n"
                  "• **Default Garries** - Shows garrison positions",
            inline=False
        )
        
        info_embed.add_field(
            name="👥 Multi-User Friendly",
            value="Multiple players can use this simultaneously!\n"
                  "Your map selections won't interfere with others.",
            inline=False
        )
        
        info_embed.set_footer(text="This interface is always available for all squad members")
        
        await interaction.response.send_message(embed=info_embed, ephemeral=True)


def create_static_maps_embed() -> discord.Embed:
    """Create the static main maps embed that never changes"""
    # Get current map count
    maps_data = data_manager.load_data('maps')
    map_count = len(maps_data) if maps_data else 0
    
    embed = discord.Embed(
        title="🧭 Hell Let Loose - Tactical Maps Browser",
        description=f"**{map_count} maps available** • Interactive map selection for all squad members\n\n"
                   "🎯 **Select a map below** to view tactical information and variants\n"
                   "👥 **Personal responses only** - your selections won't affect others",
        color=0x5865F2
    )
    
    if maps_data:
        # Show available maps in columns
        map_list = []
        for i, map_key in enumerate(maps_data.keys()):
            if i < 12:  # Show first 12 maps
                display_name = map_key.title().replace('_', ' ')
                if map_key.lower() == 'sme':
                    display_name = 'Sainte-Mère-Église'
                elif map_key.lower() == 'phl':
                    display_name = 'Purple Heart Lane'
                map_list.append(f"• {display_name}")
            elif i == 12:
                map_list.append(f"• *+{len(maps_data) - 12} more maps*")
                break
        
        # Split into two columns
        mid = len(map_list) // 2
        col1 = map_list[:mid]
        col2 = map_list[mid:]
        
        embed.add_field(
            name="📋 Available Maps (Part 1)",
            value="\n".join(col1),
            inline=True
        )
        
        if col2:
            embed.add_field(
                name="📋 Available Maps (Part 2)", 
                value="\n".join(col2),
                inline=True
            )
    
    embed.add_field(
        name="🎮 Features",
        value="✅ Personal responses only\n"
              "✅ Multiple users simultaneously\n" 
              "✅ All map variants available\n"
              "✅ Detailed tactical information\n"
              "✅ Always accessible",
        inline=False
    )
    
    embed.set_footer(
        text="🔄 Maps data auto-refreshes • Use dropdown below to get started"
    )
    
    return embed


class Maps(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="maps", 
        description="View tactical maps (personal, temporary)"
    )
    async def maps(self, interaction: discord.Interaction):
        """Original maps command - creates ephemeral response"""
        logger.info(f"🗺️ Personal maps command used by {interaction.user}")
        
        try:
            maps_data = data_manager.load_data('maps')
            
            if not maps_data:
                await interaction.response.send_message(
                    "❌ No map data available. Please check the data files.",
                    ephemeral=True
                )
                return
            
            # Create personal dropdown
            view = discord.ui.View(timeout=300)
            dropdown = PersistentMapDropdown()
            view.add_item(dropdown)
            
            # Create welcome embed
            welcome_embed = discord.Embed(
                title="🧭 Personal Maps Browser",
                description=f"Select from {len(maps_data)} available maps to view detailed tactical information.",
                color=0x5865F2
            )
            welcome_embed.add_field(
                name="📋 Available Maps",
                value=f"Choose any map: {', '.join(list(maps_data.keys())[:5])}{'...' if len(maps_data) > 5 else ''}",
                inline=False
            )
            welcome_embed.set_footer(text="Personal view • Expires in 5 minutes")
            
            await interaction.response.send_message(
                embed=welcome_embed,
                view=view,
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"❌ Error in personal maps command: {e}")
            await interaction.response.send_message(
                "❌ Sorry, there was an error loading the maps. Please try again later.",
                ephemeral=True
            )

    @app_commands.command(
        name="maps-setup",
        description="Create a persistent interactive maps browser in this channel"
    )
    @app_commands.describe(
        channel="Channel to post the persistent maps browser (optional, defaults to current channel)"
    )
    async def maps_setup(
        self, 
        interaction: discord.Interaction,
        channel: discord.TextChannel = None
    ):
        """Create a static persistent maps embed"""
        
        # Check permissions
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message(
                "❌ You need 'Manage Messages' permission to set up persistent maps.",
                ephemeral=True
            )
            return
        
        target_channel = channel or interaction.channel
        
        try:
            maps_data = data_manager.load_data('maps')
            
            if not maps_data:
                await interaction.response.send_message(
                    "❌ No map data available. Please check the data files.",
                    ephemeral=True
                )
                return
            
            # Create static view and embed
            view = StaticMapView()
            embed = create_static_maps_embed()
            
            # Send to target channel
            message = await target_channel.send(embed=embed, view=view)
            
            # Confirm to user
            await interaction.response.send_message(
                f"✅ **Persistent maps browser created** in {target_channel.mention}!\n\n"
                f"🎯 **Features:**\n"
                f"• Always available for all {interaction.guild.member_count} members\n"
                f"• Personal responses only (no interference between users)\n"
                f"• Auto-refreshing map data\n"
                f"• All {len(maps_data)} maps with variants available\n\n"
                f"💡 **Tip:** Pin the message for easy access!",
                ephemeral=True
            )
            
            logger.info(f"📌 Static persistent maps browser created in {target_channel.name} by {interaction.user}")
            
        except Exception as e:
            logger.error(f"❌ Error creating persistent maps: {e}")
            await interaction.response.send_message(
                "❌ Error creating persistent maps browser. Please try again.",
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(Maps(bot))
