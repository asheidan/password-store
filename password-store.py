#!/usr/bin/env python3
# -*- coding: UTF-8

import argparse
import configparser
import logging
import os
import subprocess
import sys

from backends import get_backends
from display import display
from matchers import get_matcher

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

### Globals ###################################################################

### Helpers ###################################################################

def set_pbcopy_clipboard(text):
    pbcopy_proc = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
    pbcopy_proc.communicate(text)

def set_xsel_clipboard(text, primary=True, secondary=True, clipboard=True):
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


def parse_configfile(file_name=None):
    """ Parse configuration file and return config
    """
    log = logging.getLogger('parse_configfile')
    defaults = {
        'Global': {
            'directory': '~/.pwstore',
        },
        'Cleartext Backend': {},
        'GPG Backend': {
            'private key': '',
        },
    }
    parser = configparser.SafeConfigParser(default_section='Global')

    parser.read_dict(defaults)

    if file_name is not None:
        try:
            log.info("Reading config file")
            log.debug("Reading %s", file_name)
            with open(file_name, 'r') as config_file:
                parser.readfp(config_file)

        except configparser.MissingSectionHeaderError as error:
            log.error(error)
            sys.exit(2)

        except FileNotFoundError:
            log.warning("Configuration file does not exist")
            try:
                log.info("Creating file with default values")
                with open(file_name, 'w') as config_file:
                    parser.write(config_file)
            except FileNotFoundError:
                log.error("Could not create file")

                sys.exit(1)

    return parser


def parse_commandline():
    """ Parse arguments and return configuration
    """
    log = logging.getLogger('parse_commandline')

    conf_parser = argparse.ArgumentParser(add_help=False)
    conf_parser.add_argument('-c', '--config',
                             default='~/.pwstore/configuration')
    log.debug("Parsing configuration file from args")
    args, remaining_args = conf_parser.parse_known_args()
    args.config = os.path.expanduser(args.config)
    log.debug("Configfile is %s", args.config)

    configuration = parse_configfile(args.config)
    #print(configuration.sections())

    parser = argparse.ArgumentParser(description='Stores information in files.')
    #parser.add_argument('command', metavar='<command>', choices=COMMANDS,
    #                    help="""""")
    #parser.add_argument('args', metavar='<arg>', nargs='*',
    #                    help="""""")
    parser.add_argument('-c', '--config',
                        default='~/.pwstore/configuration',
                        help='which configurationfile to use')

    parser.add_argument('-d', '--directory',
                        default=configuration['Global']['directory'],
                        help=('directory with storage backends (if different '
                              'from default or configuration)'))

    ### Matchers #############################################################
    match_parser = argparse.ArgumentParser(add_help=False)
    matchers = match_parser.add_mutually_exclusive_group()
    matchers.add_argument('-r', '--regexp', help='use regular expression matcher',
                        action='store_true', default=True)
    matchers.add_argument('-t', '--token', help='use token expression matcher',
                        action='store_true', default=False)

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
    list_parser.add_argument('pattern', metavar='<pattern>', help='pattern',
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

        sys.exit(0)

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
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    console.setFormatter(formatter)

    logger.addHandler(console)

    args = parse_commandline()

    if args.command in ['ls', 'list']:
        backends = get_backends(args.directory)
        logger.debug("backends: %s", backends)
        matcher = get_matcher(args, args.pattern)
        logger.debug("pattern: %s", args.pattern)
        for backend in backends:
            for key in backend.list():
                if matcher.matches(key):
                    print(key)
