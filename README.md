# SayDo — Voice-first desktop agent for macOS

## What is this project
SayDo is a local desktop agent for macOS that allows controlling Telegram Desktop
using natural language commands (spoken or text).

The agent:
- understands chat names and aliases
- understands people names and aliases
- can open chats, write messages, mention users
- works through Hammerspoon (macOS UI automation)
- is controlled by a Python "brain" via hs.ipc (CLI)

This is NOT a Telegram bot and NOT Telegram API.
This agent controls the real Telegram Desktop app like a human.

## Architecture overview
There are two main parts:

1. Python agent (brain)
- Parses natural language commands
- Resolves chat names and aliases
- Decides what action to perform
- Calls Hammerspoon via hs CLI (hs.ipc)

2. Hammerspoon (hands)
- Controls Telegram Desktop UI
- Opens search, selects chats
- Types and sends messages
- Mentions users when possible

Python never touches UI directly.
Hammerspoon never parses language.

## Communication
Python -> Hammerspoon:
- via `hs -c 'return tg_cmd(JSON)'`
- JSON in / JSON out

No HTTP, no TCP sockets.

## Supported commands (MVP)
- open chat by name or alias
- send text message
- send message with mention
- send message to Saved Messages
- paste from clipboard

## Known limitations
- Mentions do not work in Saved Messages
- Chat resolution depends on aliases
- Telegram UI may change over time

## Philosophy
- Human language first, not commands
- Desktop automation over APIs
- Learnable and extensible architecture
- Safety over speed (explicit actions)

## DO NOT
- Do not replace UI automation with Telegram API
- Do not introduce web servers
- Do not remove hs.ipc communication
# test
