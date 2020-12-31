from common import start_client, start_server, kill_client, kill_server, cleanup, debug, parse_params, run_tput_exp
from parse_data import parse_log, convert_tput, parse_latencies, NUM_REQUESTS
import os
import argparse
from pathlib import Path
import heapq

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-a", "--analyze",
                        help = "Analyze only",
                        action = "store_true")
    parser.add_argument("-pp", "--pprint",
                        help = "Print out commands that will be run",
                        action="store_true")
    parser.add_argument("-y", "--yaml",
                        help = "Experiment yaml file.",
                        required=True)
    parser.add_argument("-sys", "--system",
                        choices = ["protobuf", "baseline",
                        "flatbuffers", "capnproto",
                        "malloc_baseline","protobytes", "malloc_no_str",
                        "memcpy", "single_memcpy"],
                        nargs="+", # for compatibility with the other script
                        help = "Which system to benchmark.",
                        default = "baseline")
    parser.add_argument("-seg", "--segments", type=int, help = "Number of segments in sga.", default = 1)
    parser.add_argument("-m", "--message",
                        help = "message",
                        default = "get")
    parser.add_argument("-o", "--libos",
                        help="libos to run",
                        choices = ["dmtr-lwip", "dmtr-rdma", "dmtr-posix"],
                        default = "dmtr-lwip")
    parser.add_argument("-n", "--num_clients",
                        type = int,
                        help = "Number of clients (for throughput benchmark)",
                        default = 1)
    parser.add_argument("-l", "--logfile",
                        help = "Base logfile.",
                        required = True)
    parser.add_argument("-c", "--clients",
                        help = "Number of client threads within the echo server.",
                        type = int,
                        default = 1)
    parser.add_argument("-s", "--size",
                        help = "Size of request",
                        type = int,
                        default = 100)
    parser.add_argument("-r", "--no_retries",
                        help = "Run without retries",
                        action = "store_true")
    parser.add_argument("-pf", "--perf",
                        help = "Run perf server side to observe cache statistics",
                        action = "store_true")
    parser.add_argument("-z", "--zero_copy",
                        help = "Zero copy mode on",
                        action = "store_true")
    return parser.parse_args()

def mean(arr):
    return sum(arr)/float(len(arr))

def analyze_exp(data, final_path, num_clients):
    avgs = []
    p99s = []
    medians = []
    all_retries = 0
    use_logged_latencies = True
    all_latencies = []
    for i in range(1, num_clients + 1):
        client_err = "{}/client{}.err.log".format(final_path, i)
        client_log = "{}/client{}.log".format(final_path, i)
        latencies_log = "{}/client{}.latencies.log".format(final_path, i)
        if not(os.path.exists(final_path)):
            debug("Path {} does not exist".format(final_path))
            return
        latencies = parse_log(client_err)
        latency_list = parse_latencies(latencies_log)
        if len(latency_list) != NUM_REQUESTS:
            use_logged_latencies = False
        else:
            all_latencies.append(latency_list) # to eventually sort them all
        
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
        # there could be concurrent clients per client folder
        tput = 1.0 * data["clients"] / avg * 1000
        tput_converted = convert_tput(tput, data["size"])
        debug("Client {} tput: {:.2f} req/ms | {:.2f} Gbps,avg latency: {:.2f} us, p99: {:.2f} us, median: {:.2f} us, {} retries".format(
            i, tput, tput_converted, avg, p99, median, retries))
    # full tput
    avg = mean(avgs)
    p99 = mean(p99s)
    median = mean(medians)
    tput = 1.0 * num_clients * data["clients"]/ (avg) * 1000
    tput_converted = convert_tput(tput, data["size"])
    # calculate true statistics
    if use_logged_latencies:
        sorted_latencies = list(heapq.merge(*all_latencies))
        median = sorted_latencies[int(len(sorted_latencies)/2)] / float(1000) # convert to us
        p99 = sorted_latencies[int(len(sorted_latencies) * .99)] / float(1000) # conver to us
    else:
        debug("For folder {}, using pre-caculated percentiles".format(final_path))
    debug("Tput: {:.2f} req/ms | {:.2f} Gbps, avg: {:.2f} us, median: {:.2f} us, p99: {:.2f} us, {} retries".format(
        tput, tput_converted,
        avg, median, p99, all_retries))




def main():
    args = parse_args()
    data = parse_params(args)
    data["size"] = args.size
    if not data["pprint"] and not args.analyze:
        cleanup(data)
    # setup folder 
    message = None if ("baseline" in data["system"]) else args.message
    exp = "{}clients".format(args.num_clients)
    if args.clients > 1:
        exp = "{}clients".format(args.num_clients * args.clients)
    full_path = "{}/{}/{}/size_{}/{}".format(
            args.logfile,
            data["system"],
            message,
            args.size,
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
        run_tput_exp(data, num_trials, args.size, args.num_clients, message)
        if not data["pprint"]:
            analyze_exp(data, full_path, args.num_clients)
    else:
        for n in range(0, num_trials):  
            debug("######Analysis for trial {}#######".format(num_trials - 1))
            trial = "trial_{}".format(n)
            path = full_path / trial
            analyze_exp(data, path, args.num_clients)
        

if __name__ == '__main__':
    main()
