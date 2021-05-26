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
: Experiments:
    (1) Protobuf vs. non encoded message latency while size varies
    (2) Protobuf complexity
- Measurements:
    (1) Latency of requests on a single server (probably average and tail)
    (2) Throughput server can sustain with multiple clients (don't care about
    scalability, just pick a number of clients to run the experiment from)
"""
## CONSTANTS #########################################################
#SIZES = [100, 500, 1000, 2000, 4000, 4096, 6000, 8000]
# SIZES = [128, 256, 512, 768, 1024, 2048, 4096, 8192] # for the PCIe experiments
# SIZES = [64, 128, 256, 512, 1024, 2048, 4096, 8192
SIZES = [1024]
BASE_MESSAGE = "Get"
BASE_SIZE = 4096
MESSAGES = ["Get", "Msg1L", "Msg2L",
            "Msg3L", "Msg4L", "Msg5L"]
NUM_TRIALS = 10  # finish trials 4 and 5 later
MAX_CLIENTS = 10
######################################################################


def debug(*args):
    prepend = "\u2192"
    print(prepend, *args, file=sys.stderr)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-y", "--yaml",
                        help="Experiment yaml file.",
                        required=True)
    parser.add_argument("-s", "--system",
                        choices=["protobuf", "baseline",
                                 "flatbuffers", "capnproto", "cornflakes",
                                 "malloc_baseline", "protobytes", "malloc_no_str",
                                 "memcpy", "single_memcpy"],
                        nargs="+",
                        help="Which system to benchmark.",
                        required=True)
    parser.add_argument("-seg", "--segments", type=int,
                        help="Number of segments in sga.", default=1)
    parser.add_argument("-e", "--experiment",
                        choices=["size", "depth"],
                        required=True)
    parser.add_argument("-n", "--num_clients",
                        type=int,
                        help="Number of clients (for throughput benchmark)",
                        default=1)
    parser.add_argument("-o", "--libos",
                        help="libos to run",
                        choices=["dmtr-lwip", "dmtr-rdma", "dmtr-posix"],
                        default="dmtr-lwip")
    parser.add_argument("-l", "--logfile",
                        help="Base logfile.",
                        required=True)
    parser.add_argument("-p", "--pprint",
                        help="Print out commands that will be run",
                        action="store_true")
    parser.add_argument("-r", "--no_retries",
                        help="Run without retries",
                        action="store_true")
    parser.add_argument("-c", "--clients",
                        help="Number of client threads within the echo server.",
                        type=int,
                        default=1)
    parser.add_argument("-pf", "--perf",
                        help="Run perf server side to observe cache statistics",
                        action="store_true")
    parser.add_argument("-z", "--zero_copy",
                        help="Zero copy mode on",
                        action="store_true")
    return parser.parse_args()


def calculate_log_path(args, trial, exp, size, message=None):
    if "baseline" in args["system"]:
        return "{}/{}/{}/size_{}/{}/trial_{}".format(
            args["logfile"],
            args["system"],
            message,
            size,
            exp,
            trial)
    else:
        assert(message != None)
        return "{}/{}/{}/size_{}/{}/trial_{}".format(
            args["logfile"],
            args["system"],  # could be protobuf, capnproto, proto3
            message,
            size,
            exp,
            trial)


def connection(args, host):
    cxn = Connection(host=host,
                     user=args["user"],
                     port=22,
                     connect_kwargs={"key_filename": args["key"]})
    return cxn


# kill any rogue processes on server
def cleanup(args):
    cleanup_server(args)
    for idx in range(1, 11):
        kill_client(args, idx)
    debug("Done with  cleanup, starting experiment.")


def start_server(args, trial, exp, size, message=None):
    # prepare the logpath
    # for perf: prepend something like
    # perf stat -e task-clock,cycles, instructions,cache-references,cache-misses
    #  sudo perf stat -e L1-dcache-loads,L1-dcache-load-misses,L1-dcache-stores
    if not args["pprint"]:
        os.makedirs(calculate_log_path(
            args, trial, exp, size, message), exist_ok=True)
    cmd = "sudo nice -n -20 taskset 0x1 "
    if args["perf"]:
        debug("Running with perf")
        cmd += "perf stat -e "
        cmd += "task-clock,cycles,instructions,cache-references,cache-misses"
        cmd += ",L1-dcache-loads,L1-dcache-load-misses,L1-dcache-stores"
        cmd += ",dTLB-loads,dTLB-load-misses,dTLB-prefetch-misses"
        cmd += ",LLC-loads,LLC-load-misses,LLC-stores,LLC-prefetch"
    cmd += " {exec_dir}/{libos}-server --port {port} --config-path {config_path}".format(
        **args)
    host = args["hosts"]["server"]["addr"]

    cmd += " -s {}".format(size)

    if message is not None:
        cmd += " --system {} --message {}".format(args["system"], message)

    if args["segments"] > 1:
        cmd += " --sgasize {}".format(args["segments"])
    # for the zero copy experiments
    if args["zero_copy"]:
        cmd += " --zero-copy"
    logpath = "{}/server".format(calculate_log_path(args, trial, exp, size,
                                                    message))
    cmd += " > {} 2> {}".format("{}.log".format(logpath),
                                "{}.err.log".format(logpath))

    if args["pprint"]:
        debug(host, ": ", cmd)

    proc = multiprocessing.Process(
        target=run_cmd, args=(cmd, host, args, True))
    return proc


def start_client(args, idx, trial, exp, size, message=None, iteration_multiplier=1):
    original_iterations = args["iterations"]
    args["iterations"] = original_iterations * args["clients"]
    cmd = "sudo {exec_dir}/{libos}-client --port {port} --config-path {config_path} -i {iterations}".format(
        **args)
    if args["retry"]:
        cmd += " --retry"
    cmd += " -s {}".format(size)
    cmd += " -c {}".format(args["clients"])
    host = args["hosts"]["client{}".format(idx)]["addr"]

    if message is not None:
        cmd += " --system {} --message {}".format(args["system"], message)
    # for zero copy
    if args["zero_copy"]:
        cmd += " --zero-copy"

    logpath = "{}/client{}".format(calculate_log_path(args,
                                   trial, exp, size, message), idx)
    if args["segments"] > 1:
        cmd += " --sgasize {}".format(args["segments"])

    # record all the latencies
    cmd += " --latlog {}.latencies.log".format(logpath)
    cmd += " > {} 2> {}".format("{}.log".format(logpath),
                                "{}.err.log".format(logpath))
    if args["pprint"]:
        debug(host, ": ", cmd)
        return

    proc = multiprocessing.Process(target=run_cmd, args=(cmd, host, args))
    args["iterations"] = original_iterations
    return proc


def cleanup_server(args):
    host = args["hosts"]["server"]["addr"]
    cxn = connection(args, host)
    try:
        cxn.sudo(
            "sudo kill  -9 `ps aux | grep {exec_dir}/{libos}-server | awk '{{print $2}}' | head -n3`".format(**args), hide=True)
        time.sleep(10)
        cxn.sudo("sudo killall {libos}-server".format(**args), hide=True)
        debug("Killed server")
    except:
        try:
            cxn.sudo("sudo killall {libos}-server".format(**args), hide=True)
            debug("Used killall to kill server")
        except:
            return False
        return False


def kill_server(args):
    host = args["hosts"]["server"]["addr"]
    cxn = connection(args, host)
    try:
        cxn.sudo(
            "sudo kill -9 `ps aux | grep {exec_dir}/{libos}-server | awk '{{print $2}}' | head -n3`".format(**args), hide=True)
        time.sleep(10)
        cxn.sudo("sudo killall {libos}-server".format(**args), hide=True)
        debug("Killed server")
        return
    except:
        try:
            cxn.sudo("sudo killall {libos}-server".format(**args), hide=True)
            debug("Used killall to kill server")
        except:
            return False
        return False


def kill_client(args, idx):
    host = args["hosts"]["client{}".format(idx)]["addr"]
    cxn = connection(args, host)
    try:
        # send 2 -> interrupt from keyboard
        cxn.sudo(
            "sudo kill  -9 `ps aux | grep {exec_dir}/{libos}-client | awk '{{print $2}}' | head -n3`".format(**args), hide=True)
        time.sleep(2)
    except:
        return False


def run_cmd(cmd, host, args, fail_ok=False):
    cxn = connection(args, host)
    try:
        res = cxn.sudo(cmd, hide=True)
        res.stdout.strip()
        return
    except:
        if not fail_ok:
            debug("Failed to run cmd {} on host {}.".format(cmd, host))

        return


def run_tput_exp(args, trial, size, num_clients, message=None):
    # if num_clients > MAX_CLIENTS but < MAX_CLIENTS * 2 (non-integer), need to
    # know how many clients per script
    debug("Num clients: {}".format(num_clients))
    # start server
    exp = "{}clients".format(num_clients)
    if args["clients"] > 1:
        exp = "{}clients".format(num_clients * args["clients"])
    if os.path.exists(calculate_log_path(args, trial, exp, size, message)):
        debug("Exp: trial {}, size {}, system {}, message {}, clients {} exists, skipping".format(
            trial,
            size,
            args["system"],
            message,
            num_clients * args["clients"]))
        return
    debug("Running exp: trial {}, size {}, system {}, message {}, clients {}".format(
        trial,
        size,
        args["system"],
        message,
        num_clients * args["clients"]))
    server_proc = start_server(args, trial, exp, size, message)
    if not args["pprint"]:
        server_proc.start()
        time.sleep(3)

    # start each client
    client_procs = []
    for i in range(1, min(MAX_CLIENTS + 1, num_clients + 1)):
        iteration_multiplier = 1
        client_procs.append(start_client(
            args, i, trial, exp, size, message, iteration_multiplier))

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
    original_clients = args["clients"]
    for trial in range(0, NUM_TRIALS):
        # cycle through all the systems provided
        for system in args["systems"]:
            debug("Cycling for system {}.".format(system))
            args["system"] = system
            if args["experiment"] == "size":
                for size in reversed(SIZES):
                    for (num_clients, concurrent) in args["clients_list"]:
                        args["clients"] = concurrent
                        message = BASE_MESSAGE if "baseline" not in args["system"] else None
                        run_tput_exp(args, trial, size, num_clients, message)
                        args["clients"] = original_clients
            else:
                for message in MESSAGES:
                    for num_clients in args["clients_list"]:
                        if num_clients > MAX_CLIENTS:
                            num_clients = MAX_CLIENTS
                            args["clients"] = num_clients / MAX_CLIENTS
                        #debug("Exp: sys {}, size {}, message {}, num clients {}, concurrent clients {}".format(args["system"], size, message, num_clients, args["clients"]))
                        run_tput_exp(args, trial, BASE_SIZE,
                                     num_clients, message)
                        args["clients"] = original_clients


def num_clients_list(num_clients):
    # this is just to define which numbers of clients to cycle through
    divisor = 2
    ret = [(1, 1)]
    ret.extend([(x, 2) for x in range(1, 9)])
    # return [(10,2)]
    return ret
    divisors = [2, 3, 4, 5, 6]
    if (num_clients <= MAX_CLIENTS * 2):
        return [num for num in range(1, num_clients + 1)]
    else:
        # must be divisble by MAX_CLIENTS
        if (num_clients % MAX_CLIENTS != 0):
            debug("Num clients must be divisible by {}".format(MAX_CLIENTS))
            exit(1)
        divisor = int(num_clients / MAX_CLIENTS)
        clients = [num for num in range(1, MAX_CLIENTS + 1)]
        for d in divisors:
            if d <= divisor:
                clients.append(MAX_CLIENTS * d)
        print(clients)
        return clients


def parse_params(args):
    with open(args.yaml) as f:
        data = yaml.load(f)

    data["libos"] = args.libos  # lwip, rdma, posix
    data["systems"] = args.system  # all of them
    if len(args.system) == 1:
        # for run individual script, just set the first
        data["system"] = args.system[0]
    data["num_clients"] = args.num_clients  # number of available clients to
    data["clients_list"] = num_clients_list(data["num_clients"])
    data["logfile"] = args.logfile  # folder
    data["pprint"] = args.pprint  # just print commands
    data["clients"] = args.clients
    data["perf"] = args.perf
    data["zero_copy"] = args.zero_copy
    data["retry"] = True if (not(args.no_retries)) else False
    if data["zero_copy"]:
        assert("baseline" in data["system"])
        data["system"] = "baseline_zero_copy"
        data["systems"] = ["baseline_zero_copy"]
    if "segments" in args:
        data["segments"] = args.segments
        if args.segments > 1 and "baseline" not in args.system:
            debug(
                "For segments greater than 1, system has to be baseline, not ", args.system)
            exit(1)
        if args.segments > 1:
            debug("Setting segments as {}.".format(args.segments))
            data["system"] = "{}_seg{}".format(data["system"], args.segments)
            data["systems"] = ["{}_seg{}".format(
                data["system"], args.segments)]
    if "experiment" in args:
        data["experiment"] = args.experiment  # size or depth
        if args.experiment == "depth":
            assert(args.system != "baseline")
    return data


def main():
    args = parse_args()
    data = parse_params(args)
    # run cleanup
    if not data["pprint"]:
        cleanup(data)
    cycle_exps(data)


if __name__ == '__main__':
    main()
