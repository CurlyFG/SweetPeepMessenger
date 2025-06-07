"""
Scene Manager - Centralized coordination for multi-bot dialogue scenes
"""

import os
import json
import asyncio
import logging
from typing import Dict, Optional, List, Any
from datetime import datetime
import threading

from utils.logger import setup_logger
from config import Config

logger = setup_logger(__name__)

class SceneManager:
    """Manages scene coordination across multiple Discord bots"""
    
    def __init__(self):
        self.config = Config()
        self.lock = asyncio.Lock()
        self.file_lock = threading.Lock()
        
        # Ensure required directories exist
        self.ensure_directories()
    
    def ensure_directories(self):
        """Ensure all required directories exist"""
        directories = [
            self.config.SHARED_DIR,
            self.config.DIALOGUE_DIR,
            self.config.DATA_DIR
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            logger.debug(f"Ensured directory exists: {directory}")
    
    @property
    def scene_state_file(self) -> str:
        """Path to scene state file"""
        return os.path.join(self.config.SHARED_DIR, "scene_state.json")
    
    async def load_scene_state(self) -> Dict:
        """Load current scene state from file"""
        try:
            if not os.path.exists(self.scene_state_file):
                logger.debug("Scene state file not found, returning empty state")
                return {}
            
            with self.file_lock:
                with open(self.scene_state_file, "r", encoding="utf-8") as f:
                    state = json.load(f)
            
            logger.debug(f"Loaded scene state: {state}")
            return state
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in scene state file: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error loading scene state: {e}")
            return {}
    
    async def save_scene_state(self, state: Dict):
        """Save scene state to file"""
        try:
            async with self.lock:
                with self.file_lock:
                    with open(self.scene_state_file, "w", encoding="utf-8") as f:
                        json.dump(state, f, indent=2)
            
            logger.debug(f"Saved scene state: {state}")
            
        except Exception as e:
            logger.error(f"Error saving scene state: {e}")
            raise
    
    async def load_scene_data(self, scene_name: str) -> Optional[Dict]:
        """Load scene dialogue data from file"""
        scene_file = os.path.join(self.config.DIALOGUE_DIR, scene_name)
        
        if not os.path.exists(scene_file):
            logger.error(f"Scene file not found: {scene_file}")
            return None
        
        try:
            with open(scene_file, "r", encoding="utf-8") as f:
                scene_data = json.load(f)
            
            logger.debug(f"Loaded scene data for {scene_name}")
            return scene_data
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in scene file {scene_name}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error loading scene file {scene_name}: {e}")
            return None
    
    async def start_scene(self, scene_name: str, starting_node: str = "start") -> bool:
        """Start a new dialogue scene"""
        try:
            # Validate scene file exists
            scene_data = await self.load_scene_data(scene_name)
            if not scene_data:
                logger.error(f"Cannot start scene: {scene_name} not found")
                return False
            
            # Validate starting node exists
            if starting_node not in scene_data:
                logger.error(f"Starting node '{starting_node}' not found in scene {scene_name}")
                return False
            
            # Determine first speaker
            first_node = scene_data[starting_node]
            first_speaker = first_node.get("speaker")
            
            if not first_speaker:
                logger.error(f"No speaker defined for starting node in {scene_name}")
                return False
            
            # Create initial scene state
            state = {
                "scene": scene_name,
                "current_node": starting_node,
                "next_speaker": first_speaker,
                "waiting_for_choice": False,
                "started_at": datetime.utcnow().isoformat(),
                "scene_active": True
            }
            
            await self.save_scene_state(state)
            
            logger.info(f"Started scene '{scene_name}' with first speaker '{first_speaker}'")
            return True
            
        except Exception as e:
            logger.error(f"Error starting scene {scene_name}: {e}")
            return False
    
    async def advance_scene(self) -> Optional[Dict]:
        """Advance scene to next node and determine next speaker"""
        try:
            state = await self.load_scene_state()
            if not state or not state.get("scene_active"):
                logger.debug("No active scene to advance")
                return None
            
            scene_name = state.get("scene")
            current_node = state.get("current_node")
            
            if not scene_name or not current_node:
                logger.error("Invalid scene state: missing scene or current_node")
                return None
            
            # Load scene data
            scene_data = await self.load_scene_data(scene_name)
            if not scene_data:
                logger.error(f"Cannot advance scene: {scene_name} data not found")
                return None
            
            # Get current node data
            node_data = scene_data.get(current_node)
            if not node_data:
                logger.error(f"Current node '{current_node}' not found in scene data")
                return None
            
            # Determine next node
            next_info = node_data.get("next")
            
            if next_info is None:
                # Scene has ended
                state["scene_active"] = False
                state["current_node"] = None
                state["next_speaker"] = None
                state["ended_at"] = datetime.utcnow().isoformat()
                await self.save_scene_state(state)
                
                logger.info(f"Scene '{scene_name}' has ended")
                return None
            
            # Handle different next node formats
            if isinstance(next_info, str):
                next_node = next_info
            elif isinstance(next_info, dict):
                # Handle choice-based advancement
                if "continue" in next_info:
                    next_node = next_info["continue"]
                else:
                    # For now, just take the first available choice
                    next_node = list(next_info.values())[0] if next_info else None
            else:
                logger.error(f"Invalid next node format in {current_node}: {next_info}")
                return None
            
            if not next_node or next_node not in scene_data:
                logger.error(f"Next node '{next_node}' not found in scene data")
                return None
            
            # Get next node data to determine speaker
            next_node_data = scene_data[next_node]
            next_speaker = next_node_data.get("speaker")
            
            if not next_speaker:
                logger.error(f"No speaker defined for next node '{next_node}'")
                return None
            
            # Update scene state
            state["current_node"] = next_node
            state["next_speaker"] = next_speaker
            state["waiting_for_choice"] = False
            
            await self.save_scene_state(state)
            
            logger.info(f"Advanced scene to node '{next_node}', next speaker: '{next_speaker}'")
            return next_node_data
            
        except Exception as e:
            logger.error(f"Error advancing scene: {e}")
            return None
    
    async def stop_scene(self) -> bool:
        """Stop the current scene"""
        try:
            state = await self.load_scene_state()
            if not state:
                logger.debug("No scene state to stop")
                return True
            
            state["scene_active"] = False
            state["current_node"] = None
            state["next_speaker"] = None
            state["stopped_at"] = datetime.utcnow().isoformat()
            
            await self.save_scene_state(state)
            
            logger.info("Scene stopped")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping scene: {e}")
            return False
    
    async def get_scene_status(self) -> Dict:
        """Get current scene status"""
        try:
            state = await self.load_scene_state()
            if not state:
                return {"active": False}
            
            return {
                "active": state.get("scene_active", False),
                "scene": state.get("scene"),
                "current_node": state.get("current_node"),
                "next_speaker": state.get("next_speaker"),
                "waiting_for_choice": state.get("waiting_for_choice", False),
                "started_at": state.get("started_at"),
                "ended_at": state.get("ended_at"),
                "stopped_at": state.get("stopped_at")
            }
            
        except Exception as e:
            logger.error(f"Error getting scene status: {e}")
            return {"active": False, "error": str(e)}
    
    async def list_available_scenes(self) -> List[str]:
        """List all available scene files"""
        try:
            if not os.path.exists(self.config.DIALOGUE_DIR):
                return []
            
            scene_files = []
            for filename in os.listdir(self.config.DIALOGUE_DIR):
                if filename.endswith('.json'):
                    scene_files.append(filename)
            
            return sorted(scene_files)
            
        except Exception as e:
            logger.error(f"Error listing scenes: {e}")
            return []
    
    async def validate_scene(self, scene_name: str) -> Dict:
        """Validate a scene file structure"""
        validation_result = {
            "valid": False,
            "errors": [],
            "warnings": [],
            "nodes": 0,
            "speakers": set()
        }
        
        try:
            scene_data = await self.load_scene_data(scene_name)
            if not scene_data:
                validation_result["errors"].append("Scene file not found or invalid JSON")
                return validation_result
            
            validation_result["nodes"] = len(scene_data)
            
            # Check for start node
            if "start" not in scene_data:
                validation_result["errors"].append("Missing 'start' node")
            
            # Validate each node
            for node_name, node_data in scene_data.items():
                if not isinstance(node_data, dict):
                    validation_result["errors"].append(f"Node '{node_name}' is not a dictionary")
                    continue
                
                # Check required fields
                if "speaker" not in node_data:
                    validation_result["errors"].append(f"Node '{node_name}' missing 'speaker' field")
                else:
                    validation_result["speakers"].add(node_data["speaker"])
                
                if "text" not in node_data:
                    validation_result["errors"].append(f"Node '{node_name}' missing 'text' field")
                
                # Check next node references
                next_info = node_data.get("next")
                if next_info is not None:
                    if isinstance(next_info, str):
                        if next_info not in scene_data:
                            validation_result["errors"].append(f"Node '{node_name}' references non-existent next node '{next_info}'")
                    elif isinstance(next_info, dict):
                        for choice, target in next_info.items():
                            if target not in scene_data:
                                validation_result["errors"].append(f"Node '{node_name}' choice '{choice}' references non-existent node '{target}'")
            
            validation_result["valid"] = len(validation_result["errors"]) == 0
            validation_result["speakers"] = list(validation_result["speakers"])
            
        except Exception as e:
            validation_result["errors"].append(f"Validation error: {str(e)}")
        
        return validation_result
