import argparse
import os
import sys
import multiprocessing
from fabric import Connection
import yaml
import time 
"""
Goal of this script: common functions to run a simple benchmark.
Usage:
    python common.py --yaml <config-file> --system <protobuf,baseline>
    --experiment<size,depth> --num_clients <int> --libos
    <dmtr-lwip,dmtr-rdma,dmtr-posix> --logfile <logpath>
- What is the speed of typing into this.
- It seems reasonable fast!!!!  no it's pretty slow
- Protobuf variation supported:
    (1) size of protobuf being processed for a basic GetMessage
    (2) the complexity of the protobuf (number of leaves in a binary tree)
- Experiments:
    (1) Protobuf vs. non encoded message latency while size varies
    (2) Protobuf complexity
- Measurements:
    (1) Latency of requests on a single server (probably average and tail)
    (2) Throughput server can sustain with multiple clients (don't care about
    scalability, just pick a number of clients to run the experiment from)
"""
## CONSTANTS #########################################################
SIZES = [100, 500, 1000, 2000, 4000, 4096, 6000, 8000]
BASE_MESSAGE = "Get"
BASE_SIZE = 4096
MESSAGES = ["Get", "Msg1L", "Msg2L",
            "Msg3L", "Msg4L", "Msg5L"]
NUM_TRIALS = 5
######################################################################
def debug(*args):
    prepend = "\u2192"
    print(prepend, *args, file=sys.stderr)

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-y", "--yaml",
                        help = "Experiment yaml file.",
                        required=True)
    parser.add_argument("-s", "--system",
                        choices = ["protobuf", "baseline",
                        "flatbuffers", "capnproto"],
                        help = "Which system to benchmark.",
                        required=True)
    parser.add_argument("-e", "--experiment",
                        choices = ["size", "depth"],
                        required = True)
    parser.add_argument("-n", "--num_clients",
                        type = int,
                        help = "Number of clients (for throughput benchmark)",
                        default = 1)
    parser.add_argument("-o", "--libos",
                        help="libos to run",
                        choices = ["dmtr-lwip", "dmtr-rdma", "dmtr-posix"],
                        default = "dmtr-lwip")
    parser.add_argument("-l", "--logfile",
                        help = "Base logfile.",
                        required = True)
    parser.add_argument("-p", "--pprint",
                        help = "Print out commands that will be run",
                        action="store_true")
    parser.add_argument("-r", "--no_retries",
                        help = "Run without retries",
                        action = "store_true")
    parser.add_argument("-c", "--clients",
                        help = "Number of client threads within the echo server.",
                        type = int,
                        default = 1)
    parser.add_argument("-pf", "--perf",
                        help = "Run perf server side to observe cache statistics",
                        action = "store_true")
    return parser.parse_args()

def calculate_log_path(args, trial, exp, size, message = None):
    if args["system"] == "baseline":
        return "{}/baseline/{}/size_{}/{}/trial_{}".format(
                args["logfile"],
                message,
                size,
                exp,
                trial)
    else:
        assert(message != None)
        return "{}/{}/{}/size_{}/{}/trial_{}".format(
                args["logfile"],
                args["system"], # could be protobuf, capnproto, proto3
                message,
                size,
                exp,
                trial)

def connection(args, host):
    cxn = Connection(host = host,
                        user = args["user"],
                        port = 22,
                        connect_kwargs = {"key_filename": args["key"]})
    return cxn


# kill any rogue processes on server
def cleanup(args):
    cleanup_server(args)
    for idx in range(1, args["num_clients"] + 1):
        kill_client(args, idx)
    debug("Done with cleanup, starting experiment.")

def start_server(args, trial, exp, size, message = None):
    # prepare the logpath
    # for perf: prepend something like
    # perf stat -e task-clock,cycles, instructions,cache-references,cache-misses
    #  sudo perf stat -e L1-dcache-loads,L1-dcache-load-misses,L1-dcache-stores
    
    os.makedirs(calculate_log_path(args, trial, exp, size, message), exist_ok = True) 
    cmd = "sudo "
    if args["perf"]:
        debug("Running with perf")
        cmd += "perf stat -e "
        cmd += "task-clock,cycles,instructions,cache-references,cache-misses"
        cmd += ",L1-dcache-loads,L1-dcache-load-misses,L1-dcache-stores"
        cmd += ",dTLB-loads,dTLB-load-misses,dTLB-prefetch-misses"
        cmd += ",LLC-loads,LLC-load-misses,LLC-stores,LLC-prefetch"
    cmd += " {exec_dir}/{libos}-server --port {port} --config-path {config_path}".format(**args)
    host = args["hosts"]["server"]["addr"]

    cmd += " -s {}".format(size)
    
    if message is not None:
        cmd += " --system {} --message {}".format(args["system"], message)
    
    logpath = "{}/server".format(calculate_log_path(args, trial, exp, size,
        message))
    cmd += " > {} 2> {}".format("{}.log".format(logpath),
            "{}.err.log".format(logpath))
    
    if args["pprint"]:
        debug(host, ": ", cmd)
    
    proc = multiprocessing.Process(target = run_cmd, args=(cmd, host, args, True))
    return proc

