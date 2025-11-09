from discord.ext import commands
from .base_selector import GenericSelector

class ContentManager(commands.Cog):
    """Manages registration of all content types"""
    
    def __init__(self, bot):
        self.bot = bot
        self.register_content_types()
    
    def register_content_types(self):
        """Register all content types as commands"""
        content_types = [
            {
                'category': 'tanks',
                'command': 'tanks',
                'description': 'View tank guides and tactical information'
            },
            {
                'category': 'weapons',
                'command': 'weapons', 
                'description': 'View weapon guides and stats'
            },
            {
                'category': 'roles',
                'command': 'roles',
                'description': 'View role guides and loadouts'
            },
            {
                'category': 'vehicles',
                'command': 'vehicles',
                'description': 'View vehicle guides and tactics'
            },
            {
                'category': 'tips',
                'command': 'tips',
                'description': 'View gameplay tips and strategies'
            }
        ]
        
        for content in content_types:
            selector = GenericSelector(
                self.bot,
                content['category'],
                content['command'],
                content['description']
            )
            selector.create_command()

async def setup(bot):
    await bot.add_cog(ContentManager(bot))
