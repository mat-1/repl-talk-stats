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
				'$set': {
					'cycles': leader_data['cycles'],
					'avatar': leader_data['avatar']
				},
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
	async def get_leaders(self, limit=100):
		leaders = []
		async for leader in repltalk_data.find({}).sort('cycles', -1).limit(limit):
			if 'cycles' not in leader: continue
			cycles = leader['cycles']
			username = leader['_id']
			avatar = leader['avatar']
			leaders.append({
				'cycles': cycles,
				'name': username,
				'avatar': avatar
			})
		return leaders

db = Database()