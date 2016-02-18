## Introduction
Attempt to create a python script that monitors a telegram bot URL and replies to commands for logging data related to Bristol 'poop' measures.

Check more information about [Telegram Bots](https://core.telegram.org/bots/).

## Important
- The bot will only allow direct interactions, not being added to groups for increased privacy

## Notes
- On first execution it will create database and start filling values

## Test
- I've a copy running with the name `@cagolin_bot`.  Give it a try or click  <https://telegram.me/cagolin_bot>.

## Usage
- The bot should give you requests with custom keyboards for each data it requires and operations like filling new values, consulting historical data, etc.

## Extra commands only for owner user
### Configuration
The bot, once token has been used and owner set via commandline, will store that information in the database, so you can control it from a chat window

- `/config show` will list actual defined settings
- `/config set var=value` will set one of those settings with a new value
    - As of this writing (verbosity, url for api, token, sleep timeout, owner, database, run in daemon mode)

### Stats
The bot stores stats on users/chats, remembering the chat/user name and last time seen so it can be later used for purging data not being accessed in a while
- `/stats show (user|chat)` will list the list of users/chats and time of last update
 
