#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Usage:
    letsdo [<name>]
    letsdo --rename <newname>
    letsdo --report
    letsdo --status
    letsdo --stop
    letsdo --to    <newtask>

Notes:
    --stop          Stop current running task
    -r --rename     Rename current running task
    -s --status     Get info about the current running task
    -t --to         Switch task
'''

import os
import pickle
import datetime
import time
import docopt
import sys
import logging

# Configuration
DATA_FILENAME = os.path.expanduser(os.path.join('~', '.letsdo-data'))
TASK_FILENAME = os.path.expanduser(os.path.join('~', '.letsdo-task'))
args = docopt.docopt(__doc__)

# Logger
level = logging.INFO
logging.basicConfig(level=level, format='  %(message)s')
logger = logging.getLogger(__name__)
info = lambda x: logger.info(x)
err = lambda x: logger.error(x)
warn = lambda x: logger.warn(x)
dbg = lambda x: logger.debug(x)

dbg(args)

def get_data():
    if os.path.exists(TASK_FILENAME):
        with open(TASK_FILENAME, 'r') as f:
            return pickle.load(f)
    warn('No task is running')


def save_data(data):
   with open(TASK_FILENAME, 'w') as f:
        pickle.dump(data, f)


def start(name):
    if os.path.exists(TASK_FILENAME):
        warn('Another task is running!')
    else:
        now = datetime.datetime.now()
        save_data({'time': now, 'name': name})
        info('Starting task \'%s\' now' % name)


def stop():
    task = get_data()
    if task:
        os.remove(TASK_FILENAME)

        now = datetime.datetime.now()
        work = now - task['time']
        status = ('Stopped task \'%s\' after %s of work' % (task['name'], work)).split('.')[0]
        info(status)

        date = datetime.date.today()
        report = '%s,%s,%s\n' % (date, task['name'], work)
        with open(DATA_FILENAME, mode='a') as f:
            f.writelines(report)


def report():
    report = {}
    with open(DATA_FILENAME) as f:
        for line in f.readlines():
            entry = line.split(',')
            date = entry[0]
            name = entry[1]
            wtime_str = entry[2].split('.')[0].strip()
            wtime_date = datetime.datetime.strptime(wtime_str, '%H:%M:%S')
            wtime = datetime.timedelta(
                    hours=wtime_date.hour,
                    minutes=wtime_date.minute,
                    seconds=wtime_date.second)

            if date not in report.keys():
                report[date] = {name: wtime}
            else:
                if name not in report[date].keys():
                    report[date][name] = wtime
                else:
                    report[date][name] += wtime

    dates = sorted(report.keys(), reverse=True)
    for date in dates:
        entry = report[date]
        tot_time = datetime.timedelta()
        column = ''
        for name, wtime in entry.items():
            tot_time += wtime
            column += ('%s| %s\n' % (date, (str(wtime) + ' - ' + name)))
        print('===================================')
        print('%s| Total time: %s' % (date, tot_time))
        print('-----------------------------------')
        print(column)


def status():
    data = get_data()
    if data:
        now = datetime.datetime.now()
        work = now - data['time']
        status = ('Working on \'%s\' for %s' % (data['name'], work)).split('.')[0]
        info(status)


def rename(name):
    data = get_data()
    if data:
        info('Renaming task \'%s\' to \'%s\'' % (data['name'], name))
        data['name'] = name
        save_data(data)

def main():
    if args['--stop']:
        stop()
    elif args['--status']:
        status()
    elif args['--rename']:
        rename(args['<newname>'])
    elif args['--to']:
        stop()
        start(args['<newtask>'])
    elif args['--report']:
        report()
    else:
        if args['<name>'] is None:
            args['<name>'] = 'unknown'
        start(args['<name>'])


if __name__ == '__main__':
    main()
