#!/usr/bin/env python
# encoding: utf-8
#
# Description: Bot for controlling  Bristol on Telegram
# Author: Pablo Iranzo Gomez (Pablo.Iranzo@gmail.com)
#
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.    See the
# GNU General Public License for more details.

import optparse
import json
import urllib
import sqlite3 as lite
import sys
import time
import datetime
from time import sleep

description = """
Bristol is a script for controlling entries via Telegram.org bot api

"""

# Option parsing
p = optparse.OptionParser("bristol.py [arguments]", description=description)
p.add_option("-t", "--token", dest="token",
             help="API token for bot access to messages", default=None)
p.add_option("-b", "--database", dest="database",
             help="database file for storing data and last processed message",
             default="bristol.db")
p.add_option('-v', "--verbosity", dest="verbosity",
             help="Show messages while running", metavar='[0-n]', default=0,
             type='int')
p.add_option('-u', "--url", dest="url",
             help="Define URL for accessing bot API",
             default="https://api.telegram.org/bot")
p.add_option('-o', '--owner', dest='owner',
             help="Define owner username for monitoring service", default="iranzo")
p.add_option('-d', '--daemon', dest='daemon', help="Run as daemon",
             default=False, action="store_true")

(options, args) = p.parse_args()


# Implement switch from http://code.activestate.com/recipes/410692/


class Switch(object):
    def __init__(self, value):
        self.value = value
        self.fall = False

    def __iter__(self):
        """Return the match method once, then stop"""
        yield self.match
        raise StopIteration

    def match(self, *args):
        """Indicate whether or not to enter a case suite"""
        if self.fall or not args:
            return True
        elif self.value in args:  # changed for v1.5, see below
            self.fall = True
            return True
        else:
            return False


def createdb():
    # Create database if it doesn't exist
    cur.execute('CREATE TABLE config(key TEXT, value TEXT);')
    cur.execute('CREATE TABLE stats(type TEXT, id INT, name TEXT, date TEXT, count INT);')
    cur.execute('CREATE TABLE bristol(id INT, date TEXT, usedtime INT, type INT, comment TEXT);')
    cur.execute('CREATE TABLE status(id INT, status INT);')
    return


# Initialize database access
con = None
try:
    con = lite.connect(options.database)
    cur = con.cursor()
    cur.execute("SELECT * FROM config WHERE key='token';")
    data = cur.fetchone()

except lite.Error, e:
    createdb()
    print "Error %s:" % e.args[0]
    sys.exit(1)


# Database initialized


# Function definition
def sendmessage(chat_id=0, text="", reply_to_message_id=None,
                disable_web_page_preview=True, extra=False):
    url = "%s%s/sendMessage" % (config(key='url'), config(key='token'))
    message = "%s?chat_id=%s&text=%s" % (url, chat_id,
                                         urllib.quote_plus(text.encode('utf8'))
                                         )
    if reply_to_message_id:
        message += "&reply_to_message_id=%s" % reply_to_message_id
    if disable_web_page_preview:
        message += "&disable_web_page_preview=1"
    if extra:
        message += "&%s" % extra
    log(facility="sendmessage", verbosity=3,
        text="Sending message: %s" % text)
    return json.load(urllib.urlopen(message))


def getupdates(offset=0, limit=100):
    url = "%s%s/getUpdates" % (config(key='url'), config(key='token'))
    message = "%s?" % url
    if offset != 0:
        message += "offset=%s&" % offset
    message += "limit=%s" % limit
    try:
        result = json.load(urllib.urlopen(message))['result']
    except:
        result = []
    for item in result:
        log(facility="getupdates", verbosity=9,
            text="Getting updates and returning: %s" % item)
        yield item


def clearupdates(offset):
    url = "%s%s/getUpdates" % (config(key='url'), config(key='token'))
    message = "%s?" % url
    message += "offset=%s&" % offset
    try:
        result = json.load(urllib.urlopen(message))
    except:
        result = None
    log(facility="clearupdates", verbosity=9, text="Clearing messages")
    return result


