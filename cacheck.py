import os.path
import time

import numpy as np

#from simplepolicies import LRU , WTinyLFU, AdaptiveWTinyLFU, WC_WTinyLFU, WI_WTinyLFU
from simplepolicies import LRU,LFU
from hierarchical import HierarchicalCache
from parsers import LirsParser,RedisParser
import glob
from costmodel import CostModel
import argparse
import graphs
import math


parser = argparse.ArgumentParser()
parser.add_argument('-o', '--outfile', action='store', default='results.csv')
parser.add_argument('-p', '--path', action='store', default='graphs')
parser.add_argument('-t', '--tracesdir', action='store', default='C:\\Users\\user\\PycharmProjects\\TraceGenerator\\zipf_traces\\')
parser.add_argument('-r', '--redis', action='store', type=bool, default=False)
parser.add_argument('-a', '--append', action='store', type=bool, default=False)
parser.add_argument('-m', '--multilayer', action='store', type=bool, default=False)
parser.add_argument('-b', '--budgeted', action='store', type=bool, default=False)
parser.add_argument('-u', '--unitsize', action='store', type=int, default=1024) # minimal size of an item in Bytes
args = parser.parse_args()

cost_size = 1024*1024*1024 # 1 GB
units_per_cost = cost_size / args.unitsize
cache_technologies = [CostModel("DRAM",0.5), CostModel("SSD", 3)]
# storage_technologies = [CostModel("Dynamodb", 10), CostModel("Mongodb", 50), CostModel("SQL", 100)]
storage_technologies = [CostModel("FastDB", 10), CostModel("ModDB", 50), CostModel("SlowDB", 100)]

redis_managed_costs = { 0.05: 260,
                        0.10: 400,
                        0.20: 720,
                        0.30: 1040,
                        0.40: 1360,
                        0.50: 1680,
                        1.00: 2300
                        }
budgets_of_interest = np.array([100, 200, 300, 400, 600, 600, 700, 800, 900, 1000])

aggresults = {}


def run(trace, policy):
    policy.reset()
    for item in trace:
        policy.record(item)
    return policy.get_stats()


def add_trace_results(trace):
    if trace not in aggresults:
        aggresults[trace] = {}


def add_policy_results(trace,policy):
    if policy not in aggresults[trace]:
        aggresults[trace][policy] = {}


def add_size_results(trace,policy,size,resname,resvalue):
    if size not in aggresults[trace][policy]:
        aggresults[trace][policy][size] = {}
    if resname not in aggresults[trace][policy][size]:
        aggresults[trace][policy][size][resname] = resvalue


