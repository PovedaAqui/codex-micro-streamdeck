# Codex Micro Stream Deck Bridge

Minimal viable product replicating the Codex Micro experience on a 6-key Stream Deck.

## Architecture

- **Page 1**: Agent Status | Accept | Reject | New Chat | Reasoning (toggle) | → Page 2
- **Page 2**: PR Review | Debug | Refactor | Test/Deploy | Stop All | → Page 1

## Setup

### Windows

```powershell
# 1. Install Python 3.11+ if not already installed
# Download from https://www.python.org/downloads/

# 2. Create virtual environment
python -m venv venv
.\venv\Scripts\Activate

# 3. Install dependencies
pip install streamdeck pillow pyyaml

# 4. Run
python main.py
```

### Linux

```bash
# 1. Install system dependencies
sudo apt-get install -y libhidapi-libusb0 libusb-1.0-0-dev

# 2. Create virtual environment
python3 -m venv venv && source venv/bin/activate

# 3. Install dependencies
pip install streamdeck pillow pyyaml

# 4. Run
python main.py
```

## Usage

```bash
python main.py                    # Run with defaults
python main.py --config config.yaml  # Custom config
python main.py --simulate         # Test without hardware
```

## Key mapping (6-key layout)

| Key | Page 1 | Page 2 |
|-----|--------|--------|
| 1 | Agent Status (dynamic) | PR Review |
| 2 | Accept | Debug |
| 3 | Reject | Refactor |
| 4 | New Chat | Test/Deploy |
| 5 | Reasoning (toggle) | Stop All |
| 6 | → Page 2 | → Page 1 |

## Configuration

Edit `config.yaml` to set your OpenAI API key and adjust polling interval.

## Troubleshooting

- **No Stream Deck found**: Make sure the Stream Deck is connected via USB and the Elgato Stream Deck software is not running (it locks the device).
- **Permission denied (Linux)**: Add your user to the `uinput` group or use `sudo`.
- **ImportError (streamdeck)**: Install the `streamdeck` package: `pip install streamdeck`
