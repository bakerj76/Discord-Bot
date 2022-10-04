# Discord Bot
### Quick Start Guide
1. Download [Python 3.8.3](https://www.python.org/downloads/)
1. Install Python and make sure to select "Add Python to environment variables" and "Install pip"
1. Download and install [Visual Studio Code](https://code.visualstudio.com/)
1. Download and install [Github Desktop](https://desktop.github.com/)
1. In Github Desktop, clone this repository (https://github.com/bakerj76/Joe-Biden-Bot.git)
1. Create an application https://discord.com/developers/applications
1. Create a bot for your application
1. If you have a test server, you can add your bot to it by going to `OAuth2` under your bot's settings. Then choose `bot` as your scope and select any permissions you need. Then paste the redirect URL into your browser and add the bot to your channel. You can use my test channel here: https://discord.gg/y7Xgxua.
1. Open the repo folder in VSCode
1. Install the Python extension for VSCode
1. Go to `Run > Add Configuration...`
1. Set `"program"` to `"${workspaceFolder}/main.py"` and add `"env": { "DISCORD_BOT_TOKEN": "[Your bot token found on your bot's page on Discord]", "BOT_SPAM_CHANNEL_ID": "[The spam channel ID on your Discord server]" }`
My configuration looks like this:
```json
  "configurations": [
      {
        "name": "Python: Current File",
        "type": "python",
        "request": "launch",
        "program": "${workspaceFolder}/main.py",
        "console": "integratedTerminal",
        "env": {
          "DISCORD_BOT_TOKEN": "[Bot token for Joe Biden Bot]",
          "BOT_SPAM_CHANNEL_ID": "714618628401528882"
         },
      }
    ]
```
1. In the `Terminal` tab at the bottom of VS Code, create a virtual environment script by typing `python -m venv venv`. This makes sure that any packages that you add to the project are only installed for this project rather than on your globally on your Python install.
1. Activate the venv by typing `.\venv\Scripts\Activate.ps1` (Windows Power Shell). If that doesn't work, open Windows Powershell as Administrator and run `set-executionpolicy remotesigned` and say yes to all. Then reload the terminal by hitting the trash button and pulling the terminal back up from the bottom.
1. Install the packages in the `requirements.txt` file by typing `python -m pip install -r requirements.txt`
1. Press F5 and see if it works!
### Containerized BidenBot instructions
1. Build the container image with `make build`
1. Run the container with `make run`

### TODO
- [x] Put all the custom txt files into their own folder and put it in .gitignore.
- [ ] Poll bot
- [ ] Bias bot
