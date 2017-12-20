# Hosts-monitoring-bot

Allows you to monitor the reach status of the hosts from `list.txt`.

REQUIREMENTS
------------
The minimum requirement is supporting Python 3.5 by your server or PC. Required pip-dependencies are listed in requirements.txt.

QUICK START
-----------
Telegram's bot token stores in TOKEN varaible.

      TOKEN = ''

The monitor is turned on/off **only by the administrator**. So the administrator's id must be specified in LIST_OF_ADMINS varaible. 

      LIST_OF_ADMINS = []

The host's data is filled in the format:

      host_adress host_name

For example, the default data looks like:

      8.8.8.8 Google
      ya.ru Yandex

To run bot use command:

      python3 bot.py

HOW TO USE
-----------
### Monitor start (admin)
To start monitor send `/menu` command to bot and tap inline button `Enable`.

<p align="center"><img src="https://image.ibb.co/eZ2zc6/029.png"></p>

Result:

<p align="center"><img src="https://image.ibb.co/iuti4m/031.png"></p>

### Monitor stop (admin)
To stop monitor use `/menu` command and tap inline button `Disable`.

<p align="center"><img src="https://image.ibb.co/jQhMqR/032.png"></p>

Result:

<p align="center"><img src="https://image.ibb.co/f2aKc6/033.png"></p>

### Logfile (admin)
Use `/log` command to get logfile with event records.

<p align="center"><img src="https://image.ibb.co/kXVwPm/034.png"></p>

### Underwatch
On `/underwatch` command bot shows the list of hosts nad their statuses.

<p align="center"><img src="https://image.ibb.co/g1v2x6/035.png"></p>

### Subscription
Use `/on` and `/off` to enable/disable subscription to event alerts.
>Users with active subscriptions are notified about changes in the status of hosts.

`/status` shows your subscription status.

<p align="center"><img src="https://image.ibb.co/hZrT4m/036.png"></p>

