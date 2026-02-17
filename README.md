# Fluxer - Discord Migration Tool
A tool to migrate your Profile and all Servers from Discord to Fluxer. 

This works as a self-bot so perform it at your own risk. You require your Fluxer User Token and Discord User Token to be able to operate this.

## Dependencies
You need Python 3 installed, as well as all some other dependencies, you can run `pip install -r requirements.txt` to get any requirements installed.

## Instructions for Running the Bot
1.) Clone the repository using one of the two options:
- ```git clone https://github.com/akarealemil/fluxer-discord-migration.git```

- Download the [ZIP from Github](https://github.com/akarealemil/fluxer-discord-migration/archive/refs/heads/main.zip) and copy it to a folder.

2.) Go to terminal. ```pip install -r requirements.txt```

NOTE: It's recommended to use a throwaway Discord account for this next step as it technically counts as self-botting if you care about your account. Give administrator access to the Discord account for the server you want to transfer.

3.) Go to config folder, rename config.example.json to config.json. Add Discord Token and Fluxer Token.
   - Discord Token: Open [Discord](https://discord.com/app), press F12 or go into your browser console. Click on the network tab. Filter using "API". Look on the headers side and search for "Authorization" or "Bearer". There will be a token, copy that value and put it into the JSON.
   - Fluxer Token: Open [Fluxer](https://fluxer.gg), press F12 or go into your browser console. Click on the network tab. Filter using "API". Look on the headers side and search for "Authorization" or "Bearer". There will be a token, copy that value and put it into the JSON. If you're having issue finding a request that has the token, click on any server on Fluxer with the Network Tab open and there will be more requests sent. Try one of the new ones, personally I used @me. 

4.) ```py main.py``` or ```python.exe main.py``` in the directory of the folder. Follow the instructions to convert. If the migration ever gets stuck, CTRL+C and try again.

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
