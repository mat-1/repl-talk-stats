from datetime import datetime
import motor.motor_asyncio
import asyncio
import urllib
import uuid
import os

dbuser = os.getenv('dbuser')
dbpassword = urllib.parse.quote_plus(os.getenv('dbpassword'))

url = f'mongodb+srv://{dbuser}:{dbpassword}@cluster0-b0kyn.azure.mongodb.net/test?retryWrites=true&w=majority'

client = motor.motor_asyncio.AsyncIOMotorClient(
	url
)
database = client['repl-talk-stats']

repltalk_data = database['data']

class Database():
	def __init__(self):
		pass
	async def add_leaders(
		self, leaders
	):
		print('updating leaders')
		t = datetime.now()
		for leader_data in leaders:
			data = {
				'$push': {
					'history': {
						'time': t,
						'cycles': leader_data['cycles']
					}
				}
			}
			await repltalk_data.update_one({
				'_id': leader_data['_id']
			},
			data,
			upsert=True)
	async def get_previous_leaders(self):
		history = {}
		async for leader_data in repltalk_data.find({'position': {'$gte': 60}}):
			history[leader_data['_id']] = leader_data
		return history
	async def get_user_history(self, name):
		data = await repltalk_data.find_one({'_id': name})
		if not data: return
		return data['history']
	'''async def fix(self):
		prev_leaders = await self.get_previous_leaders()
		l_before = {'leaders':{}}
		prev_leaders_tmp = list(prev_leaders)
		i=len(prev_leaders)
		print('fixing leaderboards')
		for l in reversed(prev_leaders_tmp):
			if l['leaders'] == l_before['leaders']:
				print(i)
				del prev_leaders[i-1]
				print('deleted',i-1)
			l_before = l
			i-=1
		for l in reversed(prev_leaders_tmp):
			for u in l['leaders']:
				print(i)
				del prev_leaders[i-1]
				print('deleted',i-1)
			l_before = l
			i-=1
		await repltalk_data.update_one({'_id': 'leaderboard'}, {'$set':{'history':prev_leaders}})'''

db = Database()