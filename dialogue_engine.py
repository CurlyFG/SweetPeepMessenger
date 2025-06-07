"""
Dialogue Engine - Handles dialogue processing and scene participation for individual bots
"""

import asyncio
import logging
from typing import Dict, Optional, Any, List
import json
import os

from scene_manager import SceneManager
from utils.logger import setup_logger

logger = setup_logger(__name__)

class DialogueEngine:
    """Handles dialogue processing for individual character bots"""
    
    def __init__(self, bot_name: str, bot_instance=None):
        self.bot_name = bot_name
        self.bot_instance = bot_instance
        self.scene_manager = SceneManager()
        self.is_running = False
        self.check_task = None
        
    async def start_scene_monitoring(self):
        """Start monitoring for scene participation"""
        if self.is_running:
            logger.warning(f"Scene monitoring already running for {self.bot_name}")
            return
        
        self.is_running = True
        self.check_task = asyncio.create_task(self._scene_check_loop())
        logger.info(f"Started scene monitoring for {self.bot_name}")
    
    async def stop_scene_monitoring(self):
        """Stop scene monitoring"""
        self.is_running = False
        if self.check_task:
            self.check_task.cancel()
            try:
                await self.check_task
            except asyncio.CancelledError:
                pass
        logger.info(f"Stopped scene monitoring for {self.bot_name}")
    
    async def _scene_check_loop(self):
        """Main loop for checking scene participation"""
        while self.is_running:
            try:
                await self._check_and_participate()
                await asyncio.sleep(3)  # Check every 3 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in scene check loop for {self.bot_name}: {e}")
                await asyncio.sleep(5)  # Wait longer on error
    
    async def _check_and_participate(self):
        """Check if it's this bot's turn and participate if so"""
        try:
            state = await self.scene_manager.load_scene_state()
            
            # Debug logging
            logger.debug(f"[{self.bot_name}] Scene state: {state}")
            
            if not state or not state.get("scene_active"):
                return
            
            next_speaker = state.get("next_speaker")
            if next_speaker != self.bot_name:
                return
            
            # It's this bot's turn!
            await self._perform_dialogue_turn(state)
            
        except Exception as e:
            logger.error(f"Error checking scene participation for {self.bot_name}: {e}")
    
    async def _perform_dialogue_turn(self, state: Dict):
        """Perform this bot's dialogue turn"""
        try:
            scene_name = state.get("scene")
            current_node = state.get("current_node")
            
            if not scene_name or not current_node:
                logger.error(f"[{self.bot_name}] Invalid scene state: missing scene or node")
                return
            
            # Load scene data
            scene_data = await self.scene_manager.load_scene_data(scene_name)
            if not scene_data:
                logger.error(f"[{self.bot_name}] Could not load scene data for {scene_name}")
                return
            
            # Get current node data
            node_data = scene_data.get(current_node)
            if not node_data:
                logger.error(f"[{self.bot_name}] Node '{current_node}' not found in scene")
                return
            
            # Verify this bot is the speaker
            if node_data.get("speaker") != self.bot_name:
                logger.warning(f"[{self.bot_name}] Speaker mismatch in node '{current_node}'")
                return
            
            # Send the dialogue message
            await self._send_dialogue_message(node_data)
            
            # Wait for the specified duration
            wait_time = node_data.get("wait", 2)
            await asyncio.sleep(wait_time)
            
            # Advance the scene
            await self.scene_manager.advance_scene()
            
            logger.info(f"[{self.bot_name}] Completed dialogue turn for node '{current_node}'")
            
        except Exception as e:
            logger.error(f"Error performing dialogue turn for {self.bot_name}: {e}")
    
    async def _send_dialogue_message(self, node_data: Dict):
        """Send the dialogue message to Discord"""
        try:
            if not self.bot_instance:
                logger.error(f"[{self.bot_name}] No bot instance available for sending message")
                return
            
            # Get the channel (assumes WELCOME_CHANNEL_ID is set)
            from config import Config
            config = Config()
            
            channel = self.bot_instance.get_channel(config.WELCOME_CHANNEL_ID)
            if not channel:
                logger.error(f"[{self.bot_name}] Could not find channel {config.WELCOME_CHANNEL_ID}")
                return
            
            # Format the message
            text = node_data.get("text", "")
            message = f"**{self.bot_name}:** {text}"
            
            # Send the message
            await channel.send(message)
            
            logger.info(f"[{self.bot_name}] Sent dialogue: {text[:50]}...")
            
        except Exception as e:
            logger.error(f"Error sending dialogue message for {self.bot_name}: {e}")
    
    async def start_scene_command(self, scene_name: str = "scene1_orlin.json") -> Dict:
        """Handle scene start command"""
        try:
            success = await self.scene_manager.start_scene(scene_name)
            
            if success:
                return {
                    "success": True,
                    "message": f"🎭 Scene '{scene_name}' started! Let the dialogue begin!"
                }
            else:
                return {
                    "success": False,
                    "message": f"❌ Failed to start scene '{scene_name}'. Check if the scene file exists and is valid."
                }
                
        except Exception as e:
            logger.error(f"Error starting scene {scene_name}: {e}")
            return {
                "success": False,
                "message": f"❌ Error starting scene: {str(e)}"
            }
    
    async def stop_scene_command(self) -> Dict:
        """Handle scene stop command"""
        try:
            success = await self.scene_manager.stop_scene()
            
            if success:
                return {
                    "success": True,
                    "message": "🛑 Scene stopped successfully."
                }
            else:
                return {
                    "success": False,
                    "message": "❌ Failed to stop scene."
                }
                
        except Exception as e:
            logger.error(f"Error stopping scene: {e}")
            return {
                "success": False,
                "message": f"❌ Error stopping scene: {str(e)}"
            }
    
    async def get_scene_status(self) -> Dict:
        """Get current scene status"""
        try:
            return await self.scene_manager.get_scene_status()
        except Exception as e:
            logger.error(f"Error getting scene status: {e}")
            return {"active": False, "error": str(e)}
    
    async def list_scenes(self) -> List[str]:
        """List available scenes"""
        try:
            return await self.scene_manager.list_available_scenes()
        except Exception as e:
            logger.error(f"Error listing scenes: {e}")
            return []
