#format is pcap_automata_method_reductionratio.txt
#format in file real_error, precision, estimated_error(pruning has -1, because it doesnt count)
import numpy
import matplotlib.pyplot as plt

def get_results(method, automata, pcap, ratios):
    all_results = []

    for rat in ratios:
        if numpy.allclose(rat % 0.1, 0):
            rat = "%.1f" % rat
        else:
            rat = "%.2f" % rat
        file_name = f"results/{pcap}_{automata}_{method}_{rat}.txt"
        results = numpy.loadtxt(file_name, delimiter=",")
        all_results.append(results)
    all_results = numpy.asarray(all_results)
    return all_results


def plot_whatever(pcap, automatas, num):

    ratios = numpy.arange(0.1, 0.62, 0.02)

    plt.rc('text', usetex=True)    
    plt.rcParams.update({'font.size': 14})


    fig, axs = plt.subplots(nrows=3,ncols=2, figsize=(12,9), num=num,
                            sharex=True)

    for i, automata in enumerate(automatas):

        p_results = get_results("p", automata, pcap, ratios)
        fp_results = get_results("fp",automata, pcap, ratios)
            
        gt_pos = numpy.where(fp_results[:,2] > 1)
        # print(gt_pos)
        fp_results[gt_pos, 2] = 1

        axs[i, 0].set_title(f"{automata}  {pcap}")
        axs[i, 1].set_title(f"{automata}  {pcap}")

        axs[i, 0].plot(ratios, p_results[:,0], "-", color = 'C0', 
                       label="pruning")
        axs[i, 0].plot(ratios, fp_results[:,0], "-", color = 'C1', 
                       alpha=0.5, label="frequency pruning")
        axs[i, 0].plot(ratios, fp_results[:,2], "-", color="C2", 
                       alpha=0.6, label="estimated error")

        axs[i, 1].plot(ratios, p_results[:,1], "-", color="C0")
        axs[i, 1].plot(ratios, fp_results[:,1], "-", color="C1", alpha=0.5)


        axs[i, 0].set_xlim([0.1, 0.36])
        axs[i, 1].set_xlim([0.1, 0.36])

        axs[i, 0].set_xlabel("reduction ratio")
        axs[i, 0].set_ylabel("error")

        axs[i, 1].set_xlabel("reduction ratio")
        axs[i, 1].set_ylabel("precision")
        axs[0, 0].legend(loc="best")
        axs[i, 0].grid(alpha=0.5, linestyle="--")
        axs[i, 1].grid(alpha=0.5, linestyle="--")

    plt.tight_layout()
    plt.savefig(f"plots/{num}.pdf", dpi=300)
    plt.savefig(f"plots/{num}.png", dpi=300)


pcaps = ["darpa-1998-training-week1-friday.pcap", 
         "darpa-1998-training-week3-tuesday2.pcap"]

automatas = ["spyware-put.rules.fa", "pop3.rules.fa", "backdoor.rules.fa",
            "l7-all.fa","imap.rules.fa", "ftp.rules.fa"]

plot_whatever(pcaps[0], automatas[0:3], 1)
plot_whatever(pcaps[0], automatas[3:], 2)

plot_whatever(pcaps[1], automatas[0:3], 3)
plot_whatever(pcaps[1], automatas[3:], 4)

plt.show()
