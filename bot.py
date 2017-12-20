import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, Job, MessageHandler, CallbackQueryHandler
from telegram.ext.dispatcher import run_async
import logging

import subprocess
from queue import Queue
import time

from functools import wraps
from datetime import datetime

#admin's functions decorator
def restricted(func):
	@wraps(func)
	def wrapped(bot, update, *args, **kwargs):
		user_id = update.effective_user.id
		if user_id not in LIST_OF_ADMINS:
			logger.info("Unauthorized access denied for {}.".format(user_id))
			return
		return func(bot, update, *args, **kwargs)
	return wrapped

class Monitor(object):
	'''
	Controls monitor, provides interfaces to enable and disable it
	'''
	def __init__(self):
		super(Monitor, self).__init__()
		self.job = updater.job_queue
		self.status = False
	
	#Runs ping_hosts() with required interval
	def start(self):
		self.ping_hosts_job = self.job.run_repeating(ping_hosts, interval=60,  first=0)
		self.status = True
	
	#Stops ping_hosts()
	def stop(self):
		self.job.jobs()[0].schedule_removal()
		self.status = False

	def status_str(self):
		result = 'Monitor is activated' if self.status else 'Monitor is deactivated'
		return result

class Host(object):
	'''
	Represents an instance of host from list.txt.
	Encapsulates host's status, adress and other additional informatin.
	'''
	def __init__(self, addess, name):
		super(Host, self).__init__()
		self.addess = addess
		self.name = name
		self.reachable = 'Unknown'
		self.changed = False
		self.last_activity = ''

	def __str__(self):
		return self.addess

	def reachable_status(self,status):
		if status == 'on':
			self.last_activity == datetime.now().isoformat()
		if status != self.reachable:
			self.reachable = status
			self.changed = True
			text = 'reachable' if status == 'on' else 'not reachable'
			return text

class Hosts(object):
	'''
	Creates host's instanses according to list.txt.
	Stores them in list and makes some typical operations with host's list.
	''' 
	def __init__(self):
		super(Hosts, self).__init__()
		with open('list.txt') as file:
			splited = [i.split() for i in file]
			self.list = {Host(addess, name) for addess, name in splited}
			self.status = "All hosts are reachable!"

	def set_status(self, status):
		self.status = status

	def is_reachable(self, status):
		result = [host for host in self.list if host.reachable == status]
		return result

	def changed_hosts(self):
		result = [host for host in self.list if host.changed == True]
		return result

	def save_changes(self):
		for host in self.list:
			host.changed = False

	def reset_reachable(self):
		for host in self.list:
			host.reachable = 'Unknown'
			host.changed = False

class Subscribers(object):
	'''
	Contains the dict with subscribers and their subscribe's status,
	so some of them will get messages about changes with status of hosts.
	''' 
	def __init__(self):
		super(Subscribers, self).__init__()
		self.subscribers = {}

	def notify_on(self,user_id):
		self.subscribers[user_id] = 'on'

	def notify_off(self,user_id):
		self.subscribers[user_id] = 'off'

	def send_notifies(self, bot, message):
		active_subscribers = [sub for sub in self.subscribers if self.subscribers[sub] == 'on']
		for user_id in active_subscribers:
			echo(bot, message, user_id)

@run_async
def echo(bot, message, chat_id):
	bot.send_message(chat_id=chat_id,text=message)

@run_async
def ping(i, q, bot):
	'''
	Pings host and marks his status
	'''
	time.sleep(i)
	host = q.get()
	#Ping command returns 0 in host is reachable
	answer = subprocess.call("ping -c 1 %s" % host,
						shell=True,
						stdout=open('/dev/null', 'w'),
						stderr=subprocess.STDOUT)
	q.task_done()
	status = 'on' if not answer else 'off'
	host.reachable_status(status)

def ping_hosts(bot, job):
	'''
	Function used by Monitor's instanse in queue.
	Pings all hosts asynchronously.
	'''
	queue = Queue()
	for i in range(1, len(hosts.list)+1):
		ping(i, queue, bot)
	for host in hosts.list:
		queue.put(host)
	queue.join()

	changes = hosts.changed_hosts()
	lost = hosts.is_reachable('off')
	if not changes:
		if not lost:
			message = "All hosts are reachable!"
			logger.info(message)
		else:
			lost_names = ', '.join([host.name for host in lost])
			message = "Not reachable: %s" % lost_names
			logger.info(message)
		hosts.set_status(message)
	else:
		changes_str = []
		changes_to_on = [host.name for host in changes if host.reachable == 'on']
		if changes_to_on:
			changes_to_on_str = 'Reachable: '+', '.join(changes_to_on)
			logger.info(changes_to_on_str)
			changes_str.append(changes_to_on_str)
		changes_to_off = [host.name for host in changes if host.reachable == 'off']
		if changes_to_off:
			changes_to_off_str = 'Lost: '+', '.join(changes_to_off)
			logger.info(changes_to_off_str)
			changes_str.append(changes_to_off_str)
			lost_names = ', '.join([host.name for host in lost])
			message_s = "Not reachable: %s" % lost_names
			hosts.set_status(message_s)
		message = '\n'.join(changes_str)
		subscribers.send_notifies(bot, message)
	hosts.save_changes()

