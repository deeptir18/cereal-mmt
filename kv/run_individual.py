from common import cleanup, debug, run_exp, parse_params, get_parser
from parse_data import parse_log, convert_tput
import os
import argparse
from pathlib import Path

def parse_args():
    parser = get_parser()
    parser.add_argument("-a", "--analyze",
                        help = "Analyze only",
                        action = "store_true")
    parser.add_argument("-w", "--workload",
                        help = "Workload",
                        choices = ["workloada", "workloadb", "workloadc",
                        "workloadd"],
                        required = True)
    return parser.parse_args()

def mean(arr):
    return sum(arr)/float(len(arr))

def analyze_exp(data, final_path, num_clients):
    avgs = []
    p99s = []
    medians = []
    all_retries = 0
    for i in range(1, num_clients + 1):
        client_err = "{}/client{}.err.log".format(final_path, i)
        client_log = "{}/client{}.log".format(final_path, i)
        if not(os.path.exists(final_path)):
            debug("Path {} does not exist".format(final_path))
            return
        latencies = parse_log(client_err)
        retries_dict = parse_log(client_log)
        if len(retries_dict) > 0:
            retries = int(retries_dict["retries"])
        else:
            retries = 0
        avg = latencies["avg"]/float(1000) # microseconds
        p99 = latencies["p99"]/float(1000) # microseconds
        median = latencies["median"]/float(1000) # microseconds
        avgs.append(avg)
        p99s.append(p99)
        medians.append(median)
        all_retries += retries
        tput = 1.0 / avg * 1000
        debug("Client {} tput: {:.2f} req/ms ,avg latency: {:.2f} us, p99: {:.2f} us, median: {:.2f} us, {} retries".format(i, tput, avg, p99, median, retries))
    # full tput
    avg = mean(avgs)
    p99 = mean(p99s)
    median = mean(medians)
    tput = 1.0 * num_clients / (avg) * 1000
    debug("Tput: {:.2f} req/ms, avg: {:.2f} us, median: {:.2f} us, p99: {:.2f} us, {} retries".format(tput, avg, median, p99, all_retries))

def main():
    args = parse_args()
    data = parse_params(args)
    cleanup(data)
    # setup folder 
    exp = "{}clients".format(args.num_clients)
    workload = data["workload"]
    full_path = "{}/{}/{}/{}".format(
            args.logfile,
            args.system,
            workload,
            exp)
    full_path = Path(full_path)

    # count the number of trials already in this directory
    num_trials = 0
    if os.path.exists(full_path):
        for folder in os.listdir(full_path):
            if not(os.path.isdir(full_path / folder)):
                continue
            if "trial" in folder:
                num_trials += 1
    if not(args.analyze):
        trial = "trial_{}".format(num_trials)
        full_path = full_path / trial
        run_exp(data, num_trials, args.workload, args.num_clients)
        analyze_exp(data, full_path, args.num_clients)
    else:
        for n in range(0, num_trials):
            debug("######Analysis for trial {}#######".format(num_trials - 1))
            trial = "trial_{}".format(n)
            path = full_path / trial
            analyze_exp(data, path, args.num_clients)
        
if __name__ == '__main__':
    main()
