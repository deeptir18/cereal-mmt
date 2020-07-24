import os
from pathlib import Path
import re
import sys
import argparse
import parse
from common import MESSAGES, SIZES, BASE_SIZE, debug
NUM_REQUESTS = 500000

def convert_tput(tput, size):
    return tput * 1000 * size * 8 / 1000000000


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
    parser.add_argument("-o", "--outfile",
                        help = "Base outfile",
                        required = True)
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


def parse_folder(f, final_path, system, message, size, trial, num_clients):
    tputs = []
    p99s = []
    medians = []
    avgs = []
    all_retries = 0
    for i in range(1, num_clients + 1):
        client_err = "{}/client{}.err.log".format(final_path, i)
        client_log = "{}/client{}.log".format(final_path, i)
        if not(os.path.exists(final_path)):
            debug("Path {} does not exist".format(final_path))
            return
        latencies = parse_log(client_err)
        retries = parse_log(client_log)
        if len(retries) != 0:
            all_retries += int(retries["retries"])
        if len(latencies) == 0:
            debug("Path {} has an error".format(final_path))
            return
        avg = latencies["avg"]/float(1000000) # milliseconds
        p99 = latencies["p99"]/float(1000) # microseconds
        median = latencies["median"]/float(1000) # microseconds
        avgs.append(avg)
        p99s.append(p99)
        medians.append(median)
    avg = float(sum(avgs)) / len(avgs)
    tput = float(num_clients) / avg
    tput_converted = convert_tput(tput, size)
    median = float(sum(medians)) / len(medians)
    p99 = max(p99s)
    f.write("{},{},{},{},{},{},{},{},{},{}\n".format(
            system,size,message,num_clients,median,avg*1000,p99,tput,
            tput_converted,
            all_retries))

def get_suffix(arg):
    try:
        return arg.split("_")[1]
    except:
        print(arg)
        exit(1)

def iterate(f, args):
    current_path = Path(args.logfile)
    for system_name in os.listdir(args.logfile):
        if not(os.path.isdir(current_path / system_name)):
            continue # extra files stored in directory
        for message in os.listdir(current_path / system_name):
            for size_name in os.listdir(current_path / system_name / message):
                size = int(get_suffix(size_name))
                for clients_name in os.listdir(current_path / system_name / message / size_name):
                    num_clients = int(clients_name[0])
                    for trial_name in os.listdir((current_path / system_name / message / size_name / clients_name)):                    
                        trial = int(get_suffix(trial_name))
                        final_path = ( current_path / system_name / message / size_name / clients_name / trial_name)
                        parse_folder(f, final_path, system_name, message, size, trial, num_clients)
                        

def main():
    args = parse_args()
    outfile = "{}.log".format(args.outfile)
    f =  open(outfile, "w")
    f.write("system,size,message,num_clients,median,avg,p99,tput,tputgbps,retries\n")
    #size_graph(f, args)
    #depth_graph(f, args)
    iterate(f, args)
    f.flush()
    f.close()
    
if __name__ == '__main__':
    main()
