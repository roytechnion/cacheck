import csv
import argparse
import os
import numpy as np
from scipy.interpolate import BSpline, CubicSpline
import matplotlib.pyplot as plt
import math

parser = argparse.ArgumentParser()
parser.add_argument('-s', '--singlefile', action='store', default='single_budgeted.csv')
parser.add_argument('-m', '--multifile', action='store', default='multi_budgeted.csv')
parser.add_argument('-d', '--indir', action='store', default='.')
parser.add_argument('-p', '--outpath', action='store', default='.\\graphs\\budgeted')
parser.add_argument('-u', '--unitsize', action='store', type=int, default=1024) # minimal size of an item in Bytes
parser.add_argument('-v', '--verbose', action='store', type=bool, default=False)

args = parser.parse_args()

cost_size = 1024*1024*1024 # 1 GB
units_per_cost = cost_size / args.unitsize
storage_technologies = ["FastDB", "ModDB", "SlowDB"]

redis_managed_costs = { 0.05: 260,
                        0.10: 400,
                        0.20: 720,
                        0.30: 1040,
                        0.40: 1360,
                        0.50: 1680,
                        1.00: 2300
                        }
budgets_of_interest = np.array([100, 200, 300, 400, 600, 600, 700, 800, 900, 1000])


def parse_single_input():
    results = {}
    with open(os.path.join(args.indir,args.singlefile), mode ='r') as file:
        dictResults = csv.DictReader(file)
        for row in dictResults:
            trace = row['Trace               '].split(".txt")[0]
            if trace not in results:
                results[trace] = {}
            policy = row['Policy      '].strip()
            if policy not in results[trace]:
                results[trace][policy] = {}
            size = int(row['Cache Size  '].strip())
            if size not in results[trace][policy]:
                results[trace][policy][size] = {}
            results[trace][policy][size]["FastDB"] = int(float(row['FastDBDRAM  ']))
            results[trace][policy][size]["ModDB"] = int(float(row['ModDBDRAM   ']))
            results[trace][policy][size]["SlowDB"] = int(float(row['SlowDBDRAM  ']))
    return results


def parse_multi_input():
    results = {}
    with open(os.path.join(args.indir,args.multifile), mode ='r') as file:
        dictResults = csv.DictReader(file)
        for row in dictResults:
            trace = row['Trace'].split(".txt")[0]
            if trace not in results:
                results[trace] = {}
            l1_size = int(row['L1_Size'].strip())
            l2_size = int(row['L2_Size'].strip())
            if (l1_size,l2_size) not in results[trace]:
                results[trace][(l1_size,l2_size)] = {}
            results[trace][(l1_size,l2_size)]["FastDB"] = int(float(row[" WeightedFastDB"]))
            results[trace][(l1_size,l2_size)]["ModDB"] = int(float(row[" WeightedModDB"]))
            results[trace][(l1_size,l2_size)]["SlowDB"] = int(float(row[" WeightedSlowDB"]))
    return results


def trace_plot(trace,single,multi,storage):
    plt.figure()
    plt.rc('xtick', labelsize=18)
    plt.rc('ytick', labelsize=18)
    sizes = budgets_of_interest * units_per_cost / redis_managed_costs[1.00]
    sizes = list(map(lambda size: round(size),sizes))
    latencies = list(map(lambda size: single[size][storage],sizes))
    plt.plot(budgets_of_interest, latencies, label='100%')
    for ratio in redis_managed_costs.keys():
        if ratio < 0.3:
            total_sizes = budgets_of_interest * units_per_cost / redis_managed_costs[ratio]
            total_sizes = np.array(list(map(lambda size: math.ceil(size), total_sizes)))
            l1_sizes = ratio * total_sizes
            print("l1_sizes:", l1_sizes)
            l1_sizes = list(map(lambda size: math.ceil(size), l1_sizes))
            print("post l1_sizes:", l1_sizes)
            l2_sizes = (1-ratio) * total_sizes
            print("l2_sizes:", l2_sizes)
            l2_sizes = list(map(lambda size: math.ceil(size), l2_sizes))
            print("post l2_sizes:", l2_sizes)
            size_pairs = list(zip(l1_sizes, l2_sizes))
            print("trace_plot_2:", total_sizes, l1_sizes, l2_sizes)
            latencies = list(map(lambda size_pair: multi[size_pair][storage],size_pairs))
            plt.plot(budgets_of_interest, latencies, label=str(ratio * 100)+'%')
    #plt.xlim(min(budgets_of_interest), max(budgets_of_interest))
    #plt.ylim(min(latencies), max(latencies))
    plt.ylim(ymin=0)
    plt.xlabel('Budget',fontsize=20)
    plt.ylabel('Simulated Access Time (ms)', fontsize=20)
    plt.legend()
    plt.title(trace+":"+storage+":managed")
    plt.savefig(os.path.join(args.outpath,trace+"-"+storage+".png"), bbox_inches='tight')
    plt.close('all')


single_results = parse_single_input()
multi_results = parse_multi_input()
for trace in single_results:
    for storage in storage_technologies:
        trace_plot(trace,single_results[trace]['LRU'],multi_results[trace],storage)
