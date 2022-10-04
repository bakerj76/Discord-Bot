from discord.ext import commands
from collections.abc import Iterable

def iterable(obj):
    return isinstance(obj, Iterable)

def restrict_channels(*channel_ids):
	"""
	Restricts this command to these channels so it doesn't spam other chats.
	"""
	restricted_channel_ids = []
	for id in channel_ids:
		if isinstance(id, Iterable):
			restricted_channel_ids += [i for i in id]
		else:
			restricted_channel_ids.append(id)
	
	async def predicate(ctx):
		return ctx.channel and ctx.channel.id in restricted_channel_ids
	
	return commands.check(predicate)
