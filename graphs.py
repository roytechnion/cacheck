import os.path
import matplotlib.pyplot as plt


def generate_weighted_graph(path,title,trace,policy,avoid,xlabel,ylabel,xvalues,aggresults,technologies):
    plt.figure(figsize=(1.8 * len(xvalues), 6))
    plt.rc('xtick', labelsize=18)
    plt.rc('ytick', labelsize=18)
    for technology in technologies:
        if technology != avoid:
            yvalues = list(map(lambda wat: wat[technology], aggresults[trace][policy].values()))
            plt.plot(xvalues, yvalues, label=technology)
    plt.xlabel(xlabel,fontsize=20)
    plt.ylabel(ylabel, fontsize=20)
    plt.legend()
    plt.savefig(os.path.join(path,trace+"-"+title+".png"), bbox_inches='tight')
    plt.close()


def init_hitrate_graph(numvalues):
    plt.figure(figsize=(1.5 * numvalues, 6))
    plt.rc('xtick', labelsize=18)
    plt.rc('ytick', labelsize=18)

def add_to_hitrate_graph(policy, xvalues, yvalues):
    plt.plot(xvalues, yvalues, label=policy)

def finish_hitrate_graph(path, trace):
    plt.xlabel("Cache Size",fontsize=20)
    plt.ylabel("Hit Ratio (%)", fontsize=20)
    plt.legend()
    plt.savefig(os.path.join(path,trace+"-hit_ratio.png"), bbox_inches='tight')
    plt.close()


def generate_hit_graph(path, aggresults):
    for trace in aggresults.keys():
        init_hitrate_graph(len((list(aggresults[trace].items()))[0][1].keys()))
        for policy in aggresults[trace].keys():
            sizes = aggresults[trace][policy].keys()
            hitratios = list(map(lambda ht: ht["hit ratio"], aggresults[trace][policy].values()))
            add_to_hitrate_graph(policy,sizes,hitratios)
        finish_hitrate_graph(path, trace)


def generate_all_weighted_graphs(path, aggresults, technologies):
    for trace in aggresults.keys():
        for policy in aggresults[trace].keys():
            sizes = aggresults[trace][policy].keys()
            generate_weighted_graph(path, "weighted-"+policy, trace, policy, "hit ratio", "Cache Size", "Access Time (ms)", sizes, aggresults, technologies)


def generate_all_graphs(path, aggresults, technologies):
    generate_hit_graph(path, aggresults)
    generate_all_weighted_graphs(path, aggresults, technologies)