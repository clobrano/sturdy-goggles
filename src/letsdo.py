#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Usage:
    letsdo [--force] [--time=<time>]      [<name>...]
    letsdo --change <newname>...
    letsdo --keep [--id=<id>] [--time=<time>]
    letsdo --report
    letsdo --report-full
    letsdo --report-daily
    letsdo --stop [--time=<time>]
    letsdo --to             <newtask>...

Notes:
    With no arguments, letsdo start a new task or report the status of the current running task

    -c --change   Rename current running task
    -k --keep     Restart last run task
    -f --force    Start new unnamed task without asking
    -s --stop     Stop current running task
    --to          Switch to a new task
    -t <time> --time=<time>     Suggest the start/stop time of the task
    -r --report
'''

import os
import pickle
import datetime
import time
import docopt
import sys
import logging
import yaml
import re

DATA_FILENAME = ''
TASK_FILENAME = ''

# Logger
level = logging.INFO
logging.basicConfig(level=level, format='  %(message)s')
logger = logging.getLogger(__name__)
info = lambda x: logger.info(x)
err = lambda x: logger.error(x)
warn = lambda x: logger.warn(x)
dbg = lambda x: logger.debug(x)


class Configuration(object):

    def __init__(self):
        conf_file_path = os.path.expanduser(os.path.join('~', '.letsdo'))
        if os.path.exists(conf_file_path):
            configuration = yaml.load(open(conf_file_path).read())
            self.data_filename = os.path.expanduser(os.path.join(configuration['datapath'], '.letsdo-data'))
            self.task_filename = os.path.expanduser(os.path.join(configuration['taskpath'], '.letsdo-task'))
        else:
            dbg('Config file not found. Using default')
            self.data_filename = os.path.expanduser(os.path.join('~', '.letsdo-data'))
            self.task_filename = os.path.expanduser(os.path.join('~', '.letsdo-task'))



class Task(object):
    def __init__(self, name='unknown', start=None, end=None, id=None):
        self.context = None
        self.end_date = None
        self.end_time = None
        self.name = None
        self.start_time = None
        self.tags = None
        self.work_time = None
        self.id = id

        self.parse_name(name.strip())
        if start:
            try:
                self.start_time = datetime.datetime.strptime(start.strip(), '%Y-%m-%d %H:%M:%S.%f')
            except ValueError:
                self.start_time = datetime.datetime.strptime(start.strip(), '%Y-%m-%d %H:%M:%S')
        else:
            self.start_time = datetime.datetime.now()

        if end:
            try:
                self.end_time = datetime.datetime.strptime(end.strip(), '%Y-%m-%d %H:%M:%S.%f')
            except ValueError:
                self.end_time = datetime.datetime.strptime(end.strip(), '%Y-%m-%d %H:%M:%S')
            self.end_date = (self.end_time.strftime('%Y-%m-%d'))
            self.work_time = self.end_time - self.start_time

    @staticmethod
    def get():
        TASK_FILENAME = Configuration().task_filename
        if Task.__is_running():
            with open(TASK_FILENAME, 'r') as f:
                return pickle.load(f)

    @staticmethod
    def stop(stop_time_str=None):
        task = Task.get()
        if task:
            stop_time = datetime.datetime.now()
            if stop_time_str:
                stop_time_date = datetime.datetime.strftime(stop_time, '%Y-%m-%d')
                stop_time = datetime.datetime.strptime(stop_time_date + ' ' + stop_time_str, '%Y-%m-%d %H:%M')

                if stop_time < task.start_time:
                    warn('Given stop time (%s) is more recent than start time (%s)' % (stop_time, task.start_time))
                    return False

            work = stop_time - task.start_time
            status = ('Stopped task \'%s\' after %s of work' % (task.name, work)).split('.')[0]
            info(status)

            date = datetime.date.today()
            if task.tags:
                tags = ' '.join(task.tags)
            else:
                tags = None
            report = '%s,%s,%s,%s,%s\n' % (date, task.name, work, task.start_time, stop_time)
            DATA_FILENAME = Configuration().data_filename
            with open(DATA_FILENAME, mode='a') as f:
                f.writelines(report)

            TASK_FILENAME = Configuration().task_filename
            os.remove(TASK_FILENAME)
            return True
        info('No task running')
        return False

    @staticmethod
    def change(name):
        task = Task.get()
        if task:
            info('Renaming task \'%s\' to \'%s\'' % (task.name, name))
            task.parse_name(name)
            return task.__create()

        warn('No task running')

    @staticmethod
    def status():
        task = Task.get()
        if task:
            now = datetime.datetime.now()
            work = now - task.start_time
            status = ('Working on \'%s\' for %s' % (task.name, work)).split('.')[0]
            info(status)
            return True
        else:
            info('No task running')
            return False

    @staticmethod
    def __is_running():
        TASK_FILENAME = Configuration().task_filename
        exists = os.path.exists(TASK_FILENAME)
        dbg('is it running? %d' % exists)
        return exists

    def start(self):
        if not Task.__is_running():
            if self.__create():
                info('Starting task \'%s\' now' % self.name)
                return Task.get()

            err('Could not create new task')
            return False

        warn('Another task is running')
        return True

    def __create(self):
        TASK_FILENAME = Configuration().task_filename
        with open(TASK_FILENAME, 'w') as f:
            pickle.dump(self, f)
            return True

    def parse_name(self, name):
        name = name.replace(',', ' ')
        self.name = name
        matches = re.findall('@[\w\-_]+', name)
        if len(matches) == 1:
            self.context = matches[0]
        matches = re.findall('\+[\w\-_]+', name)
        if len(matches) >= 1:
            self.tags = matches

    def __repr__(self):
        work_str = '%s' % str(self.work_time).split('.')[0]
        start_str = '%s' % self.start_time.strftime('%H:%M')
        end_str = '%s' % self.end_time.strftime('%H:%M')
        if self.id is not None:
            return '[%d] - %s| %s (%s -> %s) - %s' % (self.id, self.end_date, work_str, start_str, end_str, self.name)
        return '%s| %s (%s -> %s) - %s' % (self.end_date, work_str, start_str, end_str, self.name)

    def __eq__(self, other):
        return self.name == other.name


def keep(start_time_str=None, id=-1):
    tasks = []
    datafilename = Configuration().data_filename
    with open(datafilename) as f:
        lines = f.readlines()
        try:
            line = lines[id]
        except ValueError:
            if id == -1:
                err('Could not find task last task')
            else:
                err('Could not find task with id %d' % id)
            return

        tok = line.split(',')
        task_name = tok[1]

        if start_time_str:
            date_str = datetime.datetime.strftime(datetime.datetime.today(), '%Y-%m-%d')
            start_time = date_str + ' ' + start_time_str + ':0'
        else:
            start_time = None

        Task(task_name, start=start_time).start()


def report_task():
    tasks = []
    datafilename = Configuration().data_filename
    with open(datafilename) as f:
        for line in f.readlines():
            tok = line.split(',')
            task = Task(
                    name=tok[1],
                    start=tok[3],
                    end=tok[4]
                    )
            try:
                index = tasks.index(task)
                same_task = tasks.pop(index)
                task.work_time += same_task.work_time
            except ValueError:
                pass

            tasks.append(task)

    for idx, task in enumerate(tasks):
        work_str = '%s' % str(task.work_time).split('.')[0]
        info('[%d] %s| %s - %s' % (idx, task.end_date, work_str, task.name))


def report_full(filter=None):
    tasks = {}
    with open(DATA_FILENAME) as f:
        for id, line in enumerate(f.readlines()):
            tok = line.split(',')
            task = Task(
                    name=tok[1],
                    start=tok[3],
                    end=tok[4],
                    id=id
                    )
            date = task.end_date
            if date in tasks.keys():
                tasks[date].append(task)
            else:
                tasks[date] = [task]

        dates = sorted(tasks.keys(), reverse=True)
        for date in dates:
            tot_time = datetime.timedelta()
            column = ''
            for task in tasks[date]:
                tot_time += task.work_time

                work_str = '%s' % str(task.work_time).split('.')[0]
                start_str = '%s' % task.start_time.strftime('%H:%M')
                end_str = '%s' % task.end_time.strftime('%H:%M')

                column += '%s| %s (%s -> %s) - %s' % (task.end_date, work_str, start_str, end_str, task.name)
                column += '\n'

            print('===================================')
            print('%s| Total time: %s' % (date, str(tot_time).split('.')[0]))
            print('-----------------------------------')
            print(column)


def report_daily():
    tasks = {}
    with open(DATA_FILENAME) as f:
        for line in f.readlines():
            tok = line.split(',')
            task = Task(
                    name=tok[1],
                    start=tok[3],
                    end=tok[4]
                    )
            date = task.end_date
            if date in tasks.keys():
                try:
                    index = tasks[date].index(task)
                    same_task = tasks[date][index]
                    same_task.work_time += task.work_time
                except ValueError:
                    tasks[date].append(task)
            else:
                tasks[date] = [task]

    dates = sorted(tasks.keys(), reverse=True)
    for date in dates:
        tot_time = datetime.timedelta()
        column = ''
        for task in tasks[date]:
            tot_time += task.work_time
            work_str = '%s' % str(task.work_time).split('.')[0]
            column += '%s| %s - %s' % (task.end_date, work_str, task.name)
            column += '\n'
        print('===================================')
        print('%s| Total time: %s' % (date, str(tot_time).split('.')[0]))
        print('-----------------------------------')
        print(column)



def main():
    # Configuration
    args = docopt.docopt(__doc__)
    dbg(args)

    global DATA_FILENAME
    global TASK_FILENAME
    conf = Configuration()
    DATA_FILENAME = conf.data_filename
    TASK_FILENAME = conf.task_filename

    if args['--stop']:
        Task.stop(args['--time'])

    elif args['--change']:
        new_task_name = ' '.join(args['<newname>'])
        Task.change(new_task_name)

    elif args['--to']:
        Task.stop()
        new_task_name = ' '.join(args['<newtask>'])
        Task(new_task_name).start()

    elif args['--keep']:
        if args['--id']:
            id = eval(args['--id'])
        else:
            id = -1
        keep(start_time_str=args['--time'], id=id)

    elif args['--report']:
        report_task()

    elif args['--report-daily']:
        report_daily()

    elif args['--report-full']:
        report_full()

    else:
        if Task.get():
            Task.status()
            sys.exit(0)
        elif not args['<name>'] and not args['--force']: # Not sure if asking for status or starting an unnamed task
            resp = raw_input('No running task. Let\'s create a new unnamed one [y/n]?: ')
            if resp.lower() != 'y':
                sys.exit(0)
            args['<name>'] = ['unknown']

        new_task_name = ' '.join(args['<name>'])
        Task(new_task_name, start=args['--time']).start()


if __name__ == '__main__':
    main()
