"""
Base Bot - Common functionality for all character bots
"""

import discord
from discord.ext import commands
from discord import app_commands
import logging
import asyncio
import os
from typing import Optional, Dict, Any

from dialogue_engine import DialogueEngine
from utils.logger import setup_logger
from config import Config

logger = setup_logger(__name__)

class BaseCharacterBot(commands.Bot):
    """Base class for all character bots in the dialogue system"""
    
    def __init__(self, character_name: str, command_prefix: str = "!", **kwargs):
        # Set up intents
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        
        # Initialize bot
        super().__init__(
            command_prefix=command_prefix,
            intents=intents,
            **kwargs
        )
        
        self.character_name = character_name
        self.config = Config()
        self.dialogue_engine = DialogueEngine(character_name, self)
        
        # Remove default help command
        self.remove_command('help')
        
        # Setup event handlers
        self.setup_events()
    
    def setup_events(self):
        """Setup common event handlers"""
        
        @self.event
        async def on_ready():
            await self._on_ready()
        
        @self.event
        async def on_error(event, *args, **kwargs):
            logger.error(f"Bot error in {event}: {args}, {kwargs}")
    
    async def _on_ready(self):
        """Handle bot ready event"""
        try:
            # Sync slash commands
            await self.tree.sync()
            
            # Start dialogue engine
            await self.dialogue_engine.start_scene_monitoring()
            
            logger.info(f"🤖 {self.character_name} is online as {self.user}!")
            
        except Exception as e:
            logger.error(f"Error in on_ready for {self.character_name}: {e}")
    
    async def close(self):
        """Clean shutdown"""
        try:
            # Stop dialogue engine
            await self.dialogue_engine.stop_scene_monitoring()
            
            # Close bot connection
            await super().close()
            
            logger.info(f"{self.character_name} bot closed successfully")
            
        except Exception as e:
            logger.error(f"Error closing {self.character_name} bot: {e}")
    
    def add_scene_commands(self):
        """Add scene management commands (only for coordinator bots)"""
        
        @self.tree.command(name="startscene", description="Begin a dialogue scene")
        @app_commands.describe(scene_name="The JSON filename of the scene")
        async def start_scene(interaction: discord.Interaction, scene_name: str = "scene1_orlin.json"):
            await interaction.response.defer()
            
            result = await self.dialogue_engine.start_scene_command(scene_name)
            
            if result["success"]:
                await interaction.followup.send(result["message"])
            else:
                await interaction.followup.send(result["message"], ephemeral=True)
        
        @self.tree.command(name="stopscene", description="Stop the current dialogue scene")
        async def stop_scene(interaction: discord.Interaction):
            await interaction.response.defer()
            
            result = await self.dialogue_engine.stop_scene_command()
            
            if result["success"]:
                await interaction.followup.send(result["message"])
            else:
                await interaction.followup.send(result["message"], ephemeral=True)
        
        @self.tree.command(name="scenestatus", description="Get current scene status")
        async def scene_status(interaction: discord.Interaction):
            await interaction.response.defer()
            
            status = await self.dialogue_engine.get_scene_status()
            
            if status.get("active"):
                embed = discord.Embed(
                    title="🎭 Scene Status",
                    description="A scene is currently active",
                    color=discord.Color.green()
                )
                embed.add_field(name="Scene", value=status.get("scene", "Unknown"), inline=True)
                embed.add_field(name="Current Node", value=status.get("current_node", "Unknown"), inline=True)
                embed.add_field(name="Next Speaker", value=status.get("next_speaker", "Unknown"), inline=True)
                
                if status.get("started_at"):
                    embed.add_field(name="Started At", value=status["started_at"], inline=False)
                
                await interaction.followup.send(embed=embed)
            else:
                embed = discord.Embed(
                    title="🎭 Scene Status",
                    description="No scene is currently active",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
        
        @self.tree.command(name="listscenes", description="List available dialogue scenes")
        async def list_scenes(interaction: discord.Interaction):
            await interaction.response.defer()
            
            scenes = await self.dialogue_engine.list_scenes()
            
            if scenes:
                embed = discord.Embed(
                    title="📚 Available Scenes",
                    description="\n".join([f"• {scene}" for scene in scenes]),
                    color=discord.Color.blue()
                )
            else:
                embed = discord.Embed(
                    title="📚 Available Scenes",
                    description="No scenes found",
                    color=discord.Color.orange()
                )
            
            await interaction.followup.send(embed=embed)
    
    def get_character_color(self) -> discord.Color:
        """Get the character's theme color (to be overridden by subclasses)"""
        return discord.Color.blue()
    
    def get_character_description(self) -> str:
        """Get character description (to be overridden by subclasses)"""
        return f"I am {self.character_name}, a character in the Wispwell realm."
    
    async def send_character_message(self, channel, text: str, embed: bool = False):
        """Send a message as this character"""
        try:
            if embed:
                embed_obj = discord.Embed(
                    description=text,
                    color=self.get_character_color()
                )
                embed_obj.set_author(name=self.character_name)
                await channel.send(embed=embed_obj)
            else:
                message = f"**{self.character_name}:** {text}"
                await channel.send(message)
                
        except Exception as e:
            logger.error(f"Error sending character message for {self.character_name}: {e}")
