import collections
import discord
from discord.embeds import Embed
from discord.ext import commands
from googleapiclient.errors import HttpError
import os
import time
from urllib.parse import urlparse, parse_qs

from db import db
from helpers.rate_limit import RateLimiter
import youtube
from helpers.decorators import restrict_channels

COLOR = discord.Color(16250610) # Shell White
BOT_SPAM_CHANNEL_ID = [] if os.getenv('BOT_SPAM_CHANNEL_ID') is None else [int(id) for id in os.getenv('BOT_SPAM_CHANNEL_ID').split(',')]
TEST_CHANNEL_ID = int(os.getenv('TEST_CHANNEL_ID'))
YOUTUBE_PLAYLIST_URL = 'https://www.youtube.com/playlist?list='
YOUTUBE_VIDEO_URL='https://www.youtube.com/watch?v={}&list={}&index={}'
FETCH_INTERVAL = 60*5

Playlist = collections.namedtuple('Playlist', ['youtube_id', 'title', 'description', 'videos'])
Video = collections.namedtuple('Video', ['youtube_id', 'youtube_playlist_item_id', 'title', 'description', 'position', 'privacy_status'])

class YTPlaylist(commands.Cog):
	def __init__(self, bot):
		self.limiter = RateLimiter(2)
		self.fetch_timer = 0
		self.__bot = bot


	@commands.group()
	async def playlist(self, ctx):
		pass
	

	@playlist.command(name='list')
	async def list_playlists(self, ctx, *, playlist_name=None):
		if time.time() > self.fetch_timer:
			self.__update_db()

		embed = None
		if playlist_name is None:
			rows = db.execute('SELECT `p`.`youtube_id`, `p`.`title`, `p`.`description`, (SELECT COUNT(*) FROM `videos` `v` WHERE `v`.`playlist_id` = `p`.`id`) as `videos` FROM `playlists` `p`', ())
			playlists = [Playlist(
				youtube_id=row['youtube_id'],
				title=row['title'],
				description=row['description'],
				videos=row['videos']
			) for row in rows]
			description = ''
			fields = []

			if len(playlists) == 0:
				description = "There aren't any playlists yet." 

			embed = discord.Embed( 
				title='Youtube Playlists',
				description= description,
				color=COLOR,
			)

			for playlist in playlists:
				embed.add_field(
					name="═════════════",
					value=f"[{playlist.title}]({YOUTUBE_PLAYLIST_URL}{playlist.youtube_id}) ({playlist.videos} videos)\n" +
						  (playlist.description[:1024] if len(playlist.description) else 'No description.')
				)

		else:
			row = db.execute('SELECT `id`, `youtube_id`, `title`, `description` FROM `playlists` WHERE `title` LIKE ? ORDER BY `id` LIMIT 1', (playlist_name, )).fetchone()
			if row == None:
				return

			embed = discord.Embed(
				title=row['title'],
				description=(row['description'][:1024] if len(row['description']) > 0 else 'No description.'),
				url=f"{YOUTUBE_PLAYLIST_URL}{row['youtube_id']}",
			)

			video_rows = db.execute('SELECT `youtube_id`, `title`, `description`, `position` FROM `videos` WHERE `playlist_id` = ? ORDER BY `position` DESC', (row['id'], ))
			for i, video_row in enumerate(list(video_rows)):
				embed.add_field(
					name="═════════════",
					value=f"{i+1}. [{video_row['title']}]({YOUTUBE_VIDEO_URL.format(video_row['youtube_id'], row['youtube_id'], video_row['position'])})\n" + 
						  (video_row['description'][:256] + ('...' if len(video_row['description']) > 256 else '') if len(video_row['description']) > 0 else 'No description.'),
					inline=False,
				)

		await ctx.send(embed=embed)


	@playlist.command(name='create')
	@restrict_channels(BOT_SPAM_CHANNEL_ID, TEST_CHANNEL_ID)
	@commands.has_role('overlords')
	async def create_playlist(self, ctx, title, description):
		request = youtube.get_client().playlists().insert(
			part='snippet,status',
			body={
				'snippet': {
					'title': title,
					'description': description,
					'defaultLanguage': 'en'
				},
				'status': {
					'privacyStatus': 'public',
				}
			}
		)
		response = request.execute()

		await ctx.send(f"Added a new YouTube playlist [{title}]({YOUTUBE_PLAYLIST_URL}{response['id']}).")

		cursor = db.cursor()
		cursor.execute(
			'INSERT INTO `playlists` (`youtube_id`, `title`, `description`) VALUES (?, ?, ?)', 
			(response['id'], response['snippet']['title'], response['snippet']['description'])
		)
		db.commit()
		cursor.close()


	@playlist.command(name='add')
	@restrict_channels(BOT_SPAM_CHANNEL_ID, TEST_CHANNEL_ID)
	@commands.has_role('overlords')
	async def add_playlist(self, ctx, playlist, *video_urls):
		row = db.execute("SELECT `id`, `youtube_id` FROM `playlists` WHERE `title` LIKE ? ORDER BY `id` LIMIT 1", (playlist, )).fetchone()
		
		# If we can't find the playlist in the database, try updating the database and see if it was created outside of Discord commands
		if row is None and time.time() > self.fetch_timer:
			self.__update_db()
			row = db.execute("SELECT `id`, `youtube_id` FROM `playlists` WHERE `title` LIKE ? ORDER BY `id` LIMIT 1", (playlist, )).fetchone()

			if row is None:
				return

		elif row is None:
			return
		
		playlist_id = row['id']
		yt_playlist_id = row['youtube_id']

		video_urls = [video_url[1:-1] if video_url.startswith('<') else video_url for video_url in video_urls]
		video_ids = [parse_qs(urlparse(video_url).query)['v'][0] for video_url in video_urls]
		request = youtube.get_client().videos().list(
			part="snippet,status",
			id=','.join(video_ids),
		)
		response = request.execute()

		cursor = db.cursor()
		inserted = 0
		for item in response['items']:
			if item['status']['privacyStatus'] == 'private':
				continue

			insertRequest = youtube.get_client().playlistItems().insert(
				part='contentDetails,snippet',
				body={
					'snippet': {
						'playlistId': yt_playlist_id,
						'resourceId': {
							'videoId': item['id'],
							'kind': 'youtube#video'
						},
					},
				}
			)
			insertResponse = insertRequest.execute()

			cursor.execute(
				'INSERT OR IGNORE INTO `videos` (`youtube_id`, `youtube_playlist_item_id`, `playlist_id`, `title`, `description`, `position`) VALUES (?, ?, ?, ?, ?, ?)', 
				(insertResponse['contentDetails']['videoId'], insertResponse['id'], playlist_id, insertResponse['snippet']['title'], insertResponse['snippet']['description'], 0)
			)
			inserted += 1
		db.commit()
		cursor.close()

		if inserted == 0:
			await ctx.send(f"Couldn't add any videos.")
		else:
			await ctx.send(f'Added {inserted} videos.')


	@playlist.command(name='remove')
	@restrict_channels(BOT_SPAM_CHANNEL_ID, TEST_CHANNEL_ID)
	@commands.has_role('overlords')
	async def remove_playlist(self, ctx, playlist, *video_urls):
		row = db.execute("SELECT `id`, `youtube_id` FROM `playlists` WHERE `title` LIKE ? ORDER BY `id` LIMIT 1", (playlist, )).fetchone()
		
		# If we can't find the playlist in the database, try updating the database and see if it was created outside of Discord commands
		if row is None and time.time() > self.fetch_timer:
			self.__update_db()
			row = db.execute("SELECT `id`, `youtube_id` FROM `playlists` WHERE `title` LIKE ? ORDER BY `id` LIMIT 1", (playlist, )).fetchone()

			if row is None:
				return

		elif row is None:
			return

		playlist_id = row['id']
		yt_playlist_id = row['youtube_id']

		video_urls = [video_url[1:-1] if video_url.startswith('<') else video_url for video_url in video_urls]
		video_ids = [f"'{parse_qs(urlparse(video_url).query)['v'][0]}'" for video_url in video_urls]
		cursor = db.cursor()
		deleted = 0
		rows = db.execute(f"SELECT `id`, `youtube_playlist_item_id` FROM `videos` WHERE `playlist_id` = ? AND `youtube_id` IN ({','.join(video_ids)})", (playlist_id, ))
		for row in rows:
			try:
				request = youtube.get_client().playlistItems().delete(
					id=row['youtube_playlist_item_id'],
				)
				request.execute()
			except HttpError as e:
				if e.resp.status == 404:
					pass
				else:
					print(e)

			cursor.execute('DELETE FROM `videos` WHERE `id` = ?', (row['id'], ))
			deleted += 1
		db.commit()
		cursor.close()

		if deleted == 0:
			await ctx.send(f"Couldn't delete any videos.")
		else:
			await ctx.send(f'Deleted {deleted} videos.')

	
	@playlist.command(name='delete')
	@restrict_channels(BOT_SPAM_CHANNEL_ID, TEST_CHANNEL_ID)
	@commands.has_role('overlords')
	async def delete_playlist(self, ctx, playlist):
		row = db.execute("SELECT `id`, `youtube_id`, `title` FROM `playlists` WHERE `title` LIKE ? ORDER BY `id` LIMIT 1", (playlist, )).fetchone()
		
		# If we can't find the playlist in the database, try updating the database and see if it was created outside of Discord commands
		if row is None and time.time() > self.fetch_timer:
			self.__update_db()
			row = db.execute("SELECT `id`, `youtube_id`, `title` FROM `playlists` WHERE `title` LIKE ? ORDER BY `id` LIMIT 1", (playlist, )).fetchone()

			if row is None:
				return

		elif row is None:
			return

		playlist_id = row['id']
		yt_playlist_id = row['youtube_id']
		playlist_title = row['title']

		try:
			request = youtube.get_client().playlists().delete(
				id=yt_playlist_id,
			)
			request.execute()
		except HttpError as e:
			if e.resp.status == 404:
				pass
			else:
				print(e)
		
		cursor = db.cursor()
		cursor.execute('DELETE FROM `playlists` WHERE `id` = ?', (playlist_id, ))
		db.commit()
		cursor.close()

		await ctx.send(f'Deleted {playlist_title}.')

		
	def __update_db(self):
		request = youtube.get_client().playlists().list(
			part='snippet,status',
			mine=True,
			maxResults=25,
		)
		response = request.execute()

		items = response['items']
		cursor = db.cursor()

		for item in items:
			if item['status']['privacyStatus'] == 'private':
				continue

			row = cursor.execute('SELECT `id`, `title`, `description` FROM  `playlists` WHERE `youtube_id` = ?', (item['id'], )).fetchone()
			playlist_id = None
			yt_playlist_id = item['id']
			
			if row == None:
				cursor.execute(
					'INSERT INTO `playlists` (`youtube_id`, `title`, `description`) VALUES (?, ?, ?)', 
					(item['id'], item['snippet']['title'], item['snippet']['description'])
				)
				playlist_id = cursor.lastrowid
			else:
				playlist_id = row['id']
				if row['title'] != item['snippet']['title'] or row['description'] != item['snippet']['description']:
					cursor.execute(
						'UPDATE `playlists` SET `title` = ?, `description` = ? WHERE `id` = ?', 
						(item['snippet']['title'], item['snippet']['description'], playlist_id)
					)

			request = youtube.get_client().playlistItems().list(
				part='snippet,contentDetails,status',
				playlistId=yt_playlist_id,
				maxResults=25,
			)
			response = request.execute()

			playlistItems = response['items']
			videos = [Video(
				youtube_id=playlistItem['contentDetails']['videoId'],
				youtube_playlist_item_id=playlistItem['id'],
				title=playlistItem['snippet']['title'],
				description=playlistItem['snippet']['description'],
				position=playlistItem['snippet']['position'],
				privacy_status=playlistItem['status']['privacyStatus']
			) for playlistItem in playlistItems]

			for video in videos:
				if video.privacy_status == 'private':
					continue

				playlistRow = cursor.execute('SELECT `id`, `youtube_id`, `title`, `description`, `position` FROM  `videos` WHERE `youtube_playlist_item_id` = ?', (video.youtube_playlist_item_id, )).fetchone()
				if playlistRow == None:
					cursor.execute(
						'INSERT INTO `videos` (`youtube_id`, `youtube_playlist_item_id`, `playlist_id`, `title`, `description`, `position`) VALUES (?, ?, ?, ?, ?, ?)', 
						(video.youtube_id, video.youtube_playlist_item_id, playlist_id, video.title, video.description, video.position)
					)
					playlist_item_id = cursor.lastrowid
				else:
					if playlistRow['title'] != video.title or \
					   playlistRow['description'] != video.description or \
					   playlistRow['position'] != video.position or \
					   playlistRow['youtube_id'] != video.youtube_id:
						cursor.execute(
							'UPDATE `videos` SET `youtube_id` = ?, `title` = ?, `description` = ?, `position` = ? WHERE `id` = ?', 
							(video.youtube_id, video.title, video.description, video.position, playlistRow['id'])
						)

			db_video_rows = cursor.execute('SELECT `youtube_playlist_item_id` FROM  `videos` WHERE `playlist_id` = ?', (playlist_id, ))
			video_ids = set(video.youtube_playlist_item_id for video in videos)
			for video_row in db_video_rows:
				if video_row['youtube_playlist_item_id'] not in video_ids:
					cursor.execute('DELETE FROM `videos` WHERE `youtube_playlist_item_id` = ?', (video_row['youtube_playlist_item_id'], ))

		db.commit()
		cursor.close()
		self.fetch_timer = time.time() + FETCH_INTERVAL
