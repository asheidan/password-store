#!/usr/bin/env python3
# -*- coding: UTF-8

import argparse
import configparser
import logging
import os
import subprocess
import sys

from backends import get_backends
from display import Output
from matchers import get_matcher

log = logging.getLogger(__name__)

# Globals #####################################################################

# Helpers #####################################################################


def set_pbcopy_clipboard(text):
    pbcopy_proc = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
    pbcopy_proc.communicate(bytes(text, encoding="UTF-8"))


def set_xsel_clipboard(text, primary=True, secondary=True, clipboard=True):
    if primary:
        xsel_proc = subprocess.Popen(['xsel', '-pi'], stdin=subprocess.PIPE)
        xsel_proc.communicate(bytes(text, encoding="UTF-8"))

    if secondary:
        xsel_proc = subprocess.Popen(['xsel', '-si'], stdin=subprocess.PIPE)
        xsel_proc.communicate(bytes(text, encoding="UTF-8"))

    if clipboard:
        xsel_proc = subprocess.Popen(['xsel', '-bi'], stdin=subprocess.PIPE)
        xsel_proc.communicate(bytes(text, encoding="UTF-8"))


def set_clipboard(text):
    import platform
    system = platform.system()
    if "Darwin" == system:
        set_pbcopy_clipboard(text)
    elif "Linux" == system:
        set_xsel_clipboard(text)
    else:
        print(format("I don't know how to set clipboard on %s", system))


def parse_configfile(file_name=None):
    """ Parse configuration file and return config
    """
    log = logging.getLogger('parse_configfile')
    defaults = {
        'global': {
            'directory': '~/.pwstore',
        },
        'cleartext': {},
        'gpg': {
            'private key': '',
            'gpg location': ''
        },
    }
    parser = configparser.SafeConfigParser(default_section='global')

    parser.read_dict(defaults)

    if file_name is not None:
        try:
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

    return parser


def parse_commandline(command_line):
    """ Parse arguments and return configuration
    """
    log = logging.getLogger('parse_commandline')

    parser = argparse.ArgumentParser(description='Stores information in files')
    # parser.add_argument('command', metavar='<command>', choices=COMMANDS,
    #                     help="""""")
    # parser.add_argument('args', metavar='<arg>', nargs='*',
    #                     help="""""")
    parser.add_argument('-c', '--config',
                        default='~/.pwstore/configuration',
                        help='which configurationfile to use')

    parser.add_argument('-d', '--directory',
                        default='~/.pwstore/storage',
                        help=('directory with storage backends (if different '
                              'from default or configuration)'))

    # parser.add_argument('--debug', nargs=1, metavar="DEBUGLEVEL",
    #                     default='INFO',
    #                     help=("The debug level to use for logging"))

    # Matchers ###############################################################
    match_parser = argparse.ArgumentParser(add_help=False)
    matchers = match_parser.add_mutually_exclusive_group()
    matchers.add_argument('-r', '--regexp',
                          help='use regular expression matcher',
                          action='store_true', default=True)
    # matchers.add_argument('-t', '--token', help='use token expression matcher',
    #                       action='store_true', default=False)

    # Subparsers #############################################################
    subparsers = parser.add_subparsers(dest='command', title='subcommands',
                                       description='valid subcommands')

    ###### Create ############################################################
    create_parser = subparsers.add_parser(
        'create', help='create a new entry',
        description='''Create a new entry for the given <key> in an existing
                       backend''')
    create_parser.add_argument('storage', metavar='<storage>', help="storage")
    create_parser.add_argument('key', metavar='<key>',
                               help="key for the new entry")

    ###### Get ###############################################################
    get_parser = subparsers.add_parser(
        'get', aliases=['g'], help='get password (first line) from an entry',
        description=('Get the password (first line) from an entry described '
                     'by <pattern>'),
        parents=[match_parser])
    get_parser.add_argument('pattern', metavar='<pattern>',
                            help="pattern for the wanted entry")
    get_parser.add_argument('--clipboard', action="store_true",
                            help="Set clipboard instead of print to stdout")

    ###### Show ##############################################################
    show_parser = subparsers.add_parser(
        'show', aliases=['sh'], help='show an entry',
        description='show the entry described by <pattern>',
        parents=[match_parser])
    show_parser.add_argument('-c', '--stdout', help='print password on stdout',
                             action='store_true', default=False)
    show_parser.add_argument('pattern', metavar='<pattern>',
                             help="pattern for the wanted entry")

    ###### List ##############################################################
    list_parser = subparsers.add_parser(
        'list', aliases=['ls'], help='list keys',
        description='show keys matching <pattern> (or all)',
        parents=[match_parser])
    list_parser.add_argument('pattern', metavar='<pattern>', help='pattern',
                             nargs='?', default='')
    ###### Help ##############################################################
    help_parser = subparsers.add_parser('help', help='show help')
    help_parser.add_argument('help_command', metavar='command', nargs='?')

    try:
        import argcomplete
        argcomplete.autocomplete(parser)
    except ImportError:
        log.debug("No argcomplete found")

    args = parser.parse_args(command_line[1:])
    if 'help' == args.command:
        if args.help_command is None:
            parser.print_help()
        else:
            subparsers.choices.get(args.help_command, parser).print_help()

        sys.exit(0)

    log.debug("args: %s", args)

    return args


###############################################################################

if '__main__' == __name__:
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter('%(asctime)s - %(name)s -'
                                  ' %(levelname)s - %(message)s')

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(formatter)

    logger.addHandler(console)

    args = parse_commandline(sys.argv)

    config_path = os.path.expanduser(args.config)
    log.debug("Configfile is %s", config_path)

    configuration = parse_configfile(config_path)

    output = Output()

    if args.command in ['ls', 'list']:
        backends = get_backends(args.directory)
        matcher = get_matcher(args, args.pattern)
        for backend in backends.values():
            backend.filter(output, matcher)

        output.pretty_print()

    elif args.command in ['g', 'get']:
        backends = get_backends(args.directory)
        matcher = get_matcher(args, args.pattern)
        for backend in backends.values():
            password = backend.get_password(matcher)
            if password is not None:
                if args.clipboard is True:
                    set_clipboard(password)
                else:
                    print(password)
                break

    elif args.command in ['sh', 'show']:
        backends = get_backends(args.directory)
        matcher = get_matcher(args, args.pattern)
        for backend in backends.values():
            password = backend.get_entry(matcher)
            if password is not None:
                print(password)
                break

    elif args.command in ['create']:
        backends = get_backends(args.directory)
        backend = backends.get(args.storage, None)
        if backend is None:
            print("There is no such storage")

        backend.create(args.key)
