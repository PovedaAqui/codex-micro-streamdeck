#!/usr/bin/env python
"""
Codex Micro Stream Deck Bridge — MVP for 6-key Stream Deck

Replicates the Codex Micro experience on a 6-key Stream Deck with 2 pages:
  Page 1: Agent Status | Accept | Reject | New Chat | Reasoning (toggle) | → Page 2
  Page 2: PR Review | Debug | Refactor | Test/Deploy | Stop All | → Page 1

Requires:
  - Stream Deck hardware connected via USB
  - Python 3.8+ (3.11+ recommended)
  - System dependencies: see README.md (apt-get on Linux, pip on Windows)
  - Python packages: pip install streamdeck pillow pyyaml

Usage:
  python main.py                    # Run with defaults
  python main.py --config config.yaml  # Custom config
  python main.py --simulate         # Test without hardware
"""

import sys
import os
import time
import threading
import argparse
from pathlib import Path
from typing import Optional, List

import yaml
from PIL import Image, ImageDraw

# Try to import Stream Deck (optional for simulation)
try:
    from StreamDeck.DeviceManager import DeviceManager
    from StreamDeck.Image import ImageDraw as SDImageDraw
    from StreamDeck.Util import create_picture_mask
    HAS_STREAMDECK = True
except ImportError:
    HAS_STREAMDECK = False

# Constants
SCRIPT_DIR = Path(__file__).parent
CONFIG_PATH = SCRIPT_DIR / "config.yaml"
ICONS_DIR = SCRIPT_DIR / "icons"

# Agent states (matching Codex Micro)
AGENT_STATES = ["idle", "thinking", "running", "waiting", "done", "error"]
AGENT_COLORS = {
    "idle": "#808080",
    "thinking": "#FFD700",
    "running": "#32CD32",
    "waiting": "#1E90FF",
    "done": "#9370DB",
    "error": "#FF4500",
}

# Key mapping for 6-key Stream Deck
# Each key has different behavior on page 1 vs page 2
KEY_MAP = {
    0: {
        "page1": {"name": "Agent Status", "type": "agent_status"},
        "page2": {"name": "PR Review", "type": "workflow", "action": "pr_review"},
    },
    1: {
        "page1": {"name": "Accept", "type": "command", "action": "accept"},
        "page2": {"name": "Debug", "type": "workflow", "action": "debug"},
    },
    2: {
        "page1": {"name": "Reject", "type": "command", "action": "reject"},
        "page2": {"name": "Refactor", "type": "workflow", "action": "refactor"},
    },
    3: {
        "page1": {"name": "New Chat", "type": "command", "action": "new_chat"},
        "page2": {"name": "Test/Deploy", "type": "workflow", "action": "test_deploy"},
    },
    4: {
        "page1": {"name": "Reasoning", "type": "reasoning", "action": "toggle_reasoning"},
        "page2": {"name": "Stop All", "type": "system", "action": "stop_all"},
    },
    5: {
        "page1": {"name": "→ Page 2", "type": "page_switch", "action": "next_page"},
        "page2": {"name": "← Page 1", "type": "page_switch", "action": "prev_page"},
    },
}


class AgentMonitor:
    """Monitors agent state and provides current state to the bridge."""

    def __init__(self):
        self.current_state = "idle"
        self._lock = threading.Lock()
        self._conversation_history: List[str] = []
        self._last_response: Optional[str] = None

    def set_state(self, state: str):
        if state in AGENT_STATES:
            with self._lock:
                self.current_state = state

    def get_state(self) -> str:
        with self._lock:
            return self.current_state

    def add_message(self, message: str, is_response: bool = False):
        """Add a message to conversation history and infer state."""
        with self._lock:
            self._conversation_history.append(message)
            if is_response:
                self._last_response = message
                self.current_state = "done"
            else:
                self.current_state = "thinking"

    def new_chat(self):
        """Reset conversation and state."""
        with self._lock:
            self._conversation_history.clear()
            self._last_response = None
            self.current_state = "idle"

    def infer_state_from_conversation(self) -> str:
        """Infer agent state from conversation context."""
        with self._lock:
            if not self._conversation_history:
                return "idle"
            if self._last_response is not None:
                return "done"
            # Last message was a user message without response yet
            if self._conversation_history[-1] and not self._conversation_history[-1].startswith("__RESPONSE__"):
                return "thinking"
            return "idle"


class ReasoningLevel:
    """Manages reasoning level toggle (Low → Medium → High → Low)."""

    LEVELS = [
        {"name": "Low", "value": "none", "color": "#90EE90"},
        {"name": "Medium", "value": "medium", "color": "#FFA500"},
        {"name": "High", "value": "high", "color": "#FF6347"},
    ]

    def __init__(self):
        self.current_index = 0

    def get_current(self) -> dict:
        return self.LEVELS[self.current_index]

    def toggle(self) -> dict:
        self.current_index = (self.current_index + 1) % len(self.LEVELS)
        return self.get_current()


