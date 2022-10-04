import discord
from discord.embeds import Embed
from discord.ext import commands
import emoji
import math
import os
import re
import time
import unicodedata
import numbers

from db import db
from helpers.rate_limit import RateLimiter
from helpers.decorators import restrict_channels

COLOR = discord.Color(2310036) # Biden Blue
BOT_SPAM_CHANNEL_ID = [] if os.getenv('BOT_SPAM_CHANNEL_ID') is None else [int(id) for id in os.getenv('BOT_SPAM_CHANNEL_ID').split(',')]
TEST_CHANNEL_ID = int(os.getenv('TEST_CHANNEL_ID'))

SQUARE_COLORS = ['blue', 'red', 'green', 'brown', 'green', 'orange', 'purple', 'white_large']
BAR_SQUARES = 12

"""
TODO:
	- New syntax ✅
	- Custom emoji support ✅
	- Edit question/answers/emojis commands
	- Flags
		- -p --publish to publish
		- -t --time for timed polls
	- Closing polls
	- Time limit on polls
	- Circle graph image
	- Rate limit editing embed
"""
class Answer():
	def __init__(self, id, answer, reaction_emoji):
		self.id = id
		self.answer = answer
		self.reaction_emoji = reaction_emoji
		self.voters = []

class Question():
	def __init__(self, id, question, last_used, inserted):
		self.id = id
		self.question = question
		self.answers = {}
		self.last_used = last_used
		self.inserted = inserted

class PollData():
	def __init__(self, id):
		self.id = id
		self.author = None
		self.question = None
		self.message_id = None

