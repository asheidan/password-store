# -*- coding: UTF-8

import configparser
import contextlib
import logging
import os
import sys

CONFIG_FILE_NAME = "storage.conf"

### Backends ##################################################################

class BaseBackend(object):

    def __init__(self, root_folder, config):
        self.root = root_folder
        self.config = config

    def list(self):
        return []

    def __unicode__(self):
        return self.root

    def __str__(self):
        str(unicode(self))


class ClearTextBackend(BaseBackend):

    ignore_chars = "\t\r\n"

    def __init__(self, root_folder, config):
        super(ClearTextBackend, self).__init__(root_folder, config)
        self.log = logging.getLogger('backends.ClearText')

    def list(self):
        """ Returns an iterator for all the keys for this storage """
        walker = os.walk(self.root, followlinks=True)
        for path, subs, files in walker:
            for file in files:
                if (not file.startswith('.') and
                        not file.startswith(CONFIG_FILE_NAME)):
                    yield os.path.join(path, file)

    def filter(self, output, matcher=None):
        walker = os.walk(self.root, followlinks=True)
        common_path = self.root.split(os.sep)
        output.start_backend(self.root)
        for path, subs, files in walker:
            current_path = path.split(os.sep)
            #print(current_path, common_path)
            old_dirs = common_path.copy()
            new_dirs = current_path.copy()
            while (len(old_dirs) and len(new_dirs) and
                    old_dirs[0] == new_dirs[0]):
                old_dirs.pop(0)
                new_dirs.pop(0)

            for _ in old_dirs:
                output.end_sub()
            for name in new_dirs:
                output.start_sub(name)

            common_path = current_path

            #print("-%s +%s" % (old_dirs, new_dirs))

            for file in files:
                if (not file.startswith('.') and
                        not file.startswith(CONFIG_FILE_NAME)):
                    key = os.path.join(path, file)
                    if matcher is None or matcher.matches(key):
                        output.key(file)
        output.end_backend()

    @contextlib.contextmanager
    def storage_for_key(self, key, mode="r"):
        with open(key, mode) as storage_file:
            yield storage_file

    def get_password(self, key):
        """ Returns the password (first line) for the given key """
        password = None
        with self.storage_for_key(key) as storage:
            password = storage.readline().rstrip(self.ignore_chars)

        return password

    def get_entry(self, key):
        """ Returns the entry for the given key """
        with self.storage_for_key(key) as storage:
            return storage.read()

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

            try:
                backend_type = config.get('backend', 'type')
                if backend_type == 'cleartext':
                    backends.append(ClearTextBackend(path, config))
                elif backend_type == 'gpg':
                    backends.append(GPGBackend(path, config))
            except configparser.NoSectionError:
                log.error('No backend section in configuration %s', config_file)
            except configparser.NoOptionError as error:
                log.error(error)

    return backends


