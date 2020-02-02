from aiohttp import web
from jinja2 import Environment, \
	FileSystemLoader, \
	select_autoescape
from compress import compress_html
from database import db
from datetime import datetime
import repltalk
import asyncio
import time
import math

client = repltalk.Client()

jinja_env = Environment(
	loader=FileSystemLoader(searchpath='templates'),
	autoescape=select_autoescape(['html', 'xml']),
	enable_async=True,
	extensions=['jinja2.ext.do']
)

def jinja_print(*args):
	print(*args)
	return ''
def jinja_append(l, v):
	return l + [v]

jinja_env.globals['print'] = jinja_print

class templates:
	template_dict = {}
class cache:
	leaderboard = None
	_leaderboard = 0
	userinfo = {}
	prev_leaders = {}

	website = {}


# leaderboard_players being a multiple of 30 is better
leaderboard_players = 300

display_leaderboard_players = 100

async def get_leaderboard(from_database=True):
	if from_database:
		leaderboard = await db.get_leaders(display_leaderboard_players)
	else:
		leaderboard = await client.get_leaderboard(leaderboard_players)
	return leaderboard
	
async def update_database():
	leaderboard = await get_leaderboard(from_database=False)
	
	new_leaders = []
	for position, user in enumerate(leaderboard):
		new_leaders.append({
			'_id': user.name,
			'position': position,
			'cycles': user.cycles,
			'avatar': user.avatar
		})
	await db.add_leaders(new_leaders)
	return leaderboard

async def update_database_forever():
	update_time = 60 * 60 * 12
	await asyncio.sleep(update_time - (time.time() % update_time))
	while True:
		await update_database()
		await asyncio.sleep(update_time) 

async def get_user(username):
	if username in cache.userinfo:
		if time.time()-60 < cache.userinfo[username][0]:
			userinfo = cache.userinfo[username][1]
			return userinfo
			
	userinfo = await client.get_user(username)
	cache.userinfo[username] = (time.time(), userinfo)
	return userinfo

async def load_template(filename, **kwargs):
	if filename in templates.template_dict:
		r =  await templates.template_dict[filename].render_async(**kwargs)
	else:
		# print(f'Loading template {filename} for the first time')
		t = jinja_env.get_template(filename)
		templates.template_dict[filename] = t
		r = await t.render_async(**kwargs)
	return r

routes = web.RouteTableDef()

@routes.get('/')
async def index(request):
	l = await get_leaderboard()
	return await load_template('index.html', leaderboard=l)

@routes.get('/user/{username}')
async def get_user_route(request):
	username = request.match_info['username']
	history = await db.get_user_history(username)
	# print(len(cache.prev_leaders), 'previous histories found')
	if history is None:
		r = '<h1>Invalid user.</h1>'
		return web.Response(
			text=r,
			headers={
				'content-type': 'text/html'
			}
		)
	u = await get_user(username)
	return await load_template(
		'user.html', u=u, history=history, epoch=datetime.utcfromtimestamp(0)
	)

@routes.get('/compare/{user1}/{user2}')
async def compare_users_route(request):
	user1 = request.match_info['user1']
	user2 = request.match_info['user2']
	print(len(cache.prev_leaders), 'previous histories found')
	user1_invalid = user1 not in cache.prev_leaders[-1]['leaders']
	user2_invalid = user2 not in cache.prev_leaders[-1]['leaders']
	if user1_invalid or user2_invalid:
		r = '<h1>Invalid user.</h1>'
		return web.Response(
			text=r,
			content_type='text/html'
		)
	u1 = await get_user(user1)
	u2 = await get_user(user2)
	h = list(cache.prev_leaders)
	h.append({
		'time': datetime.now(),
		'leaders': {
			u1.name: u1.cycles,
			u2.name: u2.cycles
		}
	})
	return await load_template(
		'compare.html', u1=u1, u2=u2, history=h, epoch=datetime.utcfromtimestamp(0)
	)

website_cache_timeout = 60 # a minute

@web.middleware
async def content_type_middleware(request, handler):
	#print('content type middleware started')
	r = await handler(request)
	if isinstance(r, str):
		r = web.Response(
			text=r,
			headers={
				'content-type': 'text/html'
			}
		)
	content_types = {
		'css': 'text/css',
		'js': 'text/javascript',
		'html': 'text/html'
	}
	if r.content_type == 'application/octet-stream':
		parts = request.url.parts
		last_path = parts[-1]
		ext = last_path.rsplit('.', 1)[-1]
		if ext in content_types:
			r.content_type = content_types[ext]
		else:
			r.content_type = 'text/plain'
	if r.content_type == 'text/html':
		r.text = compress_html(r.text)
	#print('content type middleware ended')
	return r

@web.middleware
async def cache_middleware(request, handler):
	path = str(request.path)
	if path in cache.website:
		cached = cache.website[path]
		if cached[0] > time.time() - website_cache_timeout:
			print('creating response')
			r = web.Response(**cached[1])
			print('using cache',r)
			return r
	#print('loading handler')
	r = await handler(request)
	headers = r.headers
	#print('saving cache for',path)
	r_tmp = {
		'body': r.body if hasattr(r, 'body') else (r.text if hasattr(r, 'text') else r._body),
		'headers': headers,
		'status': r.status,
	}
	print(r_tmp['headers'])
	cache.website[path] = (time.time(), r_tmp)
	return r

asyncio.ensure_future(update_database_forever())

app = web.Application(middlewares=[content_type_middleware])
app.add_routes(routes)
app.add_routes([web.static('/', 'website')])
web.run_app(app, port=9999)