#/meny command's action
@restricted
def menu(bot, update):
	'''
	Inchat telegram command /menu (only for admin!)
	Provides interface to enable/disable monitor.
	'''
	dispatcher = updater.dispatcher
	status, reply_markup = buttons()
	bot.send_message(text='<b>%s</b>' % status, 
		chat_id=update.message.chat_id,
		parse_mode=telegram.ParseMode.HTML,
		reply_markup=reply_markup)

@restricted
def log(bot, update):
	'''
	Inchat telegram command /log (only for admin!)
	Send log file to admin.
	'''
	bot.send_document(chat_id=update.message.chat_id, document=open('history.log', 'rb'))

def on(bot, update):
	'''
	Inchat telegram command /on (only for admin!)
	Enables subscribe to monitor's messages.
	'''
	subscribers.notify_on(update.message.chat_id)
	message = 'Subscribe is on!\n(%s)' % monitor.status_str()
	logger.info('%s subscribed' % update.message.from_user.username)
	echo(bot, message, update.message.chat_id)

def off(bot, update):
	'''
	Inchat telegram command /off (only for admin!)
	Disables subscribe to monitor's messages.
	'''
	subscribers.notify_off(update.message.chat_id)
	message = 'Subscribe is off!\n(%s)' % monitor.status_str()
	logger.info('%s unsubscribed' % update.message.from_user.username)
	echo(bot, message, update.message.chat_id)

def status(bot, update):
	'''
	Inchat telegram command /off (only for admin!)
	Returns status of subscribe to monitor's messages.
	'''
	try:
		check = subscribers.subscribers[update.message.chat_id]		
		notify_status = 'Subscribe is on!' if check =='on' else 'Subscribe is off!'
	except KeyError:
		notify_status = 'Subscribe is off!'
	message = '%s\n(%s)' % (notify_status, monitor.status_str())
	logger.info('%s checkes subscribe status' % update.message.from_user.username)
	echo(bot, message, update.message.chat_id)

#Inline buttons menu
def underwatch(bot, update):
	hosts_list = [host for host in hosts.list]
	hosts_list.sort(key=lambda x: x.name)
	x = []
	states = {'Unknown':'💤', 'on':'✅', 'off':'🆘'}
	x = [states[h.reachable]+h.name+' '+h.last_activity for h in hosts_list]
	hosts_list_str = '\n'.join(x)
	message = 'Monitoring list:\n' + hosts_list_str
	echo(bot, message, update.message.chat_id)

#Inline buttons menu
def button(bot, update):
	query = update.callback_query
	if query.data == 'disable':
		monitor.stop()
		status = 'Monitor is deactivated'
		hosts.reset_reachable()
	else:
		monitor.start()
		status = 'Monitor is activated'
	logger.info(status)
	bot.edit_message_text(text='<b>%s</b>' % status,
			chat_id=query.message.chat_id,
			parse_mode=telegram.ParseMode.HTML,
			message_id=query.message.message_id)

def buttons():
	if monitor.status:
		status = 'Monitor is activated'
		keyboard = [
		[InlineKeyboardButton("Disable ⛔️", callback_data='disable')
		]]
		reply_markup = InlineKeyboardMarkup(keyboard)
	else:
		status = 'Monitor is deactivated'
		keyboard = [
		[InlineKeyboardButton("Enable ✅", callback_data='enable')
		]]
		reply_markup = InlineKeyboardMarkup(keyboard)
	return status, reply_markup

def error(bot, update, error):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, error)

if __name__ == '__main__':
	LIST_OF_ADMINS = []
	TOKEN = ''
	#Logging setup
	logging.basicConfig(filename='history.log',
		format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
		level=logging.INFO)
	logger = logging.getLogger(__name__)
	#Controls user'notify
	subscribers = Subscribers()
	#Hosts list creating
	hosts = Hosts()
	# Create the Updater and pass it your bot's token.
	updater = Updater(token=TOKEN)
	#Queue with hosts_ping
	monitor = Monitor()
	#Handlers adding
	updater.dispatcher.add_handler(CommandHandler('menu', menu))
	updater.dispatcher.add_handler(CommandHandler('log', log))
	updater.dispatcher.add_handler(CommandHandler('on', on))
	updater.dispatcher.add_handler(CommandHandler('off', off))
	updater.dispatcher.add_handler(CommandHandler('status', status))
	updater.dispatcher.add_handler(CommandHandler('underwatch', underwatch))
	updater.dispatcher.add_handler(CallbackQueryHandler(button))
	updater.dispatcher.add_error_handler(error)
	# Start the Bot
	updater.start_polling()
	# Run the bot until the user presses Ctrl-C or the process receives SIGINT,
	# SIGTERM or SIGABRT
	updater.idle()

	
	
