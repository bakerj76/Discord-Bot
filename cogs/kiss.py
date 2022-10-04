import discord
from discord.embeds import Embed
from discord.ext import commands
from operator import attrgetter
from PIL import Image, ImageDraw, ImageFilter
import io
import random

from helpers.rate_limit import RateLimiter

BIDEN_PIC_MASKS = (, )
BIDEN_PIC_PATHS = (, )
BIDEN_PIC_POS = ((376, 200), (571, 248), (1122, 513), (144, 51), (338, 172), (127, 69), (18, 117))
BIDEN_SIZE = (256, 512, 512, 64, 128, 256, 512)

class Kiss(commands.Cog):
	def __init__(self, bot):
		self.limiter = RateLimiter(5)
		self.__bot = bot

	@commands.command(
		name='kiss', 
		usage='[me or username]', 
		#brief='Kisses user',
		hidden=True
	)
	async def kiss(self, ctx, user):
		await ctx.message.delete()
		if not self.limiter.allow():
			return

		member = None
		user = user.lower()
		if user == 'me':
			member = ctx.author
		else:
			userIDMaybe = 0
			idFiltered = ''.join(filter(str.isdigit, user))

			if len(idFiltered) > 0:
				userIDMaybe = int(''.join(filter(str.isdigit, user)))

			member = next(filter(lambda m: m.name.lower() == user or (m.nick is not None and m.nick.lower() == user) or m.id == userIDMaybe, ctx.guild.members), None)

		if member is None:
			return

		rand = random.randint(0, len(BIDEN_PIC_PATHS)-1)
		avatar = await member.avatar_url_as(size=BIDEN_SIZE[rand]).read()
		avatar_img = Image.open(io.BytesIO(avatar)).resize((BIDEN_SIZE[rand], BIDEN_SIZE[rand]))

		mask = None
		joe_biden = Image.open(BIDEN_PIC_PATHS[rand])
		newImg = None
		if BIDEN_PIC_MASKS[rand] is not None:
			mask = Image.open(BIDEN_PIC_MASKS[rand]).convert('L')
			mask = mask.filter(ImageFilter.GaussianBlur(5))

			newImg = Image.new('RGB', joe_biden.size)
			newImg.paste(avatar_img, BIDEN_PIC_POS[rand])
			newImg.paste(joe_biden, mask=mask)
		else:
			mask = Image.new("1", avatar_img.size)
			draw = ImageDraw.Draw(mask)
			draw.ellipse((0, 0, avatar_img.size[0], avatar_img.size[1]),  fill=1)
			joe_biden.paste(avatar_img, BIDEN_PIC_POS[rand], mask)
			newImg = joe_biden
		
		arr = io.BytesIO()
		newImg.save(arr, format='JPEG')
		arr.seek(0)
		file = discord.File(arr, 'i_love_you.jpg')

		await ctx.send(file=file)