def config(key):
    string = (key,)
    sql = "SELECT * FROM config WHERE key='%s';" % string
    cur.execute(sql)
    value = cur.fetchone()

    try:
        # Get value from SQL query
        value = value[1]

    except:
        # Value didn't exist before, return 0
        value = False

    return value


def status(id=0, state=False):
    log(facility="status", verbosity=9, text="status: %s=%s" % (id, state))
    value = False
    if state:
        if status(id=id):
            sql = "UPDATE status SET status='%s' WHERE id='%s';" % (state, id)
            cur.execute(sql)
            log(facility="status", verbosity=9, text="status: %s=%s" % (id, state))
            con.commit()
        else:
            sql = "INSERT INTO status VALUES('%s','%s');" % (id, status)
            cur.execute(sql)
            log(facility="status", verbosity=9, text="status: %s=%s" % (id, state))
            con.commit()
    else:
        string = (id,)
        sql = "SELECT * FROM status WHERE id='%s';" % string
        cur.execute(sql)
        value = cur.fetchone()

        try:
            # Get value from SQL query
            value = value[1]

        except:
            # Value didn't exist before, return 0
            value = False

    return value


def saveconfig(key, value):
    if value:
        sql = "UPDATE config SET value = '%s' WHERE key = '%s';" % (value, key)
        cur.execute(sql)
        con.commit()
    return value


def getstats(type=None, id=0, name=None, date=None, count=0):
    sql = "SELECT * FROM stats WHERE id='%s' AND type='%s';" % (id, type)
    cur.execute(sql)

    try:
        value = cur.fetchone()
    except:
        value = False

    if value:
        (type, id, name, date, count) = value
    log(facility="getstats", verbosity=9, text="value")
    return value


def updatestats(type=None, id=0, name=None, date=None, count=0):
    try:
        value = getstats(type=type, id=id)
        count = value[4] + 1
        old_id = value[1]
    except:
        value = False
        old_id = False

    # Asume value doesn't exist, then set to update if it does
    sql = "INSERT INTO stats VALUES ('%s', '%s', '%s', '%s', '%s');" % (type, id, name, date, count)

    if old_id != 0 and type:
        sql = "UPDATE stats SET type='%s', name='%s', date='%s', count='%s'  WHERE id = '%s';" % (
            type, name, date, count, id)
    log(facility="updatestats", verbosity=9, text="value")
    cur.execute(sql)
    return con.commit()


