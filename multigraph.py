import csv
import argparse
import os
import matplotlib.pyplot as plt

parser = argparse.ArgumentParser()
parser.add_argument('-i', '--infile', action='store', default='multi-output.csv')
parser.add_argument('-d', '--indir', action='store', default='.')
args = parser.parse_args()

results = {}
with open(os.path.join(args.indir,args.infile), mode ='r') as file:
    print("opened")
    dictResults = csv.DictReader(file)
    for row in dictResults:
        trace = row['Trace']
        if trace not in results:
            results[trace] = {}
        L1_size = int(row[' L1_Size'])
        L2_size = int(row[' L2_Size'])
        total = L1_size + L2_size
        percentage = int(100 * L1_size / total)
        if total not in results[trace]:
            results[trace][total] = {}
        if percentage not in results[trace][total]:
            results[trace][total] = {}
        results[trace][total][percentage] = {}
        print("trace, total, percentage = ", trace, total, percentage)





