import datetime

class RateLimiter:
	def __init__(self, limit):
		self.limit = limit
		self.last_time = None

	def allow(self):
		timeNow = datetime.datetime.now()
		if self.last_time == None or (timeNow - self.last_time).seconds > self.limit:
			self.last_time = timeNow
			return True

		return False