def main():
    open_mode = "w"
    if args.append:
        open_mode = "a"
    f = open(args.outfile, open_mode)
    if args.multilayer:
        f.write("Trace,Policy,L1_Size,L2_Size,L1_Hits,L1_Misses,L1_Accesses,L1_Writes,L1_Charged,L1_Hit_Ratio,L2_Hits,L2_Misses,L2_Accesses,L2_Writes,L2_Charged,L2_Hit_Ratio,Total_Hits,Total_Misses,Total_Accesses,Remote_Accesses,Remote_Writes,Remote_Charged,Total_Hit_Ratio,Time(s)")
        for storage in storage_technologies:
            f.write(", Weighted{}".format(storage.name))
    else:
        f.write("{:<20},{:<12},{:<12},{:<12},{:<12},{:<12},{:<12}".format('Trace', 'Policy', 'Cache Size', 'Hits', 'Misses', 'Hit Ratio', 'Time(s)'))
        technologies = []
        for storage in storage_technologies:
            for cache in cache_technologies:
                technology = storage.name+cache.name
                f.write(",{:12}".format(technology))
                technologies.append(technology)
    f.write("\n")
    policies = []
    if args.multilayer:
        if args.budgeted:
            for budget in budgets_of_interest:
                for percentage,cost in redis_managed_costs.items():
                    if percentage < 1.00:
                        total_size = math.ceil(budget * units_per_cost/ cost)
                        policies.append(HierarchicalCache(math.ceil(percentage * total_size), math.ceil((1 - percentage) * total_size)))
        else:
            for factor in range(3, 7):
                for i in range(1, 10, 1):
                    if factor < 6 or i < 2:
                        cachesize = i*(10**factor)
                        for percentage in [0.01, 0.05, 0.10, 0.20, 0.30, 0.40, 0.5]:
                            policies.append(HierarchicalCache(math.ceil(percentage*cachesize), math.ceil((1-percentage)*cachesize)))
    else:
        if args.budgeted:
            for budget in budgets_of_interest:
                size = math.ceil(budget * units_per_cost / redis_managed_costs[1.00])
                policies.append(LRU(size))
        else:
            for factor in range(3,7):
                for i in range(1,10,1):
                    if factor < 6 or i < 2:
                        policies.append(LRU(i*(10**factor)))
                        policies.append(LFU(i * (10 ** factor)))
    #tracesfiles = glob.glob("C:\\Users\\user\\PycharmProjects\\TraceGenerator\\zipf_traces\\zipf_[1-1].[0-5]_0.0.tr")
    tracesfiles = []
    if args.redis:
        tracesfiles = glob.glob(os.path.join(args.tracesdir,'redis_anonymized_*.txt'))
    else:
        for trace in ["zipf_0.6_0.0", "zipf_0.8_0.0", "zipf_1.0_0.0", "zipf_1.2_0.0", "zipf_1.5_0.0"]:
            tracesfiles.append(os.path.join(args.tracesdir,trace+".tr"))
            for recency in ["0.5", "1.0"]:
                recencytrace = trace.replace("0.0",recency)  # BUG: does not work "zipf_0.0_[0-9].[0.9]" traces
                tracesfiles.append(os.path.join(args.tracesdir, recencytrace + ".tr"))
    for tracefile in tracesfiles:
        add_trace_results(os.path.basename(tracefile))
        for policy in policies:
            add_policy_results(os.path.basename(tracefile),policy.get_name())
            start = time.time()
            if args.redis:
                trace = RedisParser(tracefile)
            else:
                trace = LirsParser(tracefile)
            results = run(trace, policy)
            end = time.time()
            if args.multilayer:
                f.write("{trace:<20}, ".format(trace=os.path.basename(tracefile)))
                f.write("{name}, {l1_size}, {l2_size}, {l1_hits}, {l1_misses}, {l1_accesses}, {l1_writes}, {l1_charged}, {l1_hit_ratio}, {l2_hits}, {l2_misses}, {l2_accesses}, {l2_writes}, {l2_charged}, {l2_hit_ratio}, {total_hits}, {total_misses}, {total_accesses}, {remote_accesses}, {remote_writes}, {remote_charged}, {total_hit_ratio}, {time}".format(**results, time=round(end - start,4)))
                for storage in storage_technologies:
                    weighted = results['l1_charged'] * cache_technologies[0].access_time + results['l2_charged'] * cache_technologies[1].access_time + results['remote_charged'] * storage.access_time
                    f.write(", {:12}".format(weighted))
            else:
                add_size_results(os.path.basename(tracefile), policy.get_name(), policy.maximum_size, "hit ratio", results['hit ratio'])
                f.write("{trace:<20},".format(trace=os.path.basename(tracefile)))
                f.write("{name:<12},{size:<12},{hits:<12},{misses:<12},{hit ratio:<12},{time:<12}".format(**results, time=round(end - start,4)))
                for storage in storage_technologies:
                    for cache in cache_technologies:
                        weighted = results['hits'] * cache.access_time + (results['misses'] * storage.access_time)
                        f.write(",{:12}".format(weighted))
                        add_size_results(os.path.basename(tracefile), policy.get_name(), policy.maximum_size, storage.name+cache.name, weighted)
            f.write("\n")
            f.flush()
            print(".", end="")
    f.close()
    print("")
    if not args.multilayer:
        graphs.generate_all_graphs(".\\graphs",aggresults,technologies)


if __name__ == "__main__":
    main()
