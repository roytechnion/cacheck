import csv
import argparse
import os
import matplotlib.pyplot as plt
import math
import sys
from matplotlib import cm
import numpy as np


parser = argparse.ArgumentParser()
parser.add_argument('-i', '--infile', action='store', default='multi-output.csv')
parser.add_argument('-d', '--indir', action='store', default='.')
parser.add_argument('-o', '--outdir', action='store', default='.\\graphs\\budget')
parser.add_argument('-r', '--ramcost', action='store', type=int, default=2300) # in cents/GB/month
parser.add_argument('-s', '--ssdcost', action='store', type=int, default=260) # in cents/GB/month
parser.add_argument('-u', '--unitsize', action='store', type=int, default=1024) # minimal size of an item in Bytes
parser.add_argument('-v', '--verbose', action='store', type=bool, default=False)

args = parser.parse_args()

cost_size = 1024*1024*1024 # 1 GB
storage_technologies = ["FastDB","ModDB","SlowDB"]


def plot_budgets(trace,storage,best_budgets,best_l1s,best_l2s,best_latencies):
    best_l1s = np.array(best_l1s)
    best_l2s = np.array(best_l2s)
    fig = plt.figure(figsize=plt.figaspect(2))
    ax = fig.add_subplot(projection='3d')
    ax.scatter(best_budgets, best_l1s/(best_l1s+best_l2s), best_latencies, marker='^')
    plt.xlabel("Total Budget")
    plt.ylabel("L1 Relative Size")
    ax.set_title(trace.split(".txt")[0] + ":" + storage + ":" + str(args.ramcost) + ":" + str(args.ssdcost) + ":" + str(args.unitsize))
    plt.savefig(os.path.join(args.outdir, trace.split(".txt")[0] + "_" + storage + "_" + str(args.ramcost) + "_" + str(args.ssdcost) + "_" + str(args.unitsize) + ".png"), bbox_inches='tight')
    plt.close()


def parse_input():
    results = {}
    with open(os.path.join(args.indir,args.infile), mode ='r') as file:
        dictResults = csv.DictReader(file)
        for row in dictResults:
            trace = row['Trace']
            if trace not in results:
                results[trace] = {}
            L1_size = int(row['L1_Size'])
            L2_size = int(row['L2_Size'])
            for storage in storage_technologies:
                if storage not in results[trace]:
                    results[trace][storage] = {}
                budget = round((L1_size * args.ramcost + L2_size * args.ssdcost) * args.unitsize / cost_size,2)
                if args.verbose:
                    print("L1_size:" + str(L1_size) + " L2_size:" + str(L2_size) + " Budget:" + str(budget))
                weighted = " Weighted" + storage
                if budget not in results[trace][storage].keys():
                    results[trace][storage][budget] = [(L1_size,L2_size,float(row[weighted]))]
                    if args.verbose:
                        print("New: " + str(L1_size) + "," + str(L2_size) + "," + str(float(row[weighted])))
                else:
                    results[trace][storage][budget].append((L1_size,L2_size,float(row[weighted])))
                    if args.verbose:
                        print("append: " + L1_size + "," + L2_size + "," + float(row[weighted]))
    return results


def find_fastest(budget_limit, max_i, prev_i, budgets, results):
    if args.verbose:
        print("find_fastest:"+str(budget_limit)+":"+str(max_i)+":"+str(prev_i)+":"+str(len(budgets)))
    min_latency = sys.maxsize
    best_l1 = 0
    best_l2 = 0
    best_budget = 0
    for i in range(prev_i,max_i,1):
        for l1_size,l2_size,latency in results[budgets[i]]:
            if latency < min_latency:
                min_latency = latency
                best_l1 = l1_size
                best_l2 = l2_size
                best_budget = budgets[i]
    if args.verbose:
        print("found:"+str(best_budget)+":"+str(best_l1)+":"+str(best_l2)+":"+str(min_latency))
    return (best_budget,best_l1,best_l2,min_latency)


def process_input(results):
    for trace in results.keys():
        for storage in results[trace]:
            best_budgets = []
            best_l1s = []
            best_l2s = []
            best_latencies = []
            budgets = list(results[trace][storage].keys())
            budgets.sort()
            budget_steps = range(math.ceil(budgets[0]), args.ramcost+1, 20)
            max_i = 0
            prev_i = 0
            for budget_limit in budget_steps:
                while max_i < len(budgets) and budgets[max_i] <= budget_limit:
                    max_i += 1
                if prev_i < len(budgets):
                    best_budget,best_l1,best_l2,best_latency = find_fastest(budget_limit,max_i,prev_i,budgets,results[trace][storage])
                    if best_budget > 0:
                        best_budgets.append(best_budget)
                        best_l1s.append(best_l1)
                        best_l2s.append(best_l2)
                        best_latencies.append(best_latency)
                prev_i = max_i
            plot_budgets(trace,storage,best_budgets,best_l1s,best_l2s,best_latencies)



results = parse_input()
process_input(results)

#        for storage in ["FastDB","ModDB","SlowDB"]:
#            multiplot_storage("Weighted"+storage,traceresults,X,Y)