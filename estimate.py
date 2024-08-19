import csv
import argparse
import os
import numpy as np
from scipy.interpolate import BSpline, CubicSpline
import matplotlib.pyplot as plt

parser = argparse.ArgumentParser()
parser.add_argument('-i', '--infile', action='store', default='results.csv')
parser.add_argument('-d', '--indir', action='store', default='.')
parser.add_argument('-o', '--outfile', action='store', default='.\\transformed.txt')
parser.add_argument('-p', '--outpath', action='store', default='.\\graphs\\projected')
parser.add_argument('-r', '--ramcost', action='store', type=int, default=2300) # in cents/GB/month
parser.add_argument('-s', '--ssdcost', action='store', type=int, default=260) # in cents/GB/month
parser.add_argument('-u', '--unitsize', action='store', type=int, default=1024) # minimal size of an item in Bytes
parser.add_argument('-v', '--verbose', action='store', type=bool, default=False)
parser.add_argument('-a', '--accuracy', action='store', type=int, default=4)
parser.add_argument('-f', '--filter', action='store', default="ALL")

args = parser.parse_args()

cost_size = 1024*1024*1024 # 1 GB
storage_technologies = {"FastDB" : 10,
                        "ModDB"  : 50,
                        "SlowDB" : 100}
l1_latency = 0.5
l2_latency = 3


def parse_input():
    results = {}
    with open(os.path.join(args.indir,args.infile), mode ='r') as file:
        dictResults = csv.DictReader(file)
        for row in dictResults:
            trace = row['Trace               '].split(".txt")[0]
            if trace not in results:
                results[trace] = {}
                results[trace]["nacceses"] = int(row['Hits        ']) + int(row['Misses      '])
            policy = row["Policy      "].strip()
            if args.filter == "ALL" or args.filter == policy:
                if policy not in results[trace]:
                    results[trace][policy] = []
                size = int(row["Cache Size  "].strip())
                hitratio = round(float(row["Hit Ratio   "].strip()),args.accuracy)
                results[trace][policy].append((size,hitratio))
    return results


def create_datasets(results):
    f = open(args.outfile, mode='w')
    for (trace, res) in results.items():
        for (policy, data) in res.items():
            if policy != 'nacceses':
                f.write(trace + ":" + policy + ":{")
                first = True
                for item in data:
                    if not first:
                        f.write(",")
                    first = False
                    f.write("{" + str(item[0]) + "," + str(item[1]) + "}")
                f.write("}\n\n")
    f.close()


l1_size_factor = cost_size / (args.unitsize * args.ramcost)
if args.verbose:
    print("l1_size_factor:", round(l1_size_factor,4))
l2_size_factor = cost_size / (args.unitsize * args.ssdcost)
if args.verbose:
    print("l2_size_factor:", round(l2_size_factor,4))


def latency_estimation(total_budgets, l1_budgets, f, nacceses, minx, maxx, remote_latency):
    # L(B,B1)=fh(B1*X)*A1+fh((B-B1)*Y)*A2+(1-fh((B1*X)+((B-B1)*Y)))*AS
    l1_sizes = l1_budgets * l1_size_factor
    if args.verbose:
        print("l1_size:", l1_sizes)
        print("Expected L1 hit ratio:", f(l1_sizes))
    minx = np.full(len(l1_sizes),minx)
    maxx = np.full(len(l1_sizes), maxx)
    l1_sizes = np.fmax(l1_sizes, minx)
    l1_sizes = np.fmin(l1_sizes, maxx)
    if args.verbose:
        print("Corrected Expected L1 hit ratio:", f(l1_sizes))
    l2_sizes = (total_budgets - l1_budgets) * l2_size_factor
    if args.verbose:
        print("l2_sizes:", l2_sizes)
        print("Expected L2 hit ratio:", f(l2_sizes))
    l2_sizes = np.fmax(l2_sizes, minx)
    l2_sizes = np.fmin(l2_sizes, maxx)
    if args.verbose:
        print("Corrected Expected L2 hit ratio:", f(l2_sizes))
    total_sizes = l1_budgets * l1_size_factor + (total_budgets - l1_budgets) * l2_size_factor
    if args.verbose:
        print("Total Sizes:", total_sizes)
        print("Expected total hit ratio:", f(total_sizes))
    total_sizes = np.fmax(total_sizes, minx)
    total_sizes = np.fmin(total_sizes, maxx)
    if args.verbose:
        print("Corrected Expected total hit ratio:", f(total_sizes))
    l1_share = f(l1_sizes) * nacceses
    remote_share = (1-f(total_sizes)) * nacceses
    l2_share = nacceses - (l1_share - remote_share)
    if args.verbose:
        print("l1_shares:", l1_share)
        print("l2_share:", l2_share)
        print("remote_share", remote_share)
    result = l1_latency * l1_share + l2_latency * l2_share + remote_share * remote_latency
    if args.verbose:
        print("latency_estimation:",result)
    return result


