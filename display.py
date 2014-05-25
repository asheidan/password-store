import os
from collections import defaultdict


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

    # print(code)

    print("\n".join(sorted(keys)))


class Output:
    B = 'B'
    S = 'S'
    K = 'K'

    empty_pad = "    "
    line_pad = "\u2502   "
    tree_node = "\u251C\u2500\u2500 "
    tree_end = "\u2514\u2500\u2500 "

    def __init__(self, colorizer=Colorizer()):
        self.level = 0
        self.stack = []
        self.tree = []
        self.current_node = self.tree

        self.color = colorizer

    def pad(self, line):
        print(self.line_pad * self.level + line)

    def start_backend(self, name):
        tmp = []
        self.current_node.append((name, self.B, tmp))
        self.stack.append(self.current_node)
        self.current_node = tmp

    def end_backend(self):
        # self.level -= 1
        while len(self.stack) > 0:
            self.current_node = self.stack.pop()

    def start_sub(self, name):
        tmp = []
        self.current_node.append((name, self.S, tmp))
        self.stack.append(self.current_node)
        self.current_node = tmp

    def end_sub(self):
        self.current_node = self.stack.pop()

    def key(self, key):
        self.current_node.append((key, self.K, None))

    def pprint(self):
        from pprint import pprint
        pprint(self.tree)

    def format_node(self, node, pad_string="", is_last=False):
        result = []
        name, type, sub_nodes = node
        # print(sub_nodes)

        if is_last:
            sub_pad = self.empty_pad
            this_pad = self.tree_end
        else:
            sub_pad = self.line_pad
            this_pad = self.tree_node

        if (type == self.B):
            result.append(pad_string + self.color.storage(name))
            sub_pad = ""
        elif (type == self.S):
            result.append(pad_string + this_pad + self.color.directory(name))
        elif (type == self.K):
            result.append(pad_string + this_pad + name)

        if type != self.K and sub_nodes is not None:
            if len(sub_nodes) > 0:
                for n in sub_nodes[:-1]:
                    result.extend(self.format_node(n, pad_string + sub_pad))
                n = sub_nodes[-1]
                result.extend(self.format_node(n, pad_string + sub_pad, True))

        return result

    def pretty_print(self):
        for node in self.tree:
            print("\n".join(self.format_node(node)))
