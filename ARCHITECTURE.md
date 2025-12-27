## Components

### Python Agent
Files:
- agent.py
- tracked_chats.json

Responsibilities:
- parse user intent
- resolve targets (chats, people)
- choose correct Telegram action
- call Hammerspoon

### Hammerspoon
File:
- init.lua

Responsibilities:
- open Telegram Desktop
- search chats
- send messages
- handle mentions
- expose tg_cmd(payload_json)

### Data
- tracked_chats.json:
  - canonical chat names
  - aliases
  - mentions configuration

## Execution flow
1. User speaks or types a command
2. Python parses intent
3. Python resolves chat and mentions
4. Python calls hs CLI
5. Hammerspoon executes UI actions
6. Result returned to Python
