import os.path
import time
#from simplepolicies import LRU , WTinyLFU, AdaptiveWTinyLFU, WC_WTinyLFU, WI_WTinyLFU
from simplepolicies import LRU
from parsers import LirsParser
import glob
from costmodel import CostModel
import argparse


parser = argparse.ArgumentParser()
parser.add_argument('-o', '--outfile', action='store', default='results.txt')
parser.add_argument('-p', '--path', action='store', default='graphs')
parser.add_argument('-t', '--tracesdir', action='store', default='C:\\Users\\user\\PycharmProjects\\TraceGenerator\\zipf_traces\\')
args = parser.parse_args()

cache_technologies = [CostModel("DRAM",0.5), CostModel("SSD", 3)]
storage_technologies = [CostModel("Dynamodb", 10), CostModel("Mongodb", 50), CostModel("SQL", 100)]

outputfile = "results1.out"


def run(trace, policy):
    for item in trace:
        policy.record(item)
    return policy.get_stats()


def main():
    f = open(args.outfile, "w")
    f.write("{:<20},{:<12},{:<12},{:<12},{:<12},{:<12}, {:<12}".format('Trace', 'Cache Size', 'Policy', 'Hits', 'Misses', 'Hit Ratio', 'Time(s)'))
    for storage in storage_technologies:
        for cache in cache_technologies:
            f.write(",{:12}".format(storage.name+cache.name))
    f.write("\n")
    policies = []
    for factor in range(3,7):
        for i in range(1,10):
            if factor < 6 or i < 2:
                policies.append(LRU(i*(10**factor)))
    #tracesfiles = glob.glob("C:\\Users\\user\\PycharmProjects\\TraceGenerator\\zipf_traces\\zipf_[1-1].[0-5]_0.0.tr")
    tracesfiles = []
    for trace in ["zipf_0.6_0.0", "zipf_0.8_0.0", "zipf_1.0_0.0", "zipf_1.2_0.0", "zipf_1.5_0.0"]:
        tracesfiles.append(os.path.join(args.tracesdir,trace+".tr"))
    for tracefile in tracesfiles:
        for policy in policies:
            start = time.time()
            trace = LirsParser(tracefile)
            results = run(trace, policy)
            end = time.time()
            f.write("{trace:<20},".format(trace=os.path.basename(tracefile)))
            f.write("{size:<12},{name:<12},{hits:<12},{misses:<12},{hit ratio:<12},{time:<12}".format(**results, time=round(end - start,4)))
            for storage in storage_technologies:
                for cache in cache_technologies:
                    f.write(",{:12}".format(results['hits'] * cache.access_time + (results['misses'] * storage.access_time)))
            f.write("\n")
            f.flush()
            print(".", end="")
    f.close()
    print("")


if __name__ == "__main__":
    main()
