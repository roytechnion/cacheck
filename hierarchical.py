from levelpolicies import LLRU

# accept two policies
# construct fst policy and scnd policy
# record: ->
# 1. Your default is 10% DRAM, 90% SSD. In principle we could experiment with 1%, 5%, 10%, 20%, 30%, 40%, 50%.
# 2. You can only access data that is in DRAM, so if an item is only in the SSD, you must first bring it to DRAM, and so incur both an SSD access and (one or two?) DRAM access(es).
#    Yes, actually I suppose it's 4 DRAM accesses. We read the data from disk to ram, then we deserialize it from a byte buffer to the structured format redis uses, and then we operate on it.
# 3. In your implementation, can the same data item be stored both in DRAM and SSD, or only in one (at most one) of them at the same time?
#    Yes objects in the ram can either be clean or dirty, clean ones (unmodified) are overlapping with disk copies, and can be removed from ram when cold, without any disk write. The dirty ones can also be overlapping (in case loaded from the disk and modified), we don't currently bother to delete them right away.
# 4. You apply LRU to both DRAM and SSD. An item that is removed from DRAM by LRU is demoted to SSD, and then if the SSD if full, a victim is chosen by LRU and removed from the SSD.
#    Yes, when the ram is full we use lru to swap out, and when the total quota of the db is full we delete something based on lru too (in this case it's usually cold items that are only on disk).
# 5. New items are always placed in DRAM (to be managed by LRU).
#    Yes, new objects are always created in the ram. The only exception is during import operation, in which case when the ram is full, we stote the new keys directly to the disk.
#
# Need to maintain statistics about each level's hit & miss (taken care of by its policy object), and then the hybrid hits and misses.
# Complications: We must fst check if in fst level, if yes, it is a hit. Then, check if in scnd level. If yes, hit there and bring it to fst. When evicting from fst, write to snd and if necessary remove one from there, but needs to be careful as it might be there). In the case of writeback, should not be counted as a hit nor as a miss.
# It seems that we also need to compute accesses and not just hits and misses.


class HierarchicalCache(object):
    def __init__(self, l1_maximum_size, l2_maximum_size):
        self.l1_maximum_size = l1_maximum_size
        self.l2_maximum_size = l2_maximum_size
        self.misses = 0
        self.hits = 0
        self.accesses = 0
        self.remote_accesses = 0
        self.remote_writes = 0
        self.remote_charged = 0
        self.l1_cache = LLRU(l1_maximum_size)
        self.l2_cache = LLRU(l2_maximum_size)
        pass

    def get_stats(self):
        res1 = self.l1_cache.get_stats()
        res2 = self.l2_cache.get_stats()
        return {'name': self.__class__.__name__, 'l1_size': res1['size'], 'l2_size': res2['size'], 'l1_hits': res1['hits'], 'l1_misses': res1['misses'], 'l1_accesses': res1['accesses'], 'l1_writes': res1['writes'], 'l1_charged': res1['charged'], 'l1_hit_ratio': res1['hit ratio'], 'l2_hits': res2['hits'], 'l2_misses': res2['misses'], 'l2_accesses': res2['accesses'], 'l2_writes': res2['writes'], 'l2_charged': res2['charged'], 'l2_hit_ratio': res2['hit ratio'], 'total_hits': self.hits, 'total_misses': self.misses, 'total_accesses': self.accesses, 'remote_accesses': self.remote_accesses, 'remote_writes': self.remote_writes, 'remote_charged': self.remote_charged, 'total_hit_ratio': self.hits/(self.hits+self.misses)}
       # return {'name' : self.__class__.__name__, 'size' : self.maximum_size, 'hits' : self.hits, 'misses' : self.misses, 'accesses' : self.accesses, 'hit ratio' : self.hits / (self.hits + self.misses) }

    def get_name(self):
        return self.__class__.__name__

    def reset(self):
        self.misses = 0
        self.hits = 0
        self.accesses = 0
        self.remote_accesses = 0
        self.remote_writes = 0
        self.remote_charged = 0
        self.l1_cache.reset()
        self.l2_cache.reset()

    # We handle the l2 victims by writing back victims that were modified
    # Yet, we do not count a remote_charge for them since we assume write-backs are totally asynchronous
    def handle_l2_victim(self, victim):
        (key, size, status) = victim
        if status:
            self.remote_accesses += 1
            self.remote_writes += 1
        pass

    # We handle the l1 victims by recording them in the L2
    # Next, each victim of the l2 should be handled as well
    def handle_l1_victim(self, victim):
        (key, size, status) = victim
        (l2_hits,l2_victims) = self.l2_cache.record(key, size, status, allcharge=False, count=False) # allcharge=False since we assume that such write-backs are asynchronous so 0 latency
        for victim in l2_victims:
            self.handle_l2_victim(victim)
        pass

    def l1_record(self, key, size=1, status=None, count=True):
        (l1_hit,l1_victims) = self.l1_cache.record(key, size, status, allcharge=True, count=count)
        if l1_hit:
            self.hits += 1
        for victim in l1_victims:
            self.handle_l1_victim(victim)

    def record(self, key, size=1, status=None):
        self.accesses += 1
        if status:
            self.l1_record(key, size, status)
            return
        hit = self.l1_cache.try_access(key, allcharge=True)
        if hit:
            self.hits += 1
            return
        hit = self.l2_cache.try_access(key, allcharge=False) # allcharge=False since we assume a bloom filter that prevents misses from invoking an access to SSD
        if hit:
            self.hits += 1
            self.l1_record(key, size, status, count=False) # count=False since we already counted hit/miss/access during the try_access
        else:
            self.misses += 1
            self.remote_accesses += 1
            self.remote_charged += 1 # we simulate a read by charging the latency
            self.l1_record(key, size, status, count=False) # count=False since we already counted hit/miss/access during the try_access


