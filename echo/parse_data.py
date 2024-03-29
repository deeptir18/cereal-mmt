import os
from pathlib import Path
import re
import sys
import argparse
import parse
from common import MESSAGES, SIZES, BASE_SIZE, debug, num_clients_list
import heapq
import math
import multiprocessing as mp
from statistics import mean
MAX_CLIENTS = 10
STRIP_PERCENT = .03

def mean_func(arr):
    return mean(arr)
def median_func(arr):
    return arr[int(len(arr) * 0.50)]
def p99_func(arr):
    return arr[int(len(arr) * 0.99)]

def convert_tput(tput, size):
    return tput * 1000 * size * 8 / 1000000000


def parse_num_clients(string):
    fmt = parse.compile("Number of clients: {}")
    num_clients = fmt.parse(string)
    return num_clients

def parse_latency_fmt(string):
    fmt = parse.compile("LATENCY end-to-end: {} {} {} {}/{} {} {} {} ({} samples, {} {} total)")
    lmin, min_unit, lavg, avg_unit, lmedian, median_unit, lmax, max_unit, num_samples, total, total_unit = fmt.parse(string)
    return {"min": lmin, "min-unit": min_unit,
            "avg-unit": avg_unit, "median": lmedian,
            "avg": lavg, "median-unit": median_unit,
            "max": lmax, "max-unit": max_unit,
            "total": total, "total-unit": total_unit}

def parse_tail_fmt(string):
    fmt = parse.compile("TAIL LATENCY 99={} {} 99.9={} {} 99.99={} {}")
    p99, p99_unit, p999, p999_unit, p9999, p9999_unit = fmt.parse(string)
    return {"p99": p99, "p99-unit": p99_unit,
            "p999": p999, "p999-unit": p999_unit,
            "p9999": p9999, "p9999-unit": p9999_unit}
def parse_retries(string):
    fmt = parse.compile("Final num retries: {}")
    retries, = fmt.parse(string)
    return retries
def string_to_dict(string, pattern):
    regex = re.sub(r'{(.+?)}', r'(?P<_\1>.+)', pattern)
    values = list(re.search(regex, string).groups())
    keys = re.findall(r'{(.+?)}', pattern)
    _dict = dict(zip(keys, values))
    return _dict



def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--logfile",
                        help = "Base logfile",
                        required = True)
    parser.add_argument("-a", "--append",
                        help = "Open file in append mode",
                        action = 'store_true')
    parser.add_argument("-o", "--outfile",
                        help = "Base outfile",
                        required = True)
    parser.add_argument("-sys", "--systems",
                        help = "Only parse these systems",
                        nargs = "+",
                        default = [])
    parser.add_argument("-s", "--sizes",
                        help = "Only parse these sizes",
                        type = int,
                        nargs = "+",
                        default = [])
    parser.add_argument('-n', "--num_clients",
                        help = "Only parse these num_clients",
                        type = int,
                        nargs = "+",
                        default = [])
    return parser.parse_args()

def parse_to_ns(num, unit):
    if unit == "ns":
        return num
    elif unit == "us":
        return num * 1000
    elif unit == "ms":
        return num * 1000000
    elif unit == "s":
        return num * 1000000000
    else:
        print("Unknown unit {}".format(unit))
        exit(1)

def parse_latency(matches, latency):
    for key in matches:
        if "unit" in key:
            continue
        else:
            num = int(matches[key])
            unit = matches["{}-unit".format(key)]
            latency[key] = parse_to_ns(num, unit)
    return latency

"""
Parses client log and returns dictionary of the various latencies
"""
def parse_log(logfile):
    latency = {}
    if not(os.path.exists(logfile)):
        debug("Logfile {} does not exist".format(logfile))
        return latency
    with open(logfile, "r") as f:
        for line in f:
            line = line.strip()
            if line.startswith("LATENCY"):
                # LATENCY end-to-end: 8176 ns 12 us/8192 ns 979 us (500000 samples, 6267 ms total)
                matches = parse_latency_fmt(line)
                parse_latency(matches, latency)
            if line.startswith("TAIL LATENCY"):
                matches = parse_tail_fmt(line)
                parse_latency(matches, latency)
            if line.startswith("Final num retries"):
                retries = parse_retries(line)
                latency["retries"] = retries
    return latency


