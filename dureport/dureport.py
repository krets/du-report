import argparse
import json
import os
import sys
import time

DEFAULT_DEPTH = 3
class DuTree:
    def __init__(self, name=None, size=None, parent=None, depth=0):
        if name is None:
            name = ''
        self._name = name
        self._size = size
        self._sum_size = None
        self.parent = parent
        self.children = {}
        self.depth = depth

    @property
    def size(self):
        for cached in [self._size, self._sum_size]:
            if cached is not None:
                return cached

        self._sum_size = 0
        for name, child in self.children.items():
            self._sum_size += child.size
        return self._sum_size

    @size.setter
    def size(self, value):
        self._size = value

    @property
    def root(self):
        if self.parent is None:
            return self
        return self.parent.root

    @property
    def path(self):
        if self.parent is None:
            return "/"
        return "/".join([self.parent.path, self._name])

    def get(self, path):
        root = self.root

        cursor = root
        for part in path.split("/"):
            cursor = cursor[part]
        return cursor

    def human_size(self):
        suffixes = ['B', 'KB', 'MB', 'GB', 'TB']
        suffix_index = 0
        size_in_kb = self.size
        while size_in_kb >= 1024 and suffix_index < len(suffixes) - 1:
            size_in_kb /= 1024
            suffix_index += 1
        formatted_size = '{:.1f}'.format(size_in_kb)
        human_readable_size = formatted_size + ' ' + suffixes[suffix_index]
        return human_readable_size

    def __lt__(self, other):
        return self.size < other.size

    def __getitem__(self, name):
        if name == '' and self.parent is None:
            return self
        if name not in self.children:
            self.children[name] = DuTree(name, parent=self, depth=self.depth+1)
        return self.children[name]

    def __repr__(self):
        return f"<{self.__class__.__name__} ({self._name}) {self.human_size()}>"

    def find_first_branch(self):
        cursor = self

        for i in range(9999):
            if not cursor.children:
                break

            if len(cursor.children) > 1:
                break

            child = next(iter(cursor.children.values()), None)
            if child is None:
                break

            cursor = child


        return cursor


# Define a custom JSON encoder
class DuTreeEncoder(json.JSONEncoder):
    depth = 4

    def default(self, obj):
        if isinstance(obj, DuTree):
            if obj.depth > self.depth:
                return
            children = list(sorted(obj.children.values(), reverse=True))
            result = {
                "path": obj.path,
                "size": obj.size,
            }
            if children and obj.depth < self.depth:
                result['children'] = children
            return result
        return super().default(obj)


def main():
    parser = argparse.ArgumentParser(description='du output processor')
    parser.add_argument('-d', '--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose mode')
    parser.add_argument('--depth', type=int, default=DEFAULT_DEPTH, help=f'Specify depth (default: {DEFAULT_DEPTH})')
    parser.add_argument('-o', '--output', type=argparse.FileType('w'), default=sys.stdout, help=f'Specifiy output file to write json')

    parser.add_argument('file', nargs='?', type=argparse.FileType('r'), default=None,
                        help='Input file (alternatively can read from pipe)')
    args = parser.parse_args()

    if args.file:
        handler = args.file
    elif not sys.stdin.isatty():
        handler = sys.stdin
    else:
        parser.print_help()
        exit(1)


    base = DuTree()
    start = time.time()
    for line in handler:
        size, path = line.strip().split('\t')
        leaf = base.get(path)
        leaf.size = int(size)
        continue
    handler.close()

    stop = time.time()
    msg = "%0.1f seconds to parse" % (stop - start)
    print(msg)

    first_branch = base.find_first_branch()
    DuTreeEncoder.depth = args.depth + first_branch.depth # depth past jobs folder
    json.dump(first_branch, args.output, cls=DuTreeEncoder, indent=2)
    args.output.close()
    pass

if __name__ == '__main__':
    main()