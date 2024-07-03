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

# Algorithm:
# On an access to high level:
#   Increment TL access count.
#   If exists in high level, we simply incur a hit: increment TL + OA hit count and skip to END.
#   Otherwise, increment TL miss count and initiate an access to low level.
#     Increment BL access count
#     If it exists in low level, increment BL + OA hit count and return to high level.
#     Otherwise, increment BL miss count and return nil
#   When returning, if nil
#     If read, increment RT access count
#   Increment TL access count
#   Add to high level and check for victim(s)
#   If victim(s) is(are) dirty, initiate an add to low level
#     Increment BL access count
#     Check for victim(s)
#     For each victim, if dirty, increment RT access count
# END:
# If it is a write, we mark dirty.
