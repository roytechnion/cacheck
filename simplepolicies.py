from enum import Enum, auto
from collections import Counter
from math import log
from scipy import stats
from sortedcontainers import SortedDict

class Policy(object):
    def __init__(self, maximum_size):
        self.maximum_size = maximum_size
        self.misses = 0
        self.hits = 0
        pass
    def record(self, key, size=1):
        pass
    def get_stats(self):
        return {'name' : self.__class__.__name__, 'size' : self.maximum_size, 'hits' : self.hits, 'misses' : self.misses, 'hit ratio' : self.hits / (self.hits + self.misses) }
    def get_name(self):
        return self.__class__.__name__


class LRU(Policy):
    def __init__(self, maximum_size):
        super().__init__(maximum_size)
        self.current_size = 0
        self.data = {}
        self.sentinel = Node()

    def record(self, key, size=1):
        node = self.data.get(key)
        if node:
            self.hits += 1
            node.remove()
            node.append_to_tail(self.sentinel)
        else:
            self.misses += 1
            if size > self.maximum_size:
                return
            self.current_size += size
            while (self.current_size > self.maximum_size):
                del self.data[self.sentinel.next_node.data]
                self.current_size -= self.sentinel.next_node.size
                self.sentinel.next_node.remove()
            new_node = Node(key, size=size)
            new_node.append_to_tail(self.sentinel)
            self.data[key] = new_node


class Node(object):
    def __init__(self, data=None, size=1, status=None):
        self.data = data
        self.next_node = self
        self.prev_node = self
        self.status = status
        self.size = size
    def remove(self):
        self.prev_node.next_node = self.next_node
        self.next_node.prev_node = self.prev_node
    def append_to_tail(self, sentinel):
        self.prev_node = sentinel.prev_node
        self.next_node = sentinel
        self.prev_node.next_node = self
        self.next_node.prev_node = self
    def append_to_head(self, sentinel):
        self.next_node = sentinel.next_node
        self.prev_node = sentinel
        self.prev_node.next_node = self
        self.next_node.prev_node = self


class LFU(Policy):
    def __init__(self, maximum_size):
        super().__init__(maximum_size)
        self.current_size = 0
        self.lfuq = SortedDict()
        self.items = {}

    def record(self, key, size=1):
        node = self.items.get(key)
        if node:
            self.hits += 1
            item = self.items[key]
            lfuid = item[0]
            newlfuid = (lfuid[0]+1,lfuid[1])
            self.lfuq.pop(lfuid)
            self.lfuq[newlfuid] = key
            self.items[key] = (newlfuid,item[1])
        else:
            self.misses += 1
            if size > self.maximum_size:
                return
            self.current_size += size
            while (self.current_size > self.maximum_size):
                victim = self.lfuq.popitem(0)
                self.current_size -= self.items[victim[1]][1]
                self.items.pop(victim[1])
            lfuid = (1,self.misses)
            self.items[key] = (lfuid,size)
            self.lfuq[lfuid] = key