def start_client(args, idx, trial, exp, size, message = None):
    cmd = "sudo {exec_dir}/{libos}-client --port {port} --config-path {config_path} -i {iterations}".format(**args)
    if args["retry"]:
        cmd += " --retry"
    cmd += " -s {}".format(size)
    cmd += " -c {}".format(args["clients"])
    host = args["hosts"]["client{}".format(idx)]["addr"]

    if message is not None:
        cmd += " --system {} --message {}".format(args["system"], message)

    logpath = "{}/client{}".format(calculate_log_path(args, trial, exp, size,
        message), idx)
    cmd += " > {} 2> {}".format("{}.log".format(logpath),
            "{}.err.log".format(logpath))
    if args["pprint"]:
        debug(host, ": ", cmd)
        return
    
    proc = multiprocessing.Process(target = run_cmd, args = (cmd, host, args))
    return proc

def cleanup_server(args):
    host = args["hosts"]["server"]["addr"]
    cxn = connection(args, host)
    try:
        cxn.sudo("sudo kill  -9 `ps aux | grep {exec_dir}/{libos}-server | awk '{{print $2}}' | head -n4`".format(**args), hide = True)
    except:
        return False


def kill_server(args):
    host = args["hosts"]["server"]["addr"]
    cxn = connection(args, host)
    try:
        # send 2 -> interrupt from keyboard
        cxn.sudo("sudo kill -9 `ps aux | grep {exec_dir}/{libos}-server | awk '{{print $2}}' | head -n3`".format(**args), hide = True)
        time.sleep(10)
        debug("Killed server")
        return
    except:
        return False

def kill_client(args, idx):
    host = args["hosts"]["client{}".format(idx)]["addr"]
    cxn = connection(args, host)
    try:
        # send 2 -> interrupt from keyboard
        cxn.sudo("sudo kill  -9 `ps aux | grep {exec_dir}/{libos}-client | awk '{{print $2}}' | head -n3`".format(**args), hide = True)
        time.sleep(2)
    except:
        return False

def run_cmd(cmd, host, args, fail_ok = False):
    cxn = connection(args, host)
    try:
        res = cxn.sudo(cmd, hide = True)
        res.stdout.strip()
        return
    except:
        if not fail_ok: 
            debug("Failed to run cmd {} on host {}.".format(cmd, host))

        return
def run_tput_exp(args, trial, size, num_clients, message = None):
    # start server
    exp = "{}clients".format(num_clients)
    if os.path.exists(calculate_log_path(args, trial, exp, size, message)):
        debug("Exp: trial {}, size {}, system {}, message {}, clients {} exists, skipping".format(
            trial,
            size,
            args["system"],
            message,
            num_clients))
        return
    debug("Running exp: trial {}, size {}, system {}, message {}, clients {}".format(
            trial,
            size,
            args["system"],
            message,
            num_clients))
    server_proc = start_server(args, trial, exp, size, message)
    if not args["pprint"]:
        server_proc.start()
        time.sleep(3)
    
    # start each client
    client_procs = []
    for i in range(1, num_clients + 1):
        client_procs.append(start_client(args, i, trial, exp, size, message))
    
    if args["pprint"]:
        return

    # start and join each client and kill server
    for proc in client_procs:
        proc.start()

    for proc in client_procs:
        proc.join()
        debug("\u2192Client done.")
    kill_server(args)
    return

def cycle_exps(args):
    for trial in range(0, NUM_TRIALS):
        if args["experiment"] == "size":
            for size in SIZES:
                if size == BASE_SIZE:
                    continue
                for num_clients in range(1, args["num_clients"] + 1):
                    message = BASE_MESSAGE if args["system"] != "baseline" else None
                    run_tput_exp(args, trial, size, num_clients, message)
        else:
            for message in MESSAGES:
                for num_clients in range(1, args["num_clients"] + 1):
                    run_tput_exp(args, trial, BASE_SIZE, num_clients, message)


def parse_params(args):
    with open(args.yaml) as f:
        data = yaml.load(f)

    data["libos"] = args.libos # lwip, rdma, posix
    data["system"] = args.system # currently: baseline, protobuf
    data["num_clients"] = args.num_clients # number of available clients to
    data["logfile"] = args.logfile # folder
    data["pprint"] = args.pprint # just print commands
    data["clients"] = args.clients
    data["perf"] = args.perf
    data["retry"] = True if (not(args.no_retries)) else False
    if "experiment" in args:
        data["experiment"] = args.experiment # size or depth
        if args.experiment == "depth":
            assert(args.system != "baseline")
    return data


def main():
    args = parse_args()
    data = parse_params(args)
    # run cleanup
    cleanup(data)
    cycle_exps(data)

    
if __name__ == '__main__':
    main()