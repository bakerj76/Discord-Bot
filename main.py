from discord.ext import commands
import os
import signal
import sys
import warnings

import cogs

"""
TODO:
 - Better /help
"""

bot = commands.Bot(command_prefix='/')
bot.add_cog(cogs.Poll(bot))
bot.add_cog(cogs.Suggestions(bot))
bot.add_cog(cogs.Kiss(bot))
bot.add_cog(cogs.YTPlaylist(bot))

@bot.event
async def on_ready():
    print('Logged in as {}'.format(bot.user.name))
    print('Connected to guilds:')
    for guild in bot.guilds:
        print(guild)

@bot.event
async def on_command_error(ctx, error):
    print(error)

def signal_handler(sig, frame):
    print('Logging out as {}'.format(bot.user.name))
    bot.close()


def main():
	if os.getenv('DISCORD_BOT_TOKEN') is None:
		raise Exception("Bot token not set in environment variables")

	if os.getenv('TEST_CHANNEL_ID') is None:
		warnings.warn("Test channel ID not set in environment variables")

	if os.getenv('BOT_SPAM_CHANNEL_ID') is None:
		warnings.warn("Bot spam channel ID not set in environment variables")
	
	bot.run(os.getenv('DISCORD_BOT_TOKEN'))

if __name__ == '__main__':
    main()
