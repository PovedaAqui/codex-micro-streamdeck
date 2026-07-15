# Codex Micro Stream Deck Bridge

Minimal viable product replicating the Codex Micro experience on a 6-key Stream Deck.

## Architecture

- **Page 1**: Agent Status | Accept | Reject | New Chat | Reasoning (toggle) | → Page 2
- **Page 2**: PR Review | Debug | Refactor | Test/Deploy | Stop All | → Page 1

## Setup

```bash
python3 -m venv venv && source venv/bin/activate
pip install streamdeck openai pyyaml pillow
```

## Usage

```bash
python main.py                    # Run with defaults
python main.py --config config.yaml  # Custom config
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
