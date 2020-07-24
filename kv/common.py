import argparse
import os
import sys
import multiprocessing
from fabric import Connection
import yaml
import time
#########
WORKLOADS = ["workloada", "workloadb", "workloadc"]
#########
def debug(*args):
    prepend = "\u2192"
    print(prepend, *args, file=sys.stderr)

def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-y", "--yaml",
                        help = "Experiment yaml file.",
                        required=True)
    parser.add_argument("-s", "--system",
                        choices = ["protobuf", "handcrafted",
                        "flatbuffers", "capnproto"],
                        help = "Which system to benchmark.",
                        required=True)
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
    parser.add_argument("-yc", "--ycsb_root",
                        help = "YCSB root workload location",
                        required = True)
    return parser
def parse_args():
    parser = get_parser()
    return parser.parse_args()

def calculate_log_path(args, trial, workload, exp):
    """
    Logpath for where results for this experiment will be stored.

    """
    return "{}/{}/{}/{}/trial_{}".format(
            args["logfile"],
            args["system"],
            workload,
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
    kill_server(args)
    for idx in range(1, args["num_clients"] + 1):
        kill_client(args, idx)
    debug("Done with cleanup, starting experiment.")


def kill_server(args):
    host = args["hosts"]["server"]["addr"]
    cxn = connection(args, host)
    try:
        # send 2 -> interrupt from keyboard
        cxn.sudo("sudo kill -9 `ps aux | grep {kv_exec_dir}/{libos}-kv-server | awk '{{print $2}}' | head -n3`".format(**args), hide = True)
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
        cxn.sudo("sudo kill  -9 `ps aux | grep {kv_exec_dir}/{libos}-kv-client | awk '{{print $2}}' | head -n3`".format(**args), hide = True)
        time.sleep(2)
    except:
        return False

def start_server(args, trial, workload, num_clients):
    exp = "{}clients".format(num_clients)
    baselog = calculate_log_path(args, trial, workload, exp)
    if not args["pprint"]:
        os.makedirs(baselog)
    loads = "{}/{}/{}-{}.load".format(
                                args["ycsb_root"],
                                workload,
                                workload,
                                num_clients)
    cmd = "sudo nice -n -20 taskset 0x1 "
    cmd += "{kv_exec_dir}/{libos}-kv-server --port {port} --config-path {config_path} --system {system}".format(**args)
    cmd += " --loads {}".format(loads)

    logpath  = "{}/server".format(baselog)
    cmd += " > {} 2> {}".format(
                "{}.log".format(logpath),
                "{}.err.log".format(logpath))

    host = args["hosts"]["server"]["addr"]
    if args["pprint"]:
        debug(host, ": ", cmd)

    proc = multiprocessing.Process(target = run_cmd, args=(cmd, host, args, True))
    return proc

def start_client(args, idx, trial, workload, num_clients):
    exp = "{}clients".format(num_clients)
    baselog = calculate_log_path(args, trial, workload, exp)
    logpath  = "{}/client{}".format(baselog, idx)
    cmd = "sudo {kv_exec_dir}/{libos}-kv-client --port {port} --config-path {config_path} --system {system}".format(**args)
    access_file = "{}/{}/{}-{}.access".format(
                                        args["ycsb_root"],
                                        workload,
                                        workload,
                                        num_clients)
    cmd += " --access {} --id {}".format(access_file, idx - 1)
    cmd += " > {} 2> {}".format(
                "{}.log".format(logpath),
                "{}.err.log".format(logpath))

    host = args["hosts"]["client{}".format(idx)]["addr"]
    if args["pprint"]:
        debug(host, ": ", cmd)
    proc = multiprocessing.Process(target = run_cmd, args=(cmd, host, args))
    return proc

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

def run_exp(args, trial, workload, num_clients):
    exp = "{}clients".format(num_clients)
    if os.path.exists(calculate_log_path(args, trial, workload, exp)):
        debug("Exp: trial {}, workload {}, system {}, clients {} exists, skipping".format(
            trial,
            workload,
            args["system"],
            num_clients))
    debug("Running exp: trial {}, workload {}, system {}, clients {}".format(
            trial,
            workload,
            args["system"],
            num_clients))
    server_proc = start_server(args, trial, workload, num_clients)
    if not args["pprint"]:
        server_proc.start()
        time.sleep(3)
    
    # start each client
    client_procs = []
    for i in range(1, num_clients + 1):
        client_procs.append(start_client(args, i, trial, workload, num_clients))
    
    if args["pprint"]:
        return

    # start and join each client, then kill server
    for proc in client_procs:
        proc.start()
    for proc in client_procs:
        proc.join()
        debug("\t Client joined")

    kill_server(args)
    return

def cycle_exps(args):
    for trial in range(0, NUM_TRIALS):
        for workload in WORKLOADS:
            for clients in (1, args["num_clients"] + 1):
                run_exp(args, trial, workload, clients)

def parse_params(args):
    with open(args.yaml) as f:
        data = yaml.load(f)
    data["libos"] = args.libos # lwip, rdma, posix
    data["system"] = args.system # currently: baseline, protobuf
    data["num_clients"] = args.num_clients # number of available clients to
    data["logfile"] = args.logfile # folder
    data["pprint"] = args.pprint # just print commands
    if "workload" in args:
        data["workload"] = args.workload
    if "ycsb_root" in args:
        data["ycsb_root"] = args.ycsb_root
    return data

def main():
    args = parse_args()
    config = parse_params(args)
    # run cleanup
    cleanup(config)
    cycle_exps(config)

if __name__ == '__main__':
    main()