def bristolcommands(texto, chat_id, message_id, who_id):
    # Process lines for commands in the first word of the line (Telegram)
    word = texto.split()[0]
    commandtext = None
    extra = False
    for case in Switch(word):
        if case('/add'):
            status(id=who_id, state=1)
            commandtext = "We'll be start asking some questions to store the new entry, write /cancel at anytime to stop it"
            break
            
        if case('/cancel'):
            status(id=who_id, state=-1)
            reply_markup = json.dumps(dict(hide_keyboard=True))
            extra = "reply_markup=%s" % reply_markup
            commandtext = "Cancelling any onging data input"
            break
            
        if case():
            print "GENERIC CASE"
            commandtext = False

    # If any of above commands did match, send command
    if commandtext:
        sendmessage(chat_id=chat_id, text=commandtext, reply_to_message_id=message_id, extra=extra)
        log(facility="bristol", verbosity=9, text="Command: %s" % word)

    if status(id=who_id) > 0:
        print "STATUS OVER 0"
        # We're in the middle of data entry, so process next step.
        # cur.execute('CREATE TABLE bristol(id INT, date TEXT, usedtime INT, type INT, comment TEXT);')
        # 1 - Input date
        # 2 - Store date
        # 3 - Input lenght
        # 4 - Store lenght
        # 5 - Input type
        # 6 - Store type
        # 7 - Input comment
        # 8 - Store comment
        # 9 - Store all date

        print "STATUS IS %s" % status(id=who_id)
        
        if status(id=who_id) == 1:
            log(facility="bristol", verbosity=9, text="Status 1: %s" % word)
            json_keyboard = json.dumps({'keyboard': [["now"], ["other"]],
                                        'one_time_keyboard': True,
                                        'resize_keyboard': True})
            extra = "reply_markup=%s" % json_keyboard
            text = "When did it happened?"
            sendmessage(chat_id=chat_id, reply_to_message_id=message_id, extra=extra, text=text)
            status(id=who_id, state=2)
        
        if status(id_who_id) == 2:
            if 'now' in texto:
                date = time.time()
            else if:
                print "DATE NOT NOW"

        if status(id=who_id) == 3:
            log(facility="bristol", verbosity=9, text="Status 3: %s" % word)
            json_keyboard = json.dumps({'keyboard': [["1"], ["2"], ["3"], ["4"], ["5"], ["6"], ["7"], ["8"], ["9"]],
                                        'one_time_keyboard': True,
                                        'resize_keyboard': True})
            extra = "reply_markup=%s" % json_keyboard
            text = "How long did it took?"
            sendmessage(chat_id=chat_id, reply_to_message_id=message_id, extra=extra, text=text)
            status(id=who_id, state=4)

        if status(id) == 5:
            log(facility="bristol", verbosity=9, text="Status 5: %s" % word)
            json_keyboard = json.dumps({'keyboard': [["1"], ["2"], ["3"], ["4"], ["5"], ["6"], ["7"]],
                                        'one_time_keyboard': True,
                                        'resize_keyboard': True})
            extra = "reply_markup=%s" % json_keyboard
            text = "How long did it took?"
            sendmessage(chat_id=chat_id, reply_to_message_id=message_id, extra=extra, text=text)
            status(id=who_id, state=6)

    return


