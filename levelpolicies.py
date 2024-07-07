class LevelPolicy(object):
    def __init__(self, maximum_size):
        self.maximum_size = maximum_size
        self.misses = 0
        self.hits = 0
        self.accesses = 0
        pass

    def reset(self):
        self.misses = 0
        self.hits = 0
        self.accesses = 0
        pass

    def try_access(self, key, status=None):
        return False

    def record(self, key, size=1, status=None):
        return []

    def get_stats(self):
        return {'name' : self.__class__.__name__, 'size' : self.maximum_size, 'hits' : self.hits, 'misses' : self.misses, 'accesses' : self.accesses, 'hit ratio' : self.hits / (self.hits + self.misses) }

    def get_name(self):
        return self.__class__.__name__


class LLRU(LevelPolicy):
    def __init__(self, maximum_size):
        super().__init__(maximum_size)
        self.current_size = 0
        self.data = {}
        self.sentinel = LNode()

    def reset(self):
        super().reset()
        self.current_size = 0
        self.data = {}
        self.sentinel = LNode()

    def lru_hit(self, node, status=None):
        self.hits += 1
        node.remove()
        node.append_to_tail(self.sentinel)
        if status:
            node.status = status

    def try_access(self, key, status=None):
        self.accesses += 1
        node = self.data.get(key)
        if node:
            self.lru_hit(node, status)
            return True
        else:
            self.misses += 1
            return False

    def record(self, key, size=1, status=None):
        self.accesses += 1
        node = self.data.get(key)
        if node:
            self.lru_hit(node, status)
            return []
        else:
            self.misses += 1
            if size > self.maximum_size:
                return
            self.current_size += size
            victims = []
            while (self.current_size > self.maximum_size):
                victims.append((self.sentinel.next_node.data,self.sentinel.next_node.size,self.sentinel.next_node.status))
                del self.data[self.sentinel.next_node.data]
                self.current_size -= self.sentinel.next_node.size
                self.sentinel.next_node.remove()
            new_node = LNode(key, size=size, status=status)
            new_node.append_to_tail(self.sentinel)
            self.data[key] = new_node
            return victims


class LNode(object):
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


