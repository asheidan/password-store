# -*- coding: UTF-8

import configparser
import logging
import os

CONFIG_FILE_NAME = "storage.conf"

### Backends ##################################################################

class BaseBackend(object):

    def __init__(self, root_folder, config):
        self.root = root_folder
        self.config = config

    def list(self):
        return []


class ClearTextBackend(BaseBackend):

    ignore_chars = "\t\r\n"

    def __init__(self, root_folder, config):
        super(ClearTextBackend, self).__init__(root_folder, config)

    def list(self):
        """ Returns an iterator for all the keys for this storage """
        walker = os.walk(self.root, followlinks=True)
        for path, subs, files in walker:
            for file in files:
                if not file.startswith(CONFIG_FILE_NAME):
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


### Helpers ###################################################################

def get_backends(directory):
    log = logging.getLogger('backends.get_backends')
    backends = []

    directory = os.path.expanduser(directory)
    walker = os.walk(directory, followlinks=True)

    log.debug('Walking %s', directory)
    for path, subdirs, files in walker:
        if CONFIG_FILE_NAME in files:
            del subdirs[:]

            log.debug("Found backend %s", path)

            config_file = os.path.join(path, CONFIG_FILE_NAME)
            config = configparser.SafeConfigParser()
            config.read(config_file)

            backend_type = config.get('backend', 'type')
            if backend_type == 'cleartext':
                backends.append(ClearTextBackend(path, config))
            elif backend_type == 'gpg':
                backends.append(GPGBackend(path, config))

    return backends