def bristol(who_id=False, date=False, usedtime=False, type=False, comment=False):
    # Process the storing of data or updating the data already existing
    #  cur.execute('CREATE TABLE bristol(id INT, date TEXT, usedtime INT, type INT, comment TEXT);')

    log(facility="bristol", verbosity=9, text="Who: %s, date: %s, usedtime %s, type %s, comment: %s"  " % ( who_id, date,usedtime, type, comment))
      
    value = False
    
    
    # FIXME Use function for storing/retrieving values, so it can be used to incrementally update a record
    if state:
        if status(id=id):
            sql = "UPDATE status SET status='%s' WHERE id='%s';" % (state, id)
            cur.execute(sql)
            log(facility="bristol", verbosity=9, text="status: %s=%s" % (id, state))
            con.commit()
        else:
            sql = "INSERT INTO status VALUES('%s','%s');" % (id, status)
            cur.execute(sql)
            log(facility="bristol", verbosity=9, text="status: %s=%s" % (id, state))
            con.commit()
    else:
        string = (id,)
        sql = "SELECT * FROM status WHERE id='%s';" % string
        cur.execute(sql)
        value = cur.fetchone()

        try:
            # Get value from SQL query
            value = value[1]

        except:
            # Value didn't exist before, return 0
            value = False

    return value    
    


def telegramcommands(texto, chat_id, message_id, who_un):
    # Process lines for commands in the first word of the line (Telegram)
    word = texto.split()[0]
    commandtext = None
    for case in Switch(word):
        if case('/help'):
            commandtext = "This bot tracks entries with date and bristol type \n\n"
            commandtext += "Learn more about this bot in https://github.com/iranzo/cagolin"
            break
        if case('/start'):
            commandtext = "This bot does not use start or stop commands"
            break
        if case('/stop'):
            commandtext = "This bot does not use start or stop commands"
            break
        if case('/config'):
            configcommands(texto, chat_id, message_id, who_un)
            break
        if case('/stats'):
            statscommands(texto, chat_id, message_id, who_un)
            break
        if case():
            commandtext = None

    # If any of above commands did match, send command
    if commandtext:
        sendmessage(chat_id=chat_id, text=commandtext,
                    reply_to_message_id=message_id)
        log(facility="commands", verbosity=9,
            text="Command: %s" % word)
    return


def setconfig(key, value):
    if config(key=key):
        deleteconfig(key)
    sql = "INSERT INTO config VALUES('%s','%s');" % (key, value)
    cur.execute(sql)
    log(facility="config", verbosity=9, text="setconfig: %s=%s" % (key, value))
    return con.commit()


def deleteconfig(word):
    sql = "DELETE FROM config WHERE key='%s';" % word
    cur.execute(sql)
    log(facility="config", verbosity=9, text="rmconfig: %s" % word)
    return con.commit()


def showconfig(key=False):
    if key:
        # if word is provided, return the config for that key
        string = (key,)
        sql = "SELECT * FROM config WHERE key='%s';" % string
        cur.execute(sql)
        value = cur.fetchone()

        try:
            # Get value from SQL query
            value = value[1]

        except:
            # Value didn't exist before, return 0 value
            value = 0
        text = "%s has a value of %s" % (key, value)

    else:
        sql = "select * from config ORDER BY key DESC;"

        text = "Defined configurations:\n"
        line = 0
        for item in cur.execute(sql):
            try:
                value = item[1]
                key = item[0]
                line += 1
                text += "%s. %s (%s)\n" % (line, key, value)
            except:
                continue
    log(facility="config", verbosity=9,
        text="Returning config %s for key %s" % (text, key))
    return text


def configcommands(texto, chat_id, message_id, who_un):
    log(facility="config", verbosity=9,
        text="Command: %s by %s" % (texto, who_un))
    if who_un == config('owner'):
        log(facility="config", verbosity=9,
            text="Command: %s by %s" % (texto, who_un))
        command = texto.split(' ')[1]
        try:
            word = texto.split(' ')[2]
        except:
            word = ""

        for case in Switch(command):
            if case('show'):
                text = showconfig(word)
                sendmessage(chat_id=chat_id, text=text, reply_to_message_id=message_id, disable_web_page_preview=True)
                break
            if case('delete'):
                key = word
                text = "Deleting config for %s" % key
                sendmessage(chat_id=chat_id, text=text, reply_to_message_id=message_id, disable_web_page_preview=True)
                deleteconfig(word=key)
                break
            if case('set'):
                word = texto.split(' ')[2]
                if "=" in word:
                    key = word.split('=')[0]
                    value = word.split('=')[1]
                    setconfig(key=key, value=value)
                    text = "Setting config for %s to %s" % (key, value)
                    sendmessage(chat_id=chat_id, text=text, reply_to_message_id=message_id,
                                disable_web_page_preview=True)
                break
            if case():
                break

    return


def showstats(type=False):
    if type:
        sql = "select * from stats WHERE type='%s' ORDER BY type DESC;" % type
    else:
        sql = "select * from stats ORDER BY type DESC;"

    text = "Defined stats:\n"
    line = 0
    for item in cur.execute(sql):
        try:
            (type, id, name, date, count) = item
            line += 1
            datefor = datetime.datetime.fromtimestamp(int(date)).strftime('%Y-%m-%d %H:%M:%S')
            text += "%s. Type: %s ID: %s(%s) Date: %s Count: %s\n" % (line, type, id, name, datefor, count)
        except:
            continue
    log(facility="stats", verbosity=9,
        text="Returning stats %s for type %s" % (text, type))
    return text


def statscommands(texto, chat_id, message_id, who_un):
    log(facility="stats", verbosity=9,
        text="Command: %s by %s" % (texto, who_un))
    if who_un == config('owner'):
        log(facility="stats", verbosity=9,
            text="Command: %s by %s" % (texto, who_un))
        command = texto.split(' ')[1]
        try:
            key = texto.split(' ')[2]
        except:
            key = ""

        for case in Switch(command):
            if case('show'):
                text = showstats(key)
                sendmessage(chat_id=chat_id, text=text, reply_to_message_id=message_id, disable_web_page_preview=True)
                break
            if case():
                break

    return


def log(facility=config(key='database'), severity="INFO", verbosity=0, text=""):
    when = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')
    if config('verbosity') >= verbosity:
        print "%s %s : %s : %s : %s" % (when, config(key='database'), facility, severity, text)
    return


def process():
    # Main code for processing the updates
    date = 0
    lastupdateid = 0
    log(facility="main", verbosity=0,
        text="Initial message at %s" % date)
    texto = ""
    error = False
    count = 0

    # Process each message available in URL and search for operators
    for message in getupdates():
        # Count messages in each batch
        count += 1
        update_id = message['update_id']

        try:
            chat_id = message['message']['chat']['id']
        except:
            chat_id = False

        try:
            chat_name = message['message']['chat']['title']
        except:
            chat_name = False

        try:
            texto = message['message']['text']
            message_id = int(message['message']['message_id'])
            date = int(float(message['message']['date']))
            who_gn = message['message']['from']['first_name']
            who_id = message['message']['from']['id']

        except:
            error = True
            who_id = False
            who_gn = False
            date = False
            message_id = False
            texto = False

        try:
            who_ln = message['message']['from']['last_name']
        except:
            who_ln = None

        # Some user might not have username defined so this
        # was failing and message was ignored
        try:
            who_un = message['message']['from']['username']

        except:
            who_un = None

        # Update stats on the message being processed
        if chat_id:
            updatestats(type="chat", id=chat_id, name=chat_name, date=date, count=0)
        if who_ln:
            name = "%s %s (@%s)" % (who_gn, who_ln, who_un)
            updatestats(type="user", id=who_id, name=name, date=date, count=0)

        # Update last message id to later clear it from the server
        if update_id > lastupdateid:
            lastupdateid = update_id

        # Search for telegram commands
        telegramcommands(texto, chat_id, message_id, who_un)

        # Search for bristol commands
        bristolcommands(texto, chat_id, message_id, who_id)

    log(facility="main", verbosity=0,
        text="Last processed message at: %s" % date)
    log(facility="main", verbosity=0,
        text="Last processed update_id : %s" % lastupdateid)
    log(facility="main", verbosity=0,
        text="Last processed text: %s" % texto)
    log(facility="main", verbosity=0,
        text="Number of messages in this batch: %s" % count)

    # clear updates (marking messages as read)
    clearupdates(offset=lastupdateid + 1)


# Main code

# Set database name in config
if options.database:
    setconfig(key='database', value=options.database)

if not config(key='sleep'):
    setconfig(key='sleep', value=2)

# Check if we've the token required to access or exit
if not config(key='token'):
    if options.token:
        token = options.token
        setconfig(key='token', value=token)
    else:
        log(facility="main", severity="ERROR", verbosity=0,
            text="Token required for operation, please check https://core.telegram.org/bots")
        sys.exit(1)
else:
    token = config(key='token')

# Check if we've URL defined on DB or on cli and store
if not config(key='url'):
    if options.url:
        setconfig(key='url', value=options.url)

# Check if we've owner defined in DB or on cli and store
if not config(key='owner'):
    if options.owner:
        setconfig(key='owner', value=options.owner)

    # Check operation mode and call process as required
if options.daemon or config(key='daemon'):
    setconfig(key='daemon', value=True)
    log(facility="main", verbosity=0, text="Running in daemon mode")
    while 1 > 0:
        process()
        sleep(int(config(key='sleep')))
else:
    log(facility="main", verbosity=0,
        text="Running in one-shoot mode")
    process()

# Close database
if con:
    con.close()
