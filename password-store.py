#!/usr/bin/env python
# -*- coding: UTF-8

import argparse
import ConfigParser
import os
import re
import subprocess
import sys

### Backends ##################################################################

class BaseBackend(object):

    def __init__(self, root_folder, config):
        self.root = root_folder
        self.config = config


class ClearTextBackend(BaseBackend):

    ignore_chars = "\t\r\n"

    def __init__(self, root_folder, config):
        super(ClearTextBackend, self).__init__(root_folder, config)

    def list(self):
        """ Returns an iterator for all the keys for this storage """
        walker = os.walk(self.root, followlinks=True)
        for path, subs, files in walker:
            for file in files:
                yield os.path.join(path, file)

    def get_password(self, key):
        """ Returns the password (first line) for the given key """
        password = None
        with open(key, 'r') as file:
            password = file.readline().rstrip(self.ignore_chars)
        
        return password

    def get_entry(self, key):
        """ Returns the entry for the given key """
        with open(key, 'r') as file:
            return file.read()

    def create(self, key):
        content = sys.stdin.read()
        with open(os.path.join(self.root, key)) as file:
            file.write(content)

    def display(self, matcher=None, subdir=None):
        keys = []
        for key in self.list():
            if matcher and matcher.matches(key):
                keys.append(key)
        display_keys(keys)


class GPGBackend(ClearTextBackend):

    def __init__(self, root_folder, config):
        super(GPGBackend, self).__init__(root_folder, config)

        print(repr(config.get('gpg', 'keys')))


### Matchers ##################################################################

class BaseMatcher(object):
    pass


class RegexpMatcher(BaseMatcher):

    def __init__(self, reg_string, flags=re.IGNORECASE):
        self.regexp = re.compile(reg_string, flags=flags)

    def matches(self, string):
        return self.regexp.search(string)


### Globals ###################################################################

BACKENDS = set()
CONFIG_FILE_NAME = "storage.conf"
COMMANDS = [
    'create'
]

### Helpers ###################################################################

def set_clipboard(text, primary=True, secondary=True, clipboard=True):
    if primary:
        xsel_proc = subprocess.Popen(['xsel', '-pi'], stdin=subprocess.PIPE)
        xsel_proc.communicate(text)

    if secondary:
        xsel_proc = subprocess.Popen(['xsel', '-si'], stdin=subprocess.PIPE)
        xsel_proc.communicate(text)

    if clipboard:
        xsel_proc = subprocess.Popen(['xsel', '-bi'], stdin=subprocess.PIPE)
        xsel_proc.communicate(text)


def padding(lvl):
    if lvl == 0:
        return ''
    else:
        return "   " * lvl


def display_keys(key_list):
    keys = sorted(key_list)
    parents = []
    for key in keys:
        parts = key.split('/')
        while parents != parts[:len(parents)]:
            parents.pop()
        for i in xrange(len(parents),len(parts)):
            print("%s%s:" % (padding(len(parents)), parts[i]))
            parents.append(parts[i])

def backends():
    backends = []

    walker = os.walk('storage', followlinks=True)

    for path, subdirs, files in walker:
        if CONFIG_FILE_NAME in files:
            del subdirs[:]

            print path, "is a backend"

            config_file = os.path.join(path, CONFIG_FILE_NAME)
            config = ConfigParser.SafeConfigParser()
            config.read(config_file)

            backend_type = config.get('backend', 'type')
            if backend_type == 'cleartext':
                backends.append(ClearTextBackend(path, config))
            elif backend_type == 'gpg':
                backends.append(GPGBackend(path, config))

    return backends


def parse_commandline():
    parser = argparse.ArgumentParser(description='Stores information in files.')
    #parser.add_argument('command', metavar='<command>', choices=COMMANDS,
    #                    help="""""")
    #parser.add_argument('args', metavar='<arg>', nargs='*',
    #                    help="""""")

    ### Matchers #############################################################
    match_parser = argparse.ArgumentParser(add_help=False)
    matchers = match_parser.add_mutually_exclusive_group()
    matchers.add_argument('-r', '--regexp', help='use regular expression matcher',
                        action='store_true', default=True)
    matchers.add_argument('-t', '--token', help='use token expression matcher',
                        action='store_true', default=True)

    ### Subparsers ###########################################################
    subparsers = parser.add_subparsers(dest='command',
            title='subcommands', description='valid subcommands')

    ###### Create ############################################################
    create_parser = subparsers.add_parser(
            'create', help='create a new entry',
            description='create a new entry for the given <key>')
    create_parser.add_argument('key', metavar='<key>', help="key for the new entry")

    ###### Get ###############################################################
    get_parser = subparsers.add_parser(
            'get', help='get password (first line) from an entry',
            description='get the password (first line) from an entry described by <pattern>',
            parents=[match_parser])
    get_parser.add_argument('pattern', metavar='<pattern>', help="pattern for the wanted entry")

    ###### Show ##############################################################
    show_parser = subparsers.add_parser(
            'show', help='show an entry',
            description='show the entry described by <pattern>',
            parents=[match_parser])
    show_parser.add_argument('pattern', metavar='<pattern>', help="pattern for the wanted entry")

    ###### Help ##############################################################
    help_parser = subparsers.add_parser('help', help='show help')
    help_parser.add_argument('help_command', metavar='command', nargs='?')

    #print(subparsers.choices)

    args = parser.parse_args()
    if 'help' == args.command:
        if args.help_command is None:
            parser.print_help()
        else:
            subparsers.choices.get(args.help_command, parser).print_help()

    return args


def create():
    pass


###############################################################################

if '__main__' == __name__:
    args = parse_commandline()

