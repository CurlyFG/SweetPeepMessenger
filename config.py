"""
Configuration Management for SweetPeep Multi-Bot Discord Dialogue System
"""

import os
from typing import Optional
import logging

class Config:
    """Centralized configuration for the SweetPeep system"""
    
    def __init__(self):
        # Load environment variables
        self.load_env_file()
        
        # Discord Configuration
        self.DISCORD_TOKEN_SWEET_PEEP = os.getenv('DISCORD_TOKEN_SWEET_PEEP', '')
        self.DISCORD_TOKEN_ORLIN = os.getenv('DISCORD_TOKEN_ORLIN', '')
        self.DISCORD_TOKEN_CLOUDBELLE = os.getenv('DISCORD_TOKEN_CLOUDBELLE', '')
        self.DISCORD_TOKEN_ELROI = os.getenv('DISCORD_TOKEN_ELROI', '')
        
        # Server Configuration
        self.WELCOME_CHANNEL_ID = int(os.getenv('WELCOME_CHANNEL_ID', '1286430360544219260'))
        self.GUILD_ID = os.getenv('GUILD_ID', '')
        
        # Port Configuration (Render uses PORT env variable)
        self.WEB_PORT = int(os.getenv('PORT', os.getenv('WEB_PORT', '5000')))
        self.BOT_PORT = int(os.getenv('BOT_PORT', '8000'))
        
        # Directory Paths
        self.BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        self.SHARED_DIR = os.path.join(self.BASE_DIR, 'shared')
        self.DIALOGUE_DIR = os.path.join(self.SHARED_DIR, 'dialogue')
        self.DATA_DIR = os.path.join(self.BASE_DIR, 'data')
        self.WEB_TEMPLATES_DIR = os.path.join(self.BASE_DIR, 'web_dashboard', 'templates')
        self.WEB_STATIC_DIR = os.path.join(self.BASE_DIR, 'web_dashboard', 'static')
        
        # Logging Configuration
        self.DEBUG_MODE = os.getenv('DEBUG_MODE', 'True').lower() == 'true'
        self.LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
        
        # Scene Configuration
        self.SCENE_CHECK_INTERVAL = int(os.getenv('SCENE_CHECK_INTERVAL', '3'))  # seconds
        self.DEFAULT_SCENE_WAIT = int(os.getenv('DEFAULT_SCENE_WAIT', '2'))  # seconds
        
        # Bot Configuration
        self.BOT_COMMAND_PREFIX = os.getenv('BOT_COMMAND_PREFIX', '!')
        self.BOT_DESCRIPTION = "SweetPeep Multi-Bot Discord Dialogue System"
        
        # File Configuration
        self.SCENE_STATE_FILE = 'scene_state.json'
        self.ANNOUNCEMENTS_FILE = 'announcements.json'
        self.BIRTHDAYS_FILE = 'birthdays.json'
        
        # Validation
        self.validate_config()
    
    def load_env_file(self):
        """Load environment variables from .env file if it exists"""
        env_file = os.path.join(os.path.dirname(__file__), '.env')
        if os.path.exists(env_file):
            try:
                with open(env_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            if '=' in line:
                                key, value = line.split('=', 1)
                                # Only set if not already in environment
                                if key not in os.environ:
                                    os.environ[key] = value
            except Exception as e:
                print(f"Warning: Could not load .env file: {e}")
    
    def validate_config(self):
        """Validate critical configuration values"""
        errors = []
        warnings = []
        
        # Check for at least one bot token
        bot_tokens = [
            self.DISCORD_TOKEN_SWEET_PEEP,
            self.DISCORD_TOKEN_ORLIN,
            self.DISCORD_TOKEN_CLOUDBELLE,
            self.DISCORD_TOKEN_ELROI
        ]
        
        valid_tokens = [token for token in bot_tokens if token and not token.startswith('your_')]
        
        if not valid_tokens:
            errors.append("No valid Discord bot tokens found. At least one bot token is required.")
        
        # Check channel ID
        if self.WELCOME_CHANNEL_ID <= 0:
            warnings.append("Invalid WELCOME_CHANNEL_ID. Some features may not work correctly.")
        
        # Check ports
        if not (1024 <= self.WEB_PORT <= 65535):
            warnings.append(f"Web port {self.WEB_PORT} is outside recommended range (1024-65535)")
        
        if not (1024 <= self.BOT_PORT <= 65535):
            warnings.append(f"Bot port {self.BOT_PORT} is outside recommended range (1024-65535)")
        
        # Log validation results
        if errors:
            for error in errors:
                print(f"CONFIG ERROR: {error}")
        
        if warnings:
            for warning in warnings:
                print(f"CONFIG WARNING: {warning}")
        
        # Raise exception for critical errors
        if errors:
            raise ValueError(f"Configuration validation failed: {'; '.join(errors)}")
    
    def get_bot_tokens(self) -> dict:
        """Get all bot tokens as a dictionary"""
        return {
            'Sweet Peep': self.DISCORD_TOKEN_SWEET_PEEP,
            'Orlin': self.DISCORD_TOKEN_ORLIN,
            'CloudBelle': self.DISCORD_TOKEN_CLOUDBELLE,
            'El Roi': self.DISCORD_TOKEN_ELROI
        }
    
    def get_valid_bot_tokens(self) -> dict:
        """Get only valid (non-empty, non-placeholder) bot tokens"""
        all_tokens = self.get_bot_tokens()
        return {
            name: token for name, token in all_tokens.items()
            if token and not token.startswith('your_') and len(token) > 10
        }
    
    def is_debug_mode(self) -> bool:
        """Check if debug mode is enabled"""
        return self.DEBUG_MODE
    
    def get_log_level(self) -> int:
        """Get logging level as integer"""
        level_map = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        return level_map.get(self.LOG_LEVEL, logging.INFO)
    
    def ensure_directories(self):
        """Ensure all required directories exist"""
        directories = [
            self.SHARED_DIR,
            self.DIALOGUE_DIR,
            self.DATA_DIR
        ]
        
        for directory in directories:
            try:
                os.makedirs(directory, exist_ok=True)
            except Exception as e:
                print(f"Warning: Could not create directory {directory}: {e}")
    
    def get_scene_file_path(self, scene_name: str) -> str:
        """Get full path to a scene file"""
        return os.path.join(self.DIALOGUE_DIR, scene_name)
    
    def get_data_file_path(self, filename: str) -> str:
        """Get full path to a data file"""
        return os.path.join(self.DATA_DIR, filename)
    
    def get_shared_file_path(self, filename: str) -> str:
        """Get full path to a shared file"""
        return os.path.join(self.SHARED_DIR, filename)
    
    def __str__(self) -> str:
        """String representation of config (without sensitive data)"""
        return f"""SweetPeep Configuration:
  Web Port: {self.WEB_PORT}
  Bot Port: {self.BOT_PORT}
  Welcome Channel: {self.WELCOME_CHANNEL_ID}
  Debug Mode: {self.DEBUG_MODE}
  Log Level: {self.LOG_LEVEL}
  Valid Bot Tokens: {len(self.get_valid_bot_tokens())}
  Base Directory: {self.BASE_DIR}
  Shared Directory: {self.SHARED_DIR}
  Dialogue Directory: {self.DIALOGUE_DIR}
  Data Directory: {self.DATA_DIR}"""

# Global config instance
config = Config()

# Ensure directories exist on import
config.ensure_directories()