class StreamDeckBridge:
    """Main bridge connecting Stream Deck to Codex Micro functionality."""

    def __init__(self, config_path: Path = CONFIG_PATH, simulate: bool = False):
        self.config = self._load_config(config_path)
        self.deck = None
        self.current_page = 1
        self.agent_monitor = AgentMonitor()
        self.reasoning = ReasoningLevel()
        self._running = True
        self.simulate = simulate

        # Key mapping: physical key index → logical key config
        self.key_map = KEY_MAP

    def _load_config(self, config_path: Path) -> dict:
        """Load configuration from YAML file."""
        if config_path.exists():
            with open(config_path, "r") as f:
                return yaml.safe_load(f) or {}
        return {}

    def _get_icon_path(self, key_type: str, state: str = None) -> Optional[Path]:
        """Get icon path for a key based on type and state."""
        if key_type == "agent_status" and state:
            icon_name = f"{state}.png"
        else:
            icon_name = f"{key_type}.png"

        icon_path = ICONS_DIR / icon_name
        if icon_path.exists():
            return icon_path
        return None

    def _create_key_image(self, color: str, icon_path: Optional[Path] = None) -> Image.Image:
        """Create a key image with background color and optional icon."""
        img = Image.new("RGB", (280, 280), color)

        if icon_path and icon_path.exists():
            try:
                icon = Image.open(icon_path).convert("RGBA")
                icon = icon.resize((200, 200))
                mask = icon.split()[3] if len(icon.split()) > 3 else None
                img.paste(icon, (40, 40), mask)
            except Exception as e:
                print(f"Warning: Could not load icon {icon_path}: {e}")

        return img

    def _update_key(self, key_index: int, color: str, icon_path: Optional[Path] = None):
        """Update a single key's color and/or icon."""
        if self.simulate:
            print(f"[SIM] Key {key_index}: color={color}, icon={icon_path}")
            return

        if not self.deck:
            return

        try:
            img = self._create_key_image(color, icon_path)
            self.deck.set_key_image(key_index, img)
            # set_key_image updates the display automatically; no show() needed
        except Exception as e:
            print(f"Error updating key {key_index}: {e}")

    def _get_key_config(self, key_index: int) -> Optional[dict]:
        """Get the current key config based on the current page."""
        if key_index not in self.key_map:
            return None
        page_key = f"page{self.current_page}"
        return self.key_map[key_index].get(page_key)

    def _render_page(self, page: int):
        """Render all keys for a given page."""
        self.current_page = page

        if self.simulate:
            print(f"\n[SIM] Rendering Page {page}:")
            for key_index in range(6):
                key_config = self._get_key_config(key_index)
                if not key_config:
                    continue

                key_type = key_config.get("type")
                key_name = key_config.get("name", f"Key {key_index}")

                if key_type == "agent_status":
                    state = self.agent_monitor.get_state()
                    color = AGENT_COLORS.get(state, "#808080")
                    icon_path = self._get_icon_path("agent_status", state)
                    print(f"  Key {key_index}: {key_name} → {state.upper()} ({color})")
                    self._update_key(key_index, color, icon_path)

                elif key_type == "command":
                    action = key_config.get("action")
                    if action == "accept":
                        color = "#32CD32"
                    else:
                        color = "#FF4500"
                    print(f"  Key {key_index}: {key_name} → {color}")
                    self._update_key(key_index, color)

                elif key_type == "reasoning":
                    level = self.reasoning.get_current()
                    print(f"  Key {key_index}: {key_name} → {level['name']} ({level['color']})")
                    self._update_key(key_index, level["color"])

                elif key_type == "page_switch":
                    color = "#808080"
                    print(f"  Key {key_index}: {key_name}")
                    self._update_key(key_index, color)

                elif key_type == "workflow":
                    print(f"  Key {key_index}: {key_name} → [workflow]")
                    self._update_key(key_index, "#4169E1")

                elif key_type == "system":
                    print(f"  Key {key_index}: {key_name} → [system]")
                    self._update_key(key_index, "#DC143C")

            return

        if not self.deck:
            return

        for key_index in range(6):
            key_config = self._get_key_config(key_index)
            if not key_config:
                continue

            key_type = key_config.get("type")

            if key_type == "agent_status":
                state = self.agent_monitor.get_state()
                color = AGENT_COLORS.get(state, "#808080")
                icon_path = self._get_icon_path("agent_status", state)
                self._update_key(key_index, color, icon_path)

            elif key_type == "command":
                action = key_config.get("action")
                if action == "accept":
                    color = "#32CD32"
                else:
                    color = "#FF4500"
                self._update_key(key_index, color)

            elif key_type == "reasoning":
                level = self.reasoning.get_current()
                self._update_key(key_index, level["color"])

            elif key_type == "page_switch":
                self._update_key(key_index, "#808080")

            elif key_type == "workflow":
                self._update_key(key_index, "#4169E1")

            elif key_type == "system":
                self._update_key(key_index, "#DC143C")

    def _start_agent_monitoring(self):
        """Start background thread for agent state monitoring."""
        def monitor_loop():
            while self._running:
                state = self.agent_monitor.infer_state_from_conversation()
                self.agent_monitor.set_state(state)
                self._render_page(self.current_page)
                time.sleep(self.config.get("polling_interval", 3))

        thread = threading.Thread(target=monitor_loop, daemon=True)
        thread.start()

    def _handle_key_press(self, key_index: int, pressed: bool):
        """Handle key press events."""
        if key_index not in self.key_map:
            return

        if not pressed:
            return

        key_config = self._get_key_config(key_index)
        if not key_config:
            return

        action = key_config.get("action")
        key_type = key_config.get("type")

        if action == "next_page":
            self.current_page = 2
            self._render_page(2)

        elif action == "prev_page":
            self.current_page = 1
            self._render_page(1)

        elif action == "toggle_reasoning":
            level = self.reasoning.toggle()
            self._update_key(key_index, level["color"])

        elif action == "accept":
            print("Action: Accept response")
            self.agent_monitor.add_message("__ACCEPTED__", is_response=True)
            self._update_key(key_index, "#00FF00")
            self._render_page(self.current_page)

        elif action == "reject":
            print("Action: Reject response")
            self.agent_monitor.add_message("__REJECTED__", is_response=True)
            self._update_key(key_index, "#FF0000")
            self._render_page(self.current_page)

        elif action == "new_chat":
            print("Action: New chat")
            self.agent_monitor.new_chat()
            self._render_page(1)

        elif action in ("pr_review", "debug", "refactor", "test_deploy"):
            print(f"Action: Workflow '{action}'")
            # TODO: Implement workflow via OpenAI API
            self._update_key(key_index, "#00FF00")
            self._render_page(self.current_page)

        elif action == "stop_all":
            print("Action: Stop all")
            self.agent_monitor.new_chat()
            self._update_key(key_index, "#FF0000")
            self._render_page(self.current_page)

    def _connect_streamdeck(self):
        """Connect to the Stream Deck hardware."""
        if not HAS_STREAMDECK:
            print("Error: Stream Deck library not installed.")
            print("Install with: pip install streamdeck")
            return False

        try:
            deck = DeviceManager().enumerate()
            if not deck:
                print("No Stream Deck found. Connect one via USB and try again.")
                return False

            self.deck = deck[0]
            self.deck.open()
            self.deck.reset()
            print(f"Connected to Stream Deck ({self.deck.key_count()} keys)")
            return True

        except Exception as e:
            print(f"Error connecting to Stream Deck: {e}")
            return False

    def run(self):
        """Start the Stream Deck bridge."""
        print("Starting Codex Micro Stream Deck Bridge...")

        if self.simulate:
            print("Running in SIMULATION mode (no hardware detected)")
            self._render_page(1)

            # Simulate key presses for testing
            print("\nSimulating key presses...")
            for i in range(3):
                print(f"\n--- Iteration {i+1} ---")
                self.agent_monitor.set_state("thinking")
                self._render_page(1)
                time.sleep(2)

                self.agent_monitor.set_state("running")
                self._render_page(1)
                time.sleep(2)

                self.agent_monitor.set_state("done")
                self._render_page(1)
                time.sleep(2)

                self.agent_monitor.set_state("idle")
                self._render_page(1)
                time.sleep(2)

            print("\nSimulation complete.")
            return

        try:
            # Connect to Stream Deck
            if not self._connect_streamdeck():
                print("\nNo hardware detected. Try --simulate to test without hardware.")
                return

            # Start agent monitoring
            self._start_agent_monitoring()

            # Render initial page
            self._render_page(1)

            # Main event loop
            while self._running:
                try:
                    events = self.deck.read_events()
                    for event in events:
                        self._handle_key_press(event.key, event.state)
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    print(f"Error reading events: {e}")
                    time.sleep(1)

        except Exception as e:
            print(f"Error connecting to Stream Deck: {e}")
            sys.exit(1)
        finally:
            if self.deck:
                self.deck.close()
            self._running = False
            print("Bridge stopped.")


def main():
    """Entry point."""
    parser = argparse.ArgumentParser(description="Codex Micro Stream Deck Bridge")
    parser.add_argument("--config", type=Path, default=CONFIG_PATH, help="Path to config file")
    parser.add_argument("--simulate", action="store_true", help="Run in simulation mode (no hardware)")
    args = parser.parse_args()

    bridge = StreamDeckBridge(args.config, args.simulate)

    bridge.run()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nBridge stopped.")
