import os
from collections import defaultdict

import logging

log = logging.getLogger(__name__)


class Colorizer(object):

    RED = 91
    GREEN = 92
    YELLOW = 93
    BLUE = 94

    def color(self, code=0):
        return "\033[%dm" % code

    def colorize(self, string, color_code):
        return self.color(color_code) + string + self.color()

    def directory(self, string):
        return self.colorize(string, self.BLUE)

    def storage(self, string):
        return self.colorize(string, self.RED)


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


def display(keys):
    import locale
    locale.setlocale(locale.LC_ALL, '')
    # code = locale.getpreferredencoding()

    print("\n".join(sorted(keys)))


class Node:
    alias = 'N'

    def __init__(self, name):
        self.name = name
        self.sub_tree = []

    def __iter__(self):
        return iter(self.sub_tree)

    def __len__(self):
        return len(self.sub_tree)

    def __getitem__(self, key):
        return self.sub_tree[key]

    def __delitem__(self, key):
        del self.sub_tree[key]

    def append(self, node):
        return self.sub_tree.append(node)

    def remove(self, value):
        return self.sub_tree.remove(value)

    def __repr__(self):
        return str((self.alias, self.name, self.sub_tree))


class Backend(Node):
    alias = 'B'


class Directory(Node):
    alias = 'D'


class Key(Node):
    alias = 'K'


class Output:
    empty_pad = "    "
    line_pad = "\u2502   "
    tree_node = "\u251C\u2500\u2500 "
    tree_end = "\u2514\u2500\u2500 "

    def __init__(self, colorizer=Colorizer()):
        self.level = 0
        self.stack = []
        self.tree = Node('root')
        self.current_node = self.tree

        self.color = colorizer

    def pad(self, line):
        print(self.line_pad * self.level + line)

    def start_backend(self, name):
        node = Backend(name)
        self.current_node.append(node)
        self.stack.append(self.current_node)
        self.current_node = node

    def end_backend(self):
        # self.level -= 1
        previous_node = self.stack.pop()
        if len(self.current_node) == 0:
            previous_node.remove(self.current_node)
        self.current_node = previous_node

        while len(self.stack) > 0:
            self.current_node = self.stack.pop()

    def start_sub(self, name):
        node = Directory(name)
        self.current_node.append(node)
        self.stack.append(self.current_node)
        self.current_node = node

    def end_sub(self):
        previous_node = self.stack.pop()
        if len(self.current_node) == 0:
            previous_node.remove(self.current_node)
        self.current_node = previous_node

    def key(self, key):
        self.current_node.append(Key(key))

    def pprint(self):
        from pprint import pprint
        pprint(self.tree)

    def format_node(self, node, pad_string="", is_last=False):
        result = []

        if is_last:
            sub_pad = self.empty_pad
            this_pad = self.tree_end
        else:
            sub_pad = self.line_pad
            this_pad = self.tree_node

        if type(node) == Backend:
            result.insert(0, pad_string + self.color.storage(node.name))
            sub_pad = ""
        elif type(node) == Directory:
            result.insert(
                0, pad_string + this_pad + self.color.directory(node.name))
        elif type(node) == Key:
            result.insert(0, pad_string + this_pad + node.name)

        if type(node) != Key:
            if len(node) > 0:
                for n in node[:-1]:
                    result.extend(self.format_node(n, pad_string + sub_pad))
                n = node[-1]
                result.extend(self.format_node(n, pad_string + sub_pad, True))

        return result

    def pretty_print(self):
        for node in self.tree:
            print("\n".join(self.format_node(node)))
