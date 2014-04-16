import os
from collections import defaultdict


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


def tree_from_list(keys):
    treenode = None
    treenode = lambda: defaultdict(treenode)

    tree = treenode()

    for key in keys:
        node = tree
        for part in key.split(os.sep):
            print(part)
            node = node[part]

    return tree


def display_directory(keys):
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


def display(keys):
    import locale
    locale.setlocale(locale.LC_ALL, '')
    code = locale.getpreferredencoding()

    #print(code)

    print("\n".join(sorted(keys)))