def parse_folder(final_path, system, message, size, trial, num_clients):
    tputs = []
    p99s = []
    medians = []
    avgs = []
    all_retries = 0
    complete_latencies = []
    use_logged_latencies = True
    debug("Parsing folder {}", final_path)
    clients_list  = num_clients_list(num_clients)
    for (machines, concurrent) in clients_list:
        if machines * concurrent == num_clients:
            break
    for i in range(1, min(machines + 1, MAX_CLIENTS + 1)):
        client_err = "{}/client{}.err.log".format(final_path, i)
        client_log = "{}/client{}.log".format(final_path, i)
        latencies_log = "{}/client{}.latencies.log".format(final_path, i)
        if not(os.path.exists(final_path)):
            debug("Path {} does not exist".format(final_path))
            return ""
        retries = parse_log(client_log)
        latency_list = parse_latencies(latencies_log)
        complete_latencies.append(latency_list) # to eventually sort them all
        
        if len(retries) != 0:
            all_retries += int(retries["retries"])
        if len(latency_list) == 0:
            debug("Path {} has an error".format(final_path))
            return ""

    # take advantage of the fact that they're already sorted to make this faster
    sorted_latencies = list(heapq.merge(*complete_latencies))
    median = median_func(sorted_latencies) / float(1000)
    p99 = p99_func(sorted_latencies) / float(1000)
    avg = mean_func(sorted_latencies) / float(1000)
    tput = 1.0 * num_clients / avg * 1000
    tput_converted = convert_tput(tput, size)
    
    return "{},{},{},{},{},{},{},{},{},{}\n".format(
            system,size,message,num_clients,median,avg*1000,p99,tput,
            tput_converted,
            all_retries)

def parse_latencies(log):
    if not (os.path.exists(log)):
        debug("Path {} does not exist".format(log))
        return []
    with open(log) as f:
        raw_lines = f.readlines()
        lines = [int(line.strip()) for line in raw_lines]
    front_cutoff = int(len(lines) * STRIP_PERCENT)
    end_cutoff = int(len(lines) * (1.0 - STRIP_PERCENT))
    lines = lines[front_cutoff:end_cutoff]
    return sorted(lines)


def get_suffix(arg):
    try:
        return arg.split("_")[1]
    except:
        print(arg)
        exit(1)

def iterate(f, args):
    pool = mp.Pool(mp.cpu_count())
    pool_args = []
    current_path = Path(args.logfile)
    for system_name in os.listdir(args.logfile):
        if not(os.path.isdir(current_path / system_name)) or system_name == "plots":
            continue # extra files stored in directory
        if (len(args.systems) > 0 and system_name not in args.systems):
            debug("Skipping {}".format(system_name))
            continue
        for message in os.listdir(current_path / system_name):
            for size_name in os.listdir(current_path / system_name / message):
                size = int(get_suffix(size_name))
                if (len(args.sizes) > 0 and size not in args.sizes):
                    debug("Skipping system {} message {} size {}".format(system_name, message, size))
                    continue
                for clients_name in os.listdir(current_path / system_name / message / size_name):
                    num_clients = get_clients(clients_name)
                    if (len(args.num_clients) > 0 and num_clients not in args.num_clients):
                        debug("Skipping {}".format(num_clients))
                        continue
                    for trial_name in os.listdir((current_path / system_name / message / size_name / clients_name)):                    
                        trial = int(get_suffix(trial_name))
                        final_path = ( current_path / system_name / message / size_name / clients_name / trial_name)
                        pool_args.append([final_path, system_name, message,
                            size, trial, num_clients])
                            
    ret = pool.starmap(parse_folder, pool_args)
    for line in ret:
        if line != "":
            f.write(line)
                        
def get_clients(name):
    return int(name.replace("clients", ""))
def main():
    args = parse_args()
    outfile = "{}".format(args.outfile)
    if not (args.append):
        f =  open(outfile, "w")
    else:
        f = open(outfile, "a")
    f.write("system,size,message,num_clients,median,avg,p99,tput,tputgbps,retries\n")
    #size_graph(f, args)
    #depth_graph(f, args)
    iterate(f, args)
    f.flush()
    f.close()
    
if __name__ == '__main__':
    main()
