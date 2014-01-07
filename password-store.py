#!/usr/bin/env python3
# -*- coding: UTF-8

import argparse
import configparser
import os
import re
import subprocess
import sys

class Colorizer(object):

    red = 91
    green = 92
    yellow = 93
    blue = 94

    def color(self, code=0):
        return "\033[%dm" % code

    def colorize(self, string, color_code):
        return self.color(color_code) + string + self.color()

    def directory(self, string):
        return self.colorize(string, self.blue)

color = Colorizer()

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


class GPGBackend(ClearTextBackend):

    import gnupg
    gpg = gnupg.GPG(use_agent=True)

    def __init__(self, root_folder, config):
        super(GPGBackend, self).__init__(root_folder, config)

        self.key_names = set(config.get('gpg', 'keys').split('\n'))
        self.keys = list()
        for key in self.gpg.list_keys():
            for uid in key.get('uids', []):
                if uid in self.key_names:
                    self.keys.append(key)
                    continue

    def encrypt(self, data):
        if len(self.keys) != len(self.key_names):
            raise ValueError('Missing keys in keychain')
        keys = [k['keyid'] for k in self.keys]
        encrypted_data = self.gpg.encrypt(keys, data)

    def decrypt(self, data):
        decrypted_data = self.gpg.decrypt(data)


### Matchers ##################################################################

class BaseMatcher(object):
    pass


class RegexpMatcher(BaseMatcher):

    def __init__(self, reg_string, flags=re.IGNORECASE):
        self.regexp = re.compile(reg_string, flags=flags)

    def matches(self, string):
        return self.regexp.search(string)


### Globals ###################################################################

CONFIG_FILE_NAME = "storage.conf"

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

            config_file = os.path.join(path, CONFIG_FILE_NAME)
            config = configparser.SafeConfigParser()
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
            description='''Create a new entry for the given <key> in an existing
                           backend''')
    create_parser.add_argument('key', metavar='<key>', help="key for the new entry")

    ###### Get ###############################################################
    get_parser = subparsers.add_parser(
            'get', aliases=['g'], help='get password (first line) from an entry',
            description='Get the password (first line) from an entry described by <pattern>',
            parents=[match_parser])
    get_parser.add_argument('pattern', metavar='<pattern>', help="pattern for the wanted entry")

    ###### Show ##############################################################
    show_parser = subparsers.add_parser(
            'show', aliases=['sh'], help='show an entry',
            description='show the entry described by <pattern>',
            parents=[match_parser])
    show_parser.add_argument('pattern', metavar='<pattern>', help="pattern for the wanted entry")

    ###### List ##############################################################
    list_parser = subparsers.add_parser(
            'list', aliases=['ls'], help='list keys',
            description='show keys matching <pattern> (or all)',
            parents=[match_parser])
    list_parser.add_argument('pattern', metavar='<pattern>', help='patthern',
            nargs='?')
    ###### Help ##############################################################
    help_parser = subparsers.add_parser('help', help='show help')
    help_parser.add_argument('help_command', metavar='command', nargs='?')

    args = parser.parse_args()
    if 'help' == args.command:
        if args.help_command is None:
            parser.print_help()
        else:
            subparsers.choices.get(args.help_command, parser).print_help()

    return args


def create():
    pass


def pad_sub(line, last=False):
    if not last:
        return "\u2502   " + line
    else:
        return "    " + line

def pad_this(line, last=False):
    if not last:
        return "\u251C\u2500\u2500 " + line
    else:
        return "\u2514\u2500\u2500 " + line


def display_directory(directory, matcher=None):
    rows = []
    walker = os.walk(directory, followlinks=True)
    path, subs, files = next(walker)
    if CONFIG_FILE_NAME in files:
        files.remove(CONFIG_FILE_NAME)
        #rows.append("\u2502 Backend")

    for i, subdir in enumerate(sorted(subs)):
        is_last = len(files) == 0 and i >= len(subs) - 1
        walk_root = os.path.join(directory, subdir)
        rows.append(pad_this(color.directory(subdir), is_last))
        subdir_data = display_directory(walk_root, matcher)
        for data_line in subdir_data:
            rows.append(pad_sub(data_line, is_last))

    for i, file in enumerate(sorted(files)):
        is_last = i >= len(files) - 1
        rows.append(pad_this(file, is_last))

    return rows


def display(directory, matcher=None):
    import locale
    locale.setlocale(locale.LC_ALL, '')
    code = locale.getpreferredencoding()

    #print(code)

    print(directory)
    print("\n".join(display_directory(directory, matcher)))


###############################################################################

if '__main__' == __name__:
    args = parse_commandline()

    
    if 'list' == args.command:
        display('storage')

