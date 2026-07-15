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
from typing import Optional

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
KEY_MAP = {
    0: {"name": "Agent Status", "page": 1, "type": "agent_status"},
    1: {"name": "Accept", "page": 1, "type": "command", "action": "accept"},
    2: {"name": "Reject", "page": 1, "type": "command", "action": "reject"},
    3: {"name": "New Chat", "page": 1, "type": "command", "action": "new_chat"},
    4: {"name": "Reasoning", "page": 1, "type": "reasoning", "action": "toggle_reasoning"},
    5: {"name": "→ Page 2", "page": 1, "type": "page_switch", "action": "next_page"},
}


class AgentMonitor:
    """Monitors agent state and provides current state to the bridge."""

    def __init__(self):
        self.current_state = "idle"
        self._lock = threading.Lock()

    def set_state(self, state: str):
        if state in AGENT_STATES:
            with self._lock:
                self.current_state = state

    def get_state(self) -> str:
        with self._lock:
            return self.current_state

    def infer_state_from_conversation(self, last_message: Optional[str] = None, has_response: bool = False) -> str:
        """Infer agent state from conversation context (MVP approach)."""
        if last_message and not has_response:
            return "thinking"
        elif has_response:
            return "done"
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
            self.deck.show()
        except Exception as e:
            print(f"Error updating key {key_index}: {e}")

    def _render_page(self, page: int):
        """Render all keys for a given page."""
        if self.simulate:
            print(f"\n[SIM] Rendering Page {page}:")
            for key_index, key_config in self.key_map.items():
                if key_config["page"] != page:
                    continue

                if key_config["type"] == "agent_status":
                    state = self.agent_monitor.get_state()
                    color = AGENT_COLORS.get(state, "#808080")
                    icon_path = self._get_icon_path("agent_status", state)
                    print(f"  Key {key_index}: {key_config['name']} → {state.upper()} ({color})")
                    self._update_key(key_index, color, icon_path)

                elif key_config["type"] == "command":
                    color = "#32CD32" if key_config["action"] == "accept" else "#FF4500"
                    print(f"  Key {key_index}: {key_config['name']} → {color}")
                    self._update_key(key_index, color)

                elif key_config["type"] == "reasoning":
                    level = self.reasoning.get_current()
                    print(f"  Key {key_index}: {key_config['name']} → {level['name']} ({level['color']})")
                    self._update_key(key_index, level["color"])

                elif key_config["type"] == "page_switch":
                    print(f"  Key {key_index}: {key_config['name']}")
                    self._update_key(key_index, "#808080")
            return

        if not self.deck:
            return

        for key_index, key_config in self.key_map.items():
            if key_config["page"] != page:
                continue

            if key_config["type"] == "agent_status":
                state = self.agent_monitor.get_state()
                color = AGENT_COLORS.get(state, "#808080")
                icon_path = self._get_icon_path("agent_status", state)
                self._update_key(key_index, color, icon_path)

            elif key_config["type"] == "command":
                color = "#32CD32" if key_config["action"] == "accept" else "#FF4500"
                self._update_key(key_index, color)

            elif key_config["type"] == "reasoning":
                level = self.reasoning.get_current()
                self._update_key(key_index, level["color"])

            elif key_config["type"] == "page_switch":
                self._update_key(key_index, "#808080")

    def _start_agent_monitoring(self):
        """Start background thread for agent state monitoring."""
        def monitor_loop():
            while self._running:
                # MVP: Simulate agent state changes
                # In production, this would poll the OpenAI API or ChatGPT Desktop App
                state = self.agent_monitor.infer_state_from_conversation()
                self.agent_monitor.set_state(state)
                time.sleep(self.config.get("polling_interval", 3))

        thread = threading.Thread(target=monitor_loop, daemon=True)
        thread.start()

    def _handle_key_press(self, key_index: int, pressed: bool):
        """Handle key press events."""
        if key_index not in self.key_map:
            return

        key_config = self.key_map[key_index]
        action = key_config.get("action")

        if not pressed:
            return

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
            # TODO: Implement accept via OpenAI API
            self._update_key(key_index, "#00FF00")
            time.sleep(0.5)
            self._render_page(self.current_page)

        elif action == "reject":
            print("Action: Reject response")
            # TODO: Implement reject via OpenAI API
            self._update_key(key_index, "#FF0000")
            time.sleep(0.5)
            self._render_page(self.current_page)

        elif action == "new_chat":
            print("Action: New chat")
            # TODO: Implement new chat via OpenAI API
            self.agent_monitor.set_state("idle")
            self._render_page(1)

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
