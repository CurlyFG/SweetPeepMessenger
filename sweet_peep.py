"""
Sweet Peep Bot - Main coordinator bot with announcement and birthday features
"""

import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import os
import random
from datetime import datetime, timezone, timedelta
import pytz
from typing import Dict, List

from character_bots.base_bot import BaseCharacterBot
from utils.logger import setup_logger

logger = setup_logger(__name__)

class SweetPeepBot(BaseCharacterBot):
    """Sweet Peep - The main coordinator bot with community features"""
    
    def __init__(self):
        super().__init__(
            character_name="Sweet Peep",
            command_prefix="!",
            description="Sweet Peep - Your friendly Wispwell community bot"
        )
        
        # Data storage
        self.scheduled_announcements = []
        self.birthdays = {}
        self.missed_members = []  # Track members who joined while bot was offline
        self.last_online_time = None
        
        # Add scene management commands (Sweet Peep is the coordinator)
        self.add_scene_commands()
        
        # Add community commands
        self.add_community_commands()
        
        # Load data
        self.load_data()
    
    def get_character_color(self) -> discord.Color:
        """Sweet Peep's theme color - soft pink"""
        return discord.Color.from_rgb(255, 182, 193)  # Light pink
    
    def get_character_description(self) -> str:
        return "I'm Sweet Peep, your friendly community coordinator in Wispwell! I help with announcements, birthdays, and organizing our wonderful dialogue scenes."
    
    async def _on_ready(self):
        """Override ready event to start tasks"""
        await super()._on_ready()
        
        # Process any overdue announcements immediately
        await self.process_overdue_announcements()
        
        # Check for members who joined while bot was offline
        await self.process_missed_members()
        
        # Start periodic tasks
        if not self.check_announcements.is_running():
            self.check_announcements.start()
        
        if not self.check_birthdays.is_running():
            self.check_birthdays.start()
    
    async def close(self):
        """Save last online time before closing"""
        try:
            self.save_last_online()
            await super().close()
        except Exception as e:
            logger.error(f"Error during Sweet Peep shutdown: {e}")
    
    def load_data(self):
        """Load announcements and birthdays data"""
        try:
            # Load announcements
            announcements_file = os.path.join(self.config.DATA_DIR, "announcements.json")
            if os.path.exists(announcements_file):
                with open(announcements_file, "r", encoding="utf-8") as f:
                    self.scheduled_announcements = json.load(f)
            
            # Load birthdays
            birthdays_file = os.path.join(self.config.DATA_DIR, "birthdays.json")
            if os.path.exists(birthdays_file):
                with open(birthdays_file, "r", encoding="utf-8") as f:
                    self.birthdays = json.load(f)
            
            # Load last online time
            last_online_file = os.path.join(self.config.DATA_DIR, "last_online.json")
            if os.path.exists(last_online_file):
                with open(last_online_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.last_online_time = datetime.fromisoformat(data.get("last_online")) if data.get("last_online") else None
            
            logger.info("Loaded Sweet Peep data successfully")
            
        except Exception as e:
            logger.error(f"Error loading Sweet Peep data: {e}")
    
    def save_announcements(self):
        """Save announcements to file"""
        try:
            announcements_file = os.path.join(self.config.DATA_DIR, "announcements.json")
            with open(announcements_file, "w", encoding="utf-8") as f:
                json.dump(self.scheduled_announcements, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving announcements: {e}")
    
    def save_birthdays(self):
        """Save birthdays to file"""
        try:
            birthdays_file = os.path.join(self.config.DATA_DIR, "birthdays.json")
            with open(birthdays_file, "w", encoding="utf-8") as f:
                json.dump(self.birthdays, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving birthdays: {e}")
    
    def save_last_online(self):
        """Save the last online timestamp"""
        try:
            last_online_file = os.path.join(self.config.DATA_DIR, "last_online.json")
            data = {"last_online": datetime.now(timezone.utc).isoformat()}
            with open(last_online_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving last online time: {e}")
    
    async def process_missed_members(self):
        """Check for members who joined while bot was offline and welcome them"""
        try:
            if not self.last_online_time:
                # First time running, set timestamp and skip check
                self.save_last_online()
                return
            
            # Get all guilds the bot is in
            for guild in self.guilds:
                async for member in guild.fetch_members(limit=None):
                    # Check if member joined after last online time
                    if member.joined_at and member.joined_at > self.last_online_time:
                        # Don't welcome bots
                        if not member.bot:
                            logger.info(f"Found member who joined while offline: {member.display_name}")
                            await self.send_delayed_welcome(member)
            
            # Update last online time
            self.save_last_online()
            
        except Exception as e:
            logger.error(f"Error processing missed members: {e}")
    
    async def send_delayed_welcome(self, member):
        """Send welcome message to member who joined while bot was offline"""
        try:
            # Find the general channel or first available text channel
            welcome_channel = None
            for channel in member.guild.text_channels:
                if channel.name in ['general', 'welcome', 'lobby'] or welcome_channel is None:
                    welcome_channel = channel
                    if channel.name in ['general', 'welcome', 'lobby']:
                        break
            
            if welcome_channel:
                delayed_messages = [
                    f"🌥️ Welcome to Wispwell, {member.mention}! Sorry I missed your arrival - I was away from the clouds for a moment!",
                    f"✨ A gentle breeze brings belated greetings to {member.mention}! Welcome to our wonderful community!",
                    f"🌸 {member.mention}, welcome! I'm Sweet Peep, and I'm sorry I wasn't here when you first arrived!",
                    f"🌟 Better late than never! {member.mention}, welcome to Wispwell! I hope you've been settling in well!",
                    f"💫 My apologies for the delayed welcome, {member.mention}! The sanctuary doors are always open for you!",
                ]
                
                message = random.choice(delayed_messages)
                
                embed = discord.Embed(
                    description=message,
                    color=self.get_character_color()
                )
                embed.set_author(name="Sweet Peep - Delayed Welcome", icon_url=self.user.avatar.url if self.user.avatar else None)
                embed.set_footer(text="✨ Welcome to the realm of Wispwell ✨")
                
                await welcome_channel.send(embed=embed)
                logger.info(f"Sent delayed welcome to {member.display_name} in {welcome_channel.name}")
                
        except Exception as e:
            logger.error(f"Error sending delayed welcome to {member.display_name}: {e}")
    
    def add_community_commands(self):
        """Add community management commands"""
        
        # Announcement commands
        @self.tree.command(name="announce", description="Schedule an announcement (mods only)")
        @app_commands.describe(
            message="The announcement text",
            time="Time in format YYYY-MM-DD HH:MM",
            timezone_str="Timezone (e.g. US/Eastern)",
            recurring="Weekly recurring: none, weekly",
            image="Optional image attachment for the announcement"
        )
        @app_commands.choices(recurring=[
            app_commands.Choice(name="One-time only", value="none"),
            app_commands.Choice(name="Weekly recurring", value="weekly")
        ])
        async def announce(interaction: discord.Interaction, message: str, time: str, timezone_str: str, recurring: str = "none", image: discord.Attachment = None):
            if not interaction.user.guild_permissions.manage_messages:
                await interaction.response.send_message("🚫 Only mods can create announcements!", ephemeral=True)
                return
            
            try:
                tz = pytz.timezone(timezone_str)
                local_time = datetime.strptime(time, "%Y-%m-%d %H:%M")
                utc_time = tz.localize(local_time).astimezone(pytz.utc)
            except Exception as e:
                await interaction.response.send_message(f"❗ Time format or timezone error: {e}", ephemeral=True)
                return
            
            # Handle image attachment if provided
            image_url = None
            if image:
                # Validate image file
                if not image.content_type or not image.content_type.startswith('image/'):
                    await interaction.response.send_message("❌ Please provide a valid image file!", ephemeral=True)
                    return
                
                # Store the image URL (Discord URLs are persistent)
                image_url = image.url
            
            announcement = {
                "message": message,
                "time": utc_time.isoformat(),
                "channel_id": interaction.channel_id,
                "recurring": recurring,
                "created_by": interaction.user.display_name,
                "sent": False,
                "image_url": image_url
            }
            
            if recurring == "weekly":
                announcement["next_occurrence"] = utc_time.isoformat()
            
            self.scheduled_announcements.append(announcement)
            self.save_announcements()
            
            recurring_text = " (repeats weekly)" if recurring == "weekly" else ""
            image_text = " with image" if image_url else ""
            await interaction.response.send_message(
                f"✅ Announcement scheduled for {utc_time.strftime('%Y-%m-%d %H:%M UTC')}{recurring_text}{image_text}."
            )
            
            # Send confirmation to the specified channel
            confirmation_channel = self.get_channel(1377107419943145553)
            if confirmation_channel:
                embed = discord.Embed(
                    title="📅 New Announcement Scheduled",
                    description=f"**Message:** {message}\n**Scheduled for:** {utc_time.strftime('%Y-%m-%d %H:%M UTC')}\n**Timezone:** {timezone_str}\n**Recurring:** {recurring.title()}",
                    color=self.get_character_color()
                )
                embed.set_author(name="Sweet Peep - Scheduler")
                embed.add_field(name="Scheduled by", value=interaction.user.mention, inline=True)
                
                if image_url:
                    embed.add_field(name="Includes Image", value="✅ Yes", inline=True)
                    embed.set_thumbnail(url=image_url)
                
                await confirmation_channel.send(embed=embed)
        
        @self.tree.command(name="edit_announcement", description="Edit an existing announcement (mods only)")
        @app_commands.describe(
            announcement_id="ID of the announcement to edit (from list_announcements)",
            new_message="New message text (optional)",
            new_time="New time in YYYY-MM-DD HH:MM format (optional)",
            new_timezone="New timezone (optional)"
        )
        async def edit_announcement(interaction: discord.Interaction, announcement_id: int, new_message: str = None, new_time: str = None, new_timezone: str = None):
            if not interaction.user.guild_permissions.manage_messages:
                await interaction.response.send_message("🚫 Only mods can edit announcements!", ephemeral=True)
                return
            
            if announcement_id >= len(self.scheduled_announcements) or announcement_id < 0:
                await interaction.response.send_message("❌ Invalid announcement ID!", ephemeral=True)
                return
            
            announcement = self.scheduled_announcements[announcement_id]
            
            # Update message if provided
            if new_message:
                announcement["message"] = new_message
            
            # Update time if provided
            if new_time and new_timezone:
                try:
                    tz = pytz.timezone(new_timezone)
                    local_time = datetime.strptime(new_time, "%Y-%m-%d %H:%M")
                    utc_time = tz.localize(local_time).astimezone(pytz.utc)
                    announcement["time"] = utc_time.isoformat()
                except Exception as e:
                    await interaction.response.send_message(f"❗ Time format error: {e}", ephemeral=True)
                    return
            
            self.save_announcements()
            
            embed = discord.Embed(
                title="✏️ Announcement Updated",
                description=f"Announcement #{announcement_id} has been updated successfully!",
                color=self.get_character_color()
            )
            await interaction.response.send_message(embed=embed)
        
        @self.tree.command(name="cancel_announcement", description="Cancel an announcement (mods only)")
        @app_commands.describe(announcement_id="ID of the announcement to cancel (from list_announcements)")
        async def cancel_announcement(interaction: discord.Interaction, announcement_id: int):
            if not interaction.user.guild_permissions.manage_messages:
                await interaction.response.send_message("🚫 Only mods can cancel announcements!", ephemeral=True)
                return
            
            if announcement_id >= len(self.scheduled_announcements) or announcement_id < 0:
                await interaction.response.send_message("❌ Invalid announcement ID!", ephemeral=True)
                return
            
            cancelled = self.scheduled_announcements.pop(announcement_id)
            self.save_announcements()
            
            embed = discord.Embed(
                title="🗑️ Announcement Cancelled",
                description=f"Cancelled: {cancelled['message'][:100]}{'...' if len(cancelled['message']) > 100 else ''}",
                color=self.get_character_color()
            )
            await interaction.response.send_message(embed=embed)

        @self.tree.command(name="list_announcements", description="List upcoming announcements")
        @app_commands.describe(date="Optional: filter by YYYY-MM-DD date")
        async def list_announcements(interaction: discord.Interaction, date: str = None):
            filtered = self.scheduled_announcements
            
            if date:
                try:
                    filter_date = datetime.strptime(date, "%Y-%m-%d").date()
                    filtered = [
                        a for a in self.scheduled_announcements
                        if datetime.fromisoformat(a["time"]).date() == filter_date
                    ]
                except ValueError:
                    await interaction.response.send_message("❌ Invalid date format. Use YYYY-MM-DD.", ephemeral=True)
                    return
            
            if not filtered:
                await interaction.response.send_message("📭 No scheduled announcements.", ephemeral=True)
            else:
                embed = discord.Embed(
                    title="📅 Scheduled Announcements",
                    color=self.get_character_color()
                )
                
                for i, announcement in enumerate(filtered):
                    time_str = datetime.fromisoformat(announcement["time"]).strftime("%Y-%m-%d %H:%M UTC")
                    recurring_text = " (Weekly)" if announcement.get("recurring") == "weekly" else ""
                    image_text = " 🖼️" if announcement.get("image_url") else ""
                    creator = announcement.get("created_by", "Unknown")
                    
                    embed.add_field(
                        name=f"#{i} - {time_str}{recurring_text}{image_text}",
                        value=f"**Message:** {announcement['message'][:100]}{'...' if len(announcement['message']) > 100 else ''}\n**Created by:** {creator}",
                        inline=False
                    )
                
                embed.set_footer(text="Use /edit_announcement or /cancel_announcement with the # ID")
                await interaction.response.send_message(embed=embed, ephemeral=True)
        
        # Birthday commands
        @self.tree.command(name="add_birthday", description="Add your birthday (MM-DD)")
        @app_commands.describe(birthday="Your birthday in MM-DD format")
        async def add_birthday(interaction: discord.Interaction, birthday: str):
            try:
                datetime.strptime(birthday, "%m-%d")
                user_id = str(interaction.user.id)
                username = interaction.user.display_name
                
                self.birthdays[user_id] = {
                    "username": username,
                    "birthday": birthday
                }
                self.save_birthdays()
                
                await interaction.response.send_message("🎉 Your birthday has been saved!", ephemeral=True)
                
            except ValueError:
                await interaction.response.send_message("❌ Invalid format. Use MM-DD.", ephemeral=True)
        
        @self.tree.command(name="next_birthdays", description="Show upcoming birthdays")
        async def next_birthdays(interaction: discord.Interaction):
            if not self.birthdays:
                await interaction.response.send_message("🎂 No birthdays registered yet!", ephemeral=True)
                return
            
            # Sort birthdays by date
            now = datetime.now()
            current_year = now.year
            
            upcoming = []
            for user_id, data in self.birthdays.items():
                try:
                    birthday_str = f"{current_year}-{data['birthday']}"
                    birthday_date = datetime.strptime(birthday_str, "%Y-%m-%d")
                    
                    # If birthday has passed this year, check next year
                    if birthday_date < now:
                        birthday_date = birthday_date.replace(year=current_year + 1)
                    
                    upcoming.append({
                        "username": data["username"],
                        "date": birthday_date,
                        "formatted": data["birthday"]
                    })
                except ValueError:
                    continue
            
            upcoming.sort(key=lambda x: x["date"])
            
            if upcoming:
                embed = discord.Embed(
                    title="🎂 Upcoming Birthdays",
                    color=self.get_character_color()
                )
                
                for i, birthday in enumerate(upcoming[:10]):  # Show next 10
                    embed.add_field(
                        name=birthday["username"],
                        value=birthday["formatted"],
                        inline=True
                    )
                
                await interaction.response.send_message(embed=embed)
            else:
                await interaction.response.send_message("🎂 No upcoming birthdays found!", ephemeral=True)
        
        @self.tree.command(name="welcome", description="Manually welcome a user to Wispwell")
        @app_commands.describe(user="The user to welcome")
        async def manual_welcome(interaction: discord.Interaction, user: discord.Member):
            try:
                welcome_messages = [
                    f"🌥️ Welcome to Wispwell, {user.mention}! Don't forget to check out the rules and say hi!",
                    f"✨ A gentle breeze brings {user.mention} to Wispwell! We hope you feel at home.",
                    f"🌸 {user.mention}, welcome! The clouds part for you today—enjoy your stay!",
                    f"🌟 The sanctuary doors open wide for {user.mention}! Welcome to our wonderful community!",
                    f"💫 A new friend joins us in Wispwell! {user.mention}, we're so glad you're here!",
                ]
                
                message = random.choice(welcome_messages)
                
                embed = discord.Embed(
                    description=message,
                    color=self.get_character_color()
                )
                embed.set_author(name="Sweet Peep", icon_url=self.user.avatar.url if self.user.avatar else None)
                embed.set_footer(text="✨ Welcome to the realm of Wispwell ✨")
                
                await interaction.response.send_message(embed=embed)
                
            except Exception as e:
                logger.error(f"Error in manual welcome command: {e}")
                await interaction.response.send_message("❌ Sorry, there was an error sending the welcome message.", ephemeral=True)
    
    async def process_overdue_announcements(self):
        """Process announcements that are overdue when bot comes online"""
        try:
            now = datetime.now(timezone.utc)
            overdue = []
            
            for announcement in self.scheduled_announcements[:]:
                announcement_time = datetime.fromisoformat(announcement["time"])
                
                if announcement_time <= now and not announcement.get("sent", False):
                    overdue.append(announcement)
            
            if overdue:
                logger.info(f"Found {len(overdue)} overdue announcements to process")
                
                for announcement in overdue:
                    success = await self.send_announcement(announcement, mark_as_overdue=True)
                    if not success:
                        # If send failed due to permissions, mark as sent to prevent infinite retries
                        announcement["sent"] = True
                        logger.warning(f"Marking failed announcement as sent to prevent retry loop: {announcement['message'][:50]}...")
                
                self.save_announcements()
            
        except Exception as e:
            logger.error(f"Error processing overdue announcements: {e}")
    
    async def send_announcement(self, announcement, mark_as_overdue=False):
        """Send a single announcement with improved error handling"""
        try:
            channel = self.get_channel(announcement["channel_id"])
            if not channel:
                logger.error(f"Channel {announcement['channel_id']} not found for announcement")
                return False
            
            # Check if bot has permissions to send messages
            if hasattr(channel, 'permissions_for') and hasattr(self, 'user'):
                permissions = channel.permissions_for(channel.guild.me if hasattr(channel, 'guild') else None)
                if permissions and not permissions.send_messages:
                    logger.error(f"Missing send_messages permission in channel {channel}")
                    return False
            
            embed = discord.Embed(
                title="📢 Scheduled Announcement" + (" (Overdue)" if mark_as_overdue else ""),
                description=announcement["message"],
                color=self.get_character_color()
            )
            embed.set_author(name="Sweet Peep")
            
            # Add image if available
            if announcement.get("image_url"):
                embed.set_image(url=announcement["image_url"])
            
            if mark_as_overdue:
                embed.set_footer(text="This announcement was delayed due to bot being offline")
            
            # Always tag the specified role with announcements
            role_mention = "<@&1316063157877342290>"
            await channel.send(content=role_mention, embed=embed)
            logger.info(f"Successfully sent announcement to channel {channel}")
            
            # Handle recurring announcements
            if announcement.get("recurring") == "weekly":
                # Schedule next week's occurrence
                next_time = datetime.fromisoformat(announcement["time"]) + timedelta(weeks=1)
                announcement["time"] = next_time.isoformat()
                announcement["sent"] = False
            else:
                # Remove one-time announcements
                if announcement in self.scheduled_announcements:
                    self.scheduled_announcements.remove(announcement)
            
            return True
            
        except discord.Forbidden as e:
            logger.error(f"Missing permissions to send announcement: {e}")
            return False
        except discord.HTTPException as e:
            logger.error(f"Discord HTTP error sending announcement: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending announcement: {e}")
            return False
    
    @tasks.loop(minutes=1)
    async def check_announcements(self):
        """Check for due announcements"""
        try:
            now = datetime.now(timezone.utc)
            due = []
            
            for announcement in self.scheduled_announcements[:]:  # Use slice to avoid modification during iteration
                announcement_time = datetime.fromisoformat(announcement["time"])
                
                if announcement_time <= now and not announcement.get("sent", False):
                    due.append(announcement)
            
            if due:
                for announcement in due:
                    success = await self.send_announcement(announcement)
                    if not success:
                        # If send failed due to permissions, mark as sent to prevent infinite retries
                        announcement["sent"] = True
                        logger.warning(f"Marking failed announcement as sent to prevent retry loop: {announcement['message'][:50]}...")
                
                self.save_announcements()
                
        except Exception as e:
            logger.error(f"Error checking announcements: {e}")
    
    @tasks.loop(hours=24)
    async def check_birthdays(self):
        """Check for birthdays today"""
        try:
            now = datetime.now(timezone.utc)
            today = now.strftime("%m-%d")
            
            birthday_users = [
                (uid, data["username"]) for uid, data in self.birthdays.items()
                if data["birthday"] == today
            ]
            
            if birthday_users:
                channel = self.get_channel(self.config.WELCOME_CHANNEL_ID)
                if channel:
                    mentions = ", ".join(f"<@{uid}> ({uname})" for uid, uname in birthday_users)
                    
                    embed = discord.Embed(
                        title="🎉 Birthday Celebration!",
                        description=(
                            f"🌟 A shimmer in the clouds! Today, we celebrate {mentions}'s birthday!\n\n"
                            "May your day be filled with sweets, sparkle, and sky-high hugs from the realm of Wispwell. 💫🎈"
                        ),
                        color=self.get_character_color()
                    )
                    embed.set_author(name="Sweet Peep")
                    
                    await channel.send(embed=embed)
                    
        except Exception as e:
            logger.error(f"Error checking birthdays: {e}")
    
    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Welcome new members"""
        try:
            welcome_messages = [
                f"🌥️ Welcome to Wispwell, {member.mention}! Don't forget to check out the rules and say hi!",
                f"✨ A gentle breeze brings {member.mention} to Wispwell! We hope you feel at home.",
                f"🌸 {member.mention}, welcome! The clouds part for you today—enjoy your stay!",
            ]
            
            channel = self.get_channel(self.config.WELCOME_CHANNEL_ID)
            if channel:
                message = random.choice(welcome_messages)
                
                embed = discord.Embed(
                    description=message,
                    color=self.get_character_color()
                )
                embed.set_author(name="Sweet Peep")
                
                await channel.send(embed=embed)
                
        except Exception as e:
            logger.error(f"Error in member join handler: {e}")