class Poll(commands.Cog):
	def __init__(self, bot):
		self.limiter = RateLimiter(5)
		self.__bot = bot


	@commands.group(help='Commands used for creating and managing polls')
	async def poll(self, ctx):
		if ctx.invoked_subcommand is None:
			s = ctx.message.content.split(' ')
			if len(s) > 1:
				args = None if len(s) < 2 else s[2:]
				await self.poll_create(ctx, command_split=1)

	@poll.error	
	async def poll_error(self, ctx, error):
		await ctx.send_help()


	@poll.command(
		name='create', 
		usage='[question] [answer_1?] emoji_1? [answer_2?] emoji_2? [...]',  
		brief='Creates a poll question',
		help='Creates a poll question. Enclose question and answers in square brackets. OPTIONAL: Set an emoji for the answer by putting an emoji after the answer. To actually publish a poll with this question, type `/poll publish question_id`.'
	)
	async def poll_create(self, ctx, *arg, command_split=2, completion_message=True):
		arg = ' '.join(ctx.message.content.split(' ')[command_split:])
		skip, question = self.__enclosed_string(arg, '[', ']')
		question = question.strip()

		answers = []
		emojis = []
		while skip < len(arg):
			c = arg[skip]

			# Skip white space.
			if c.isspace():
				skip += 1

			# We found an emoji.
			elif c == '(' or c == ':' or c in emoji.UNICODE_EMOJI:
				emoji_id = None
				if c == '(' or c == ':':
					if c == '(':
						end, emoji_name = self.__enclosed_string(arg[skip:], '(', ')')
					else:
						end, emoji_name = self.__enclosed_string(arg[skip:], ':', ':')
					
					if end == -1:
						return

					emoji_id = self.__get_emoji_id(ctx.guild, emoji_name.strip())
					skip += end
				elif not unicodedata.name(c).startswith("EMOJI MODIFIER"):
					emoji_id = c
					skip += 1

				
				if not emoji_id:
					skip += 1
					continue
				
				emojis.append(emoji_id)

				if len(emojis) > len(answers):
					answers.append(None)

			# We found an answer.
			elif c == '[':
				end, answer  = self.__enclosed_string(arg[skip:], '[', ']')
				if end == -1:
					return

				skip += end

				answers.append(answer)
				
				if len(answers) > len(emojis) + 1:
					emojis.append(None)

			# We found a zero width joiner, so this emoji has a modifier.
			elif unicodedata.name(c) == 'ZERO WIDTH JOINER':
				# Get the last emoji and append zero with joiner and modifier.
				# emojis[-1] = emojis[-1] + c + arg[skip+1]

				# Skip it.
				skip += 3

			else:
				await ctx.send("Invalid formatting. Wow! How embarassing!")
				return

		if len(answers) == 0:
			await ctx.send("Listen fat. You have to put some answers to this question.")
			return

		if len(answers) > 20:
			await ctx.send("Come on, man. Too many answers.")  
			return

		if not self.limiter.allow():
			await ctx.send("Wait a couple seconds.")  
			return

		default_emojis = [chr(ord(u'🇿') - i) for i in range(26) if chr(ord(u'🇿') - i) not in emojis]
		timeNow = math.floor(time.time())

		cursor = db.cursor()
		cursor.execute("INSERT INTO `questions` (`question`, `last_used`, `inserted`) VALUES (?, ?, ?)", (question, timeNow, timeNow))
		question_id = cursor.lastrowid

		for i, answer in enumerate(answers):
			this_emoji = emojis[i] if len(emojis) > i and emojis[i] != None else default_emojis.pop()
			cursor.execute("INSERT INTO `answers` (`question_id`, `answer`, `emoji`) VALUES (?, ?, ?)", (question_id, answer, this_emoji))

		db.commit()
		cursor.close()

		if completion_message:
			await ctx.send(f'Created question #{question_id}. Use `/poll publish {question_id}` to start voting.')

		return question_id


	def __enclosed_string(self, s, start_delimiter, end_delimiter):
		count = 0
		start = s.find(start_delimiter)
		i = start
		if start == -1:
			return -1, s
		
		for c in s[start:]:
			if c == start_delimiter:
				count += 1
			elif c == end_delimiter:
				count -= 1

			if count == 0:
				return i+1, s[start+1:i]

			i += 1
		
		return -1, s

	def __get_emoji_id(self, guild, emoji_string):
		if emoji_string.startswith(':') and emoji_string.endswith(':'):
			emoji_id = emoji.emojize(emoji_string, use_aliases=True)

			if len(emoji_id) > 1:
				emoji_id = discord.utils.get(guild.emojis, name=emoji_string.replace(':', ''))

	@poll_create.error
	async def poll_create_error(self, ctx, error):
		return


	@poll.command(
		name='publish', 
		usage='question_id', 
		brief='Publish a poll to be voted on',
		help='Publish a poll to be voted on. Users can only vote once. A poll can be published in any channel. After the poll is published, your command message is deleted.'
	)
	async def poll_publish(self, ctx, id, skip_limiter=False):
		if not isinstance(id, numbers.Number) and not str.isnumeric(id):
			return

		if not skip_limiter and not self.limiter.allow():
			await ctx.send("Wait a couple seconds.")  
			return

		id = int(id)
		cursor = db.cursor()
		question_row = cursor.execute("SELECT 1 FROM `questions` WHERE `id` = ?", (id, )).fetchone()
		if question_row == None:
			cursor.close()
			return

		cursor.execute("INSERT INTO `polls` (`question_id`, `author`) VALUES (?, ?)", (id, ctx.author.id))
		poll_id = cursor.lastrowid

		poll_data = self.__get_poll_data(ctx.guild, cursor, poll_id)
		embed = self.__create_embed(poll_data)
		message = await ctx.send(embed=embed)

		cursor.execute("UPDATE `polls` SET `message_id` = ? WHERE `id`= ?", (message.id, poll_id))
		cursor.execute("UPDATE `questions` SET `last_used` = ? WHERE `id` = ?", (math.floor(time.time()), id))

		db.commit()
		cursor.close()

		for answer in poll_data.question.answers.values():
			reaction = answer.reaction_emoji[0]
			
			# Figure out ZWJs later, I guess. This is UNACCEPTABLE!!!!
			#if len(reaction) > 1:
			#	unicodeRegex = r'\\\\[u|U]([a-zA-Z0-9]*)'
			#	reaction = re.sub(unicodeRegex, r'\\u{\1}', str(answer.reaction_emoji.encode('ascii', 'backslashreplace'))[2:-1].lower())
			#	print(reaction)

			await message.add_reaction(reaction)

		await ctx.message.delete()

	@poll_publish.error
	async def poll_publish_error(self, ctx, error):
		return

	@poll.command(
		name='quick', 
		usage='[question] [answer_1?] emoji_1? [answer_2?] emoji_2? [...]',  
		brief='Creates and publishes a poll question',
		help='Creates  nd publishes a poll question. Enclose question and answers in square brackets. OPTIONAL: Set an emoji for the answer by putting an emoji after the answer. To actually publish a poll with this question, type `/poll publish question_id`.'

	)
	async def poll_quick(self, ctx):	
		if ctx.invoked_subcommand is None:
			s = ctx.message.content.split(' ')
			if len(s) > 1:
				args = None if len(s) < 2 else s[2:]
				question_id = await self.poll_create(ctx, command_split=2, completion_message=False)
				if question_id is not None:
					await self.poll_publish(ctx, question_id, skip_limiter=True)


	"""
	@poll.command(
		name='emojis', 
		usage='question_id emoji_1 emoji_2 emoji_3 ...', 
		brief='Sets the emojis for a poll question',
		help='Sets the emojis for a poll question. There can be more emojis than answers to a question. If there are less emojis supplied than answers, the default emojis are shown for the rest of the answers.'
	)
	async def poll_emojis(self, ctx, id, *args):
		if not str.isnumeric(id):
			return

		id = int(id)
		if id <= 0 or id > len(self.questions):
			return

		# If there are less supplied emojis than answers, just replace the first set of emojis.
		question = self.questions[id-1]
		if len(args) >= len(question.emojis):
			question.emojis = args
		else:
			question.emojis = args[:len(question.emojis)-1] + question.emojis[len(args):]
		
		await ctx.send("Set the emojis.")
	"""

	@commands.Cog.listener()
	async def on_raw_reaction_add(self, payload):
		# Ignore our own votes.
		if payload.user_id == self.__bot.user.id:
			return

		user = self.__bot.get_user(payload.user_id)
		message = await self.__bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
		guild = self.__bot.get_guild(payload.guild_id)

		# Get the poll associated with this message. If it doesn't exist, the reaction wasn't on a poll probably.
		cursor = db.cursor()
		row = cursor.execute("SELECT `id` FROM `polls` WHERE `message_id` = ?", (message.id, )).fetchone()
		if row == None:
			return
		
		poll_data = self.__get_poll_data(guild, cursor, row['id'])
		reaction_emoji = payload.emoji.name

		# Check if this emoji is valid, if not REMOVE IT IMMEDIATELY.
		if reaction_emoji not in (answer.reaction_emoji for answer in poll_data.question.answers.values()):
			await message.remove_reaction(payload.emoji, user)
			cursor.close()
			return

		# See if this user voted already. If so, remove the reaction and vote.
		lastVote = None
		for answer in poll_data.question.answers.values():
			if user.id in answer.voters:
				lastVote = answer.reaction_emoji

		# If they already voted for this somehow, we're done.
		if lastVote == reaction_emoji:
			cursor.close()
			return
		
		if lastVote is not None:
			# Delete the old reaction.
			oldReaction = next((r for r in message.reactions if r.emoji == lastVote), None)
			if oldReaction is not None:
				await oldReaction.remove(user)

			# Delete the vote from results.
			answer_id = next((answer.id for answer in poll_data.question.answers.values() if answer.reaction_emoji == lastVote), None)
			cursor.execute("DELETE FROM `poll_answers` WHERE `poll_id` = ? AND `user_id` = ?", (poll_data.id, user.id))
			poll_data.question.answers[answer_id].voters.remove(user.id)
		
		# Is this reaction a valid emoji in the poll?
		answer_id = next((answer.id for answer in poll_data.question.answers.values() if answer.reaction_emoji == reaction_emoji), None)
		if answer_id:
			# If it's an emoji used in the poll, append their user ID to results.
			cursor.execute("INSERT INTO `poll_answers` (`poll_id`, `user_id`, `answer_id`) VALUES (?, ?, ?)", (poll_data.id, user.id, answer_id))
			poll_data.question.answers[answer_id].voters.append(user.id)

		cursor.close()
		db.commit()

		# Update the embed.
		newEmbed = self.__create_embed(poll_data)
		await message.edit(embed=newEmbed)


	@commands.Cog.listener()
	async def on_raw_reaction_remove(self, payload):
		# Ignore our own votes.
		if payload.user_id == self.__bot.user.id:
			return

		user = self.__bot.get_user(payload.user_id)
		message = await self.__bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
		guild = self.__bot.get_guild(payload.guild_id)

		# Get the poll associated with this message. If it doesn't exist, the reaction wasn't on a poll probably.
		cursor = db.cursor()
		row = cursor.execute("SELECT `id` FROM `polls` WHERE `message_id` = ?", (message.id, )).fetchone()
		if row == None:
			return

		poll_data = self.__get_poll_data(guild, cursor, row['id'])

		reaction_emoji = payload.emoji.name
		answer_id = next((answer.id for answer in poll_data.question.answers.values() if answer.reaction_emoji == reaction_emoji), None)

		# Check if this emoji is valid, if not we're done.
		if reaction_emoji not in (answer.reaction_emoji for answer in poll_data.question.answers.values()):
			cursor.close()
			return

		# If this user is in the results, remove the vote.
		if user.id in poll_data.question.answers[answer_id].voters:
			cursor.execute("DELETE FROM `poll_answers` WHERE `poll_id` = ? AND `user_id` = ?", (poll_data.id, user.id))
			poll_data.question.answers[answer_id].voters.remove(user.id)

			# Update the embed.
			newEmbed = self.__create_embed(poll_data)
			await message.edit(embed=newEmbed)

			db.commit()

		cursor.close()

	def __get_poll_data(self, guild, cursor, poll_id):
		poll_data = PollData(poll_id)
		poll_row = cursor.execute("SELECT `p`.`question_id`, `q`.`question`, `q`.`last_used`, `q`.`inserted`, `p`.`author`, `p`.`message_id` FROM `polls` `p` INNER JOIN `questions` `q` ON `q`.`id` = `p`.`question_id` WHERE `p`.`id` = ?", (poll_id, )).fetchone()
		
		poll_data.question = Question(poll_row['question_id'], poll_row['question'], poll_row['last_used'], poll_row['inserted'])

		poll_data.author =  guild.get_member(poll_row['author'])
		poll_data.message_id = poll_row['message_id']

		answer_rows = cursor.execute("SELECT `id`, `answer`, `emoji` FROM `answers` WHERE `question_id` = ?", (poll_data.question.id, ))
		for row in answer_rows:
			answer_id = row['id']
			poll_data.question.answers[answer_id] = Answer(answer_id, row['answer'], row['emoji'])

		poll_answers_rows = cursor.execute("SELECT `user_id`, `answer_id` FROM `poll_answers` WHERE `poll_id` = ?", (poll_id, ))
		for row in poll_answers_rows:
			poll_data.question.answers[row['answer_id']].voters.append(row['user_id'])

		return poll_data

	def __create_embed(self, poll_data):
		"""
		Creates the embed message for the poll results.
		"""
		answers = [f'{answer.reaction_emoji} {answer.answer}' for i, answer in enumerate(poll_data.question.answers.values()) if answer.answer is not None]
		total_responses = sum(len(answer.voters) for answer in poll_data.question.answers.values())
		bars = []

		for i, answer in enumerate(poll_data.question.answers.values()):
			squares = 0 if total_responses == 0 else math.floor((len(answer.voters)/total_responses) * BAR_SQUARES)
			bar = emoji.emojize(f':{SQUARE_COLORS[i % len(SQUARE_COLORS)]}_square:') * squares
			empty_bar = '⬛' * (BAR_SQUARES - squares)
			bars.append(f'{answer.reaction_emoji} {bar}{empty_bar} {len(answer.voters)}')

		embed = Embed(
			title=poll_data.question.question,
			color=COLOR
		)
		if poll_data.author != None:
			embed.set_author(
				name=poll_data.author.name,
			)

		embed.set_footer(
			text=f'Poll #{poll_data.id}'
		)

		if len(answers) > 0:
			embed.add_field(
				name='Answers',
				value='\n'.join(answers),
				inline=False
			)
		
		embed.add_field(
			name='Results',
			value='\n'.join(bars),
			inline=False
		)

		return embed
