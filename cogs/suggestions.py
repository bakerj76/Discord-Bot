import codecs
import discord
from discord.embeds import Embed
from discord.ext import commands
from operator import attrgetter
import os

from db import db
from helpers.rate_limit import RateLimiter
from helpers.decorators import restrict_channels

COLOR = discord.Color(14747136) # Honest Red
BOT_SPAM_CHANNEL_ID = [] if os.getenv('BOT_SPAM_CHANNEL_ID') is None else [int(id) for id in os.getenv('BOT_SPAM_CHANNEL_ID').split(',')]
TEST_CHANNEL_ID = int(os.getenv('TEST_CHANNEL_ID'))

class Suggestions(commands.Cog):
	def __init__(self, bot):
		self.limiter = RateLimiter(2)
	
	@commands.command(help='Suggest something to add to the bot')
	@restrict_channels(BOT_SPAM_CHANNEL_ID, TEST_CHANNEL_ID)
	async def suggest(self, ctx, *args):
		suggestion = ' '.join(args)
		if self.limiter.allow():
			cursor = db.cursor()
			cursor.execute('INSERT INTO `suggestions` (`suggestion`, `user_id`) VALUES (?, ?)', (suggestion, ctx.author.id))
			db.commit()
			cursor.close()

			await ctx.send('Thank you for your suggestion.') 
			return
		
		await ctx.send('Too many suggestions. Give me a sec.')

	@suggest.error
	async def suggest_error(self, ctx, error):
		return


	@commands.command(
		name='suggestions',
		help='Show the current suggestions'
	)
	@restrict_channels(BOT_SPAM_CHANNEL_ID, TEST_CHANNEL_ID)
	async def list_suggestions(self, ctx):
		todo = []
		completed = []
		cursor = db.cursor()
		for suggestion in cursor.execute('SELECT `suggestion`, `completed`, `user_id` FROM `suggestions` ORDER BY `id`'):
			if suggestion['completed'] == 1:
				completed.append(suggestion)
			else:
				todo.append(suggestion)

		embed = Embed(type='rich')
		embed.color = COLOR
		embed.title = f'Suggestions for {ctx.bot.user.name}'

		if len(todo) == 0 and len(completed) == 0:
			embed.description = "There aren't any suggestions."
			await ctx.send(embed=embed)
			return

		description_texts = []
		for i, suggestion in enumerate(todo):
			description_text = f"{i+1}. {suggestion['suggestion']} ({ctx.guild.get_member(suggestion['user_id']).name})"
			if suggestion['user_id'] == ctx.author.id:
				description_text = f"**{description_text}**"

			description_texts.append(description_text)

		embed.description = '\n'.join(description_texts)

		if len(completed) > 0:
			embed.add_field(
				name='Completed Suggestions',
				value='\n'.join(f"{i+1}. {suggestion['suggestion']} ({ctx.guild.get_member(suggestion['user_id']).name})" for i, suggestion in enumerate(completed))
			)

		await ctx.send(embed=embed)

	@list_suggestions.error
	async def list_suggestions_error(self, ctx, error):
		return


	@commands.group(help='Do something with a suggestion')
	@restrict_channels(BOT_SPAM_CHANNEL_ID, TEST_CHANNEL_ID)
	async def suggestion(self, ctx):
		if ctx.invoked_subcommand is None:
			pass


	@suggestion.command(
		name="add",
		usage='[suggestion]',
		help='Add a suggestion (same as /suggest)'
	)
	async def add_suggestion(self, ctx, *args):
		await self.suggest(ctx, *args)
	

	@suggestion.command(
		name="delete",
		usage='[suggestion ids]',
		help='Delete a suggestion'
	)
	@restrict_channels(BOT_SPAM_CHANNEL_ID, TEST_CHANNEL_ID)
	async def delete_suggestion(self, ctx, *args):
		delete_completed = args[0].lower() == 'completed'

		# TODO: Put this in a helper function (has_role(ctx.author, 'overlords'))
		admin = 'overlords' in map(attrgetter('name'), ctx.author.roles)

		if delete_completed and not admin:
			return

		indices = [int(i)-1 for i in args if str.isnumeric(i)]

		if len(indices) == 0:
			return

		if not self.limiter.allow():
			await ctx.send('Try again in a bit.')
			return

		cursor = db.cursor()
		rows = cursor.execute('SELECT `id`, `user_id` FROM `suggestions` WHERE `completed` = ? ORDER BY `id`', (delete_completed, ))

		ids = []
		deleted_indices = []
		for i, row in enumerate(rows):
			if i in indices and (admin or row['user_id'] == ctx.author.id):
				ids.append(str(row['id']))
				deleted_indices.append(str(i+1))
		
		cursor.execute(f"DELETE FROM `suggestions` WHERE `id` IN ({','.join(ids)})")

		db.commit()
		cursor.close()

		ret = ''
		if len(ids) > 0:
			ret += f"Deleted suggestion{'s' if len(deleted_indices) > 1 else ''} {', '.join(deleted_indices)}."
		
		diff = set(str(i+1) for i in indices) - set(deleted_indices)
		if len(diff) > 0:
			ret += f" Could not delete {', '.join(diff)}. You can only delete your own suggestions."

		await ctx.send(ret)


	@delete_suggestion.error
	async def delete_suggestion_error(self, ctx, error):
		return


	@suggestion.command(
		name='complete',
		usage='[suggestion ids]',
		help='Mark a suggestion as completed'
	)
	@restrict_channels(BOT_SPAM_CHANNEL_ID, TEST_CHANNEL_ID)
	@commands.has_role('overlords')
	async def complete_suggestion(self, ctx, *args):
		indices = [int(i)-1 for i in args if str.isnumeric(i)]

		if len(indices) == 0:
			return

		if not self.limiter.allow():
			await ctx.send('Try again in a bit.')

		cursor = db.cursor()
		rows = cursor.execute("SELECT `id` FROM `suggestions` WHERE `completed` = 0 ORDER BY `id`")
		ids = [str(row['id']) for i, row in enumerate(rows) if i in indices]

		cursor.execute(f"UPDATE `suggestions` SET `completed` = 1 WHERE `id` IN ({','.join(ids)})")
		
		db.commit()
		cursor.close()

		await ctx.send(f"Completed  suggestion{'s' if len(indices) > 1 else ''}.")
		return

	@complete_suggestion.error
	async def complete_suggestion_error(self, ctx, error):
		return


	@suggestion.command(
		name="uncomplete",
		usage='[suggestion ids]',
		help='Mark a suggestion as completed'
	)
	@restrict_channels(BOT_SPAM_CHANNEL_ID, TEST_CHANNEL_ID)
	@commands.has_role('overlords')
	async def completed_suggestion(self, ctx, *args):
		indices = [int(i)-1 for i in args if str.isnumeric(i)]

		if len(indices) == 0:
			return

		if not self.limiter.allow():
			await ctx.send('Try again in a bit.')
			return

		cursor = db.cursor()
		rows = cursor.execute("SELECT `id` FROM `suggestions` WHERE `completed` = 1 ORDER BY `id`")
		ids = [str(row['id']) for i, row in enumerate(rows) if i in indices]

		cursor.execute(f"UPDATE `suggestions` SET `completed` = 0 WHERE `id` IN ({','.join(ids)})")
		
		db.commit()
		cursor.close()

		await ctx.send(f"Uncompleted  suggestion{'s' if len(indices) > 1 else ''}.")
		

	@completed_suggestion.error
	async def completed_suggestion_error(self, ctx, error):
		return
