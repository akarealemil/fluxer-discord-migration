# Fluxer - Discord Migration Tool
A tool to migrate your Profile and all Servers from Discord to Fluxer. 

This works as a self-bot so perform it at your own risk. You require your Fluxer User Token and Discord User Token to be able to operate this.

## Dependencies
You need Python 3 installed, as well as all some other dependencies, you can run `pip install -r requirements.txt` to get any requirements installed.


## Running The Bot
After you set your tokens and install all dependencies, run `py main.py` and it'll guide you through all of the steps.

## Features
- Migrate entire profile
  - Pronouns
  - Profile Picture
  - Banner (if available)
  - Pronouns
  - Bio
- Migrate servers you own and don't own
  - All Categories, Channels, Roles, Role Permissions
  - All Emojis and Stickers
  - Server Icon
- Smart Match
  - If you have an existing Fluxer server, you can use Smart Match to migrate your Discord server to the Fluxer server and it will match channel / role / category names and only add new ones.
