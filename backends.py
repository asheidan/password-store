# -*- coding: UTF-8

import configparser
import contextlib
from io import StringIO
import logging
import os
import sys

log = logging.getLogger(__name__)

CONFIG_FILE_NAME = "storage.conf"

# Backends ####################################################################


class BaseBackend(object):

    def __init__(self, root_folder, config):
        self.root = os.path.abspath(root_folder)
        self.config = config
        self.name = os.path.basename(root_folder)
        self.trivial_path = root_folder

    def list(self):
        return []

    def __unicode__(self):
        return self.root

    def __str__(self):
        return str(unicode(self))


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
        output.start_backend(self.name)
        for path, subs, files in walker:
            current_path = path.split(os.sep)
            # print(current_path, common_path)
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

            for filename in files:
                if (not filename.startswith('.') and
                        not filename.startswith(CONFIG_FILE_NAME)):
                    key = os.path.join(path, filename)
                    if matcher is None or matcher.matches(key):
                        output.key(filename)

        root_list = self.root.split(os.sep)
        for _ in range(0, len(common_path) - len(root_list)):
            output.end_sub()
        output.end_backend()

    def _matching_keys(self, matcher):
        walker = os.walk(self.root, followlinks=True)
        root_len = len(self.root)
        for path, subs, files in walker:
            for filename in files:
                if (not filename.startswith('.') and
                        not filename.startswith(CONFIG_FILE_NAME)):
                    abs_path = os.path.join(path, filename)
                    key = abs_path[root_len+1:]
                    if matcher is None or matcher.matches(key):
                        yield(key)

    def path_for_key(self, key):
        return os.path.join(self.root, key)

    @contextlib.contextmanager
    def storage_for_key(self, key, mode="r"):
        storage_path = self.path_for_key(key)
        if mode != 'r':
            directory = os.path.dirname(storage_path)
            if os.path.exists(directory):
                if not os.path.isdir(os.path.dirname(storage_path)):
                    log.error("Cant't create directory, file already exists"
                              "with the same name")
                    raise Exception
            else:
                log.info("Creating directory: %s", directory)
                os.makedirs(directory)
        log.debug("Opening %s mode %s", storage_path, mode)
        with open(storage_path, mode) as storage_file:
            yield storage_file

    def get_password(self, matcher):
        """ Returns the password (first line) for the given key """
        password = None
        for key in self._matching_keys(matcher):
            with self.storage_for_key(key) as storage:
                password = storage.readline().rstrip(self.ignore_chars)

            return password

    def get_entry(self, matcher):
        """ Returns the entry for the given key """
        for key in self._matching_keys(matcher):
            with self.storage_for_key(key) as storage:
                return storage.read()

    def create(self, key):
        content = sys.stdin.read()
        with self.storage_for_key(key, mode="x") as storage:
            storage.write(content)


class GPGBackend(ClearTextBackend):

    _gpg = None
    default_gpg_binary = "gpg"

    @property
    def gpg(self):
        if self._gpg is None:
            import gnupg
            self._gpg = gnupg.GPG(use_agent=True,
                                  gpgbinary=self.gpg_binary)

        return self._gpg

    def __init__(self, root_folder, config, gpg_binary=None):
        super(GPGBackend, self).__init__(root_folder, config)

        self.key_names = set(config.get('gpg', 'keys').strip().split('\n'))
        self.keys = list()

        if gpg_binary is not None:
            self.gpg_binary = gpg_binary
        else:
            self.gpg_binary = self.default_gpg_binary

        self.gpg_binary = config.get('gpg', 'gpg-binary',
                                     fallback=self.gpg_binary)

        for key in self.gpg.list_keys():
            for uid in key.get('uids', []):
                if uid in self.key_names:
                    self.keys.append(key)
                    continue
        log.debug("Keys for storage: %s", self.keys)
        os.environ["PINENTRY_USER_DATA"] = "USE_CURSES=0"

    @contextlib.contextmanager
    def storage_for_key(self, key, mode="r"):
        if mode != "r":
            storage = StringIO()
            yield storage

            encrypted_data = self.encrypt(storage.getvalue())
            with super(GPGBackend, self).storage_for_key(key, mode) as storage:
                storage.write(str(encrypted_data))
        else:
            with super(GPGBackend, self).storage_for_key(key, mode) as storage:
                log.debug("The storage: %s", storage)
                decrypted_data = self.decrypt(storage.read())
                yield StringIO(str(decrypted_data))

    def encrypt(self, data):
        if len(self.keys) != len(self.key_names):
            print(self.key_names)
            raise ValueError('Missing keys in keychain')
        keys = [k['keyid'] for k in self.keys]
        encrypted_data = self.gpg.encrypt(data, keys, always_trust=True)
        return encrypted_data

    def decrypt(self, data):
        decrypted_data = self.gpg.decrypt(data)
        return decrypted_data


# Helpers #####################################################################

_backends = None


def get_backends(directory):
    global _backends
    if _backends is not None:
        return _backends

    log = logging.getLogger('backends.get_backends')
    backends = {}

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
                    backend = ClearTextBackend(path, config)
                elif backend_type == 'gpg':
                    backend = GPGBackend(path, config)

                backends[backend.name] = backend
            except configparser.NoSectionError:
                log.error('No backend section in configuration %s',
                          config_file)
            except configparser.NoOptionError as error:
                log.error(error)

    _backends = backends
    return backends
