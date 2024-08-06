import csv
import argparse
import os
import matplotlib.pyplot as plt
from matplotlib import cm
import numpy as np


parser = argparse.ArgumentParser()
parser.add_argument('-i', '--infile', action='store', default='multi-output.csv')
parser.add_argument('-d', '--indir', action='store', default='.')
parser.add_argument('-o', '--outdir', action='store', default='.\\graphs\\multilevel')
args = parser.parse_args()


def multiplot_storage(storage,traceresults,X,Y,_x,_y):
    fig = plt.figure(figsize=plt.figaspect(1))
    ax = fig.add_subplot(1, 2, 1, projection='3d')
    _Z, _ = np.meshgrid(X, Y)
    #Z = np.zeros((len(X), len(Y)))
    #print(Z)
    for total, totalresults in traceresults.items():
        for percentage, percentageresults in totalresults.items():
            print(total, percentage)
            #Z[np.where(X == total)[0][0], np.where(Y == percentage)[0][0]] = results[trace][total][percentage][storage]
            _Z[np.where(Y == percentage)[0][0], np.where(X == total)[0][0]] = results[trace][total][percentage][storage]
    print("Z=", _Z)
    fig, ax = plt.subplots(subplot_kw={"projection": "3d"})
    surf = ax.plot_surface(_X, _Y, _Z, cmap=cm.coolwarm)
    fig.colorbar(surf, shrink=0.5, aspect=5)
    plt.xlabel("Total Cache Size")
    plt.ylabel("L1 Relative Size")
    ax.set_title(trace + ":" + storage)
    plt.savefig(os.path.join(args.outdir, trace.split(".")[0] + "-" + storage + ".png"), bbox_inches='tight')
    plt.close()


results = {}
with open(os.path.join(args.indir,args.infile), mode ='r') as file:
    print("opened")
    dictResults = csv.DictReader(file)
    for row in dictResults:
        trace = row['Trace']
        if trace not in results:
            results[trace] = {}
        L1_size = int(row['L1_Size'])
        L2_size = int(row['L2_Size'])
        total = L1_size + L2_size
        percentage = round(float(L1_size / total),2)
        if total not in results[trace]:
            results[trace][total] = {}
        if percentage not in results[trace][total]:
            results[trace][total][percentage] = {}
        results[trace][total][percentage]['L1_Hit_Ratio'] = float(row['L1_Hit_Ratio'])
        results[trace][total][percentage]['L2_Hit_Ratio'] = float(row['L2_Hit_Ratio'])
        results[trace][total][percentage]['Total_Hit_Ratio'] = float(row['Total_Hit_Ratio'])
        results[trace][total][percentage]['L1_Accesses'] = int(row['L1_Accesses'])
        results[trace][total][percentage]['L2_Accesses'] = int(row['L2_Accesses'])
        results[trace][total][percentage]['Remote_Accesses'] = int(row['Remote_Accesses'])
        results[trace][total][percentage]['L1_Charged'] = int(row['L1_Charged'])
        results[trace][total][percentage]['L2_Charged'] = int(row['L2_Charged'])
        results[trace][total][percentage]['Remote_Charged'] = int(row['Remote_Charged'])
        results[trace][total][percentage]['WeightedFastDB'] = float(row[' WeightedFastDB'])
        results[trace][total][percentage]['WeightedModDB'] = float(row[' WeightedModDB'])
        results[trace][total][percentage]['WeightedSlowDB'] = float(row[' WeightedSlowDB'])
    for trace,traceresults in results.items():
        print(trace)
        X = []
        Y = []
        for total,totalresults in traceresults.items():
            if total not in X:
                X.append(total)
            for percentage,percentageresults in totalresults.items():
                if percentage not in Y:
                    Y.append(percentage)
        X = np.array(X)
        Y = np.array(Y)
        _X, _Y = np.meshgrid(X, Y)
        print(_X)
        print(_Y)
        for storage in ["FastDB","ModDB","SlowDB"]:
            multiplot_storage("Weighted"+storage,traceresults,X,Y,_X,_Y)
        #plt.show()
        #input("Press the Enter key to continue: ")