def plot_budgets(trace,policy,storage,best_budgets,best_l1s,best_l2s,best_latencies):
    best_l1s = np.array(best_l1s)
    best_l2s = np.array(best_l2s)
    best_budgets = np.array(best_budgets)
    width = 0.5
    best_budgets /= 100
    bottom = np.zeros(len(best_l2s))
    bottom_color = 'green'
    top_color = 'darkorange'
    fig, axs = plt.subplots(3, 1, sharex=True, figsize=(22, 10))
    p = axs[0].bar(best_budgets, best_l2s, width, label="L2", bottom=bottom, color=bottom_color)
    axs[0].bar_label(p, label_type='center')
    p = axs[0].bar(best_budgets, best_l1s, width, label="L1", bottom=best_l2s, color=top_color)
    axs[0].set_ylabel("Size (#items)")
    axs[0].legend(loc="upper left")
    axs[0].bar_label(p, label_type='center')
    p = axs[1].bar(best_budgets,best_l2s/(best_l1s+best_l2s), width, label="L2", bottom=bottom, color=bottom_color)
    axs[1].bar_label(p, label_type='center')
    p = axs[1].bar(best_budgets, best_l1s / (best_l1s + best_l2s), width, label="L1", bottom=best_l2s/(best_l1s+best_l2s), color=top_color)
    axs[1].bar_label(p, label_type='center')
    axs[1].set_ylabel("Relative Sizes")
    axs[1].legend(loc="upper left")
    p = axs[2].plot(best_budgets, best_latencies)
    axs[2].set_ylabel("Latency (ms)")
    plt.xlabel("Budget ($/Month)")
    axs[0].set_title(trace + ":" + policy + ":" + storage + ":" + str(args.ramcost) + ":" + str(args.ssdcost) + ":" + str(args.unitsize))
    plt.savefig(os.path.join(args.outpath, trace + "_" + policy + "_" + storage + "_" + str(args.ramcost) + "_" + str(args.ssdcost) + "_" + str(args.unitsize) + ".png"), bbox_inches='tight')
    plt.close()


results = parse_input()
create_datasets(results)
for (trace, res) in results.items():
    for (policy, data) in res.items():
        if policy != 'nacceses':
            if args.verbose:
                print("Trace:", trace, " Policy:", policy, "Nacceses: ", results[trace]['nacceses'])
                print("Interpolating:",data)
            xs,ys = map(list, zip(*data))
            cs = CubicSpline(xs, ys, bc_type='not-a-knot', extrapolate=True)
            minx = min(xs)
            maxx = max(xs)
            if args.verbose:
                print("estimated HR:",cs([1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000, 20000, 30000, 40000, 50000, 60000, 70000, 80000, 90000, 100000, 200000, 300000, 400000, 500000, 600000, 700000, 800000, 900000, 1000000]))
            for storage, access_latency in storage_technologies.items():
                best_budgets = []
                best_l1s = []
                best_l2s = []
                best_latencies = []
                for total_budget in [100.0, 200.0, 300.0, 400.0, 500.0, 600.0, 700.0, 800.0, 900.0, 1000.0, 1100.0, 1200.0]:
                    total_budgets = np.full(8,total_budget)
                    l1_budgets = [0.01, 0.02, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5] * total_budgets
                    if args.verbose:
                        print("total_budgets:", total_budgets)
                        print("l1_budgets:", l1_budgets)
                    estimated_latencies = latency_estimation(total_budgets, l1_budgets, cs, results[trace]['nacceses'], minx, maxx, access_latency)
                    if args.verbose:
                        print("Min for budget ", total_budgets[0], " is ", np.min(estimated_latencies), " at ", np.argmin(estimated_latencies), " = ", l1_budgets[np.argmin(estimated_latencies)], "(",l1_budgets[np.argmin(estimated_latencies)]/total_budgets[0],")")
                        print("==================")
                    best_budgets.append(total_budget)
                    l1_best_budget = l1_budgets[np.argmin(estimated_latencies)]
                    best_l1s.append(l1_best_budget)
                    l2_best_budget = total_budget - l1_best_budget
                    best_l2s.append(l2_best_budget)
                    best_latencies.append(np.min(estimated_latencies))
                plot_budgets(trace, policy, storage, best_budgets, best_l1s, best_l2s, best_latencies)
            #input("Press the Enter key to continue: ")


