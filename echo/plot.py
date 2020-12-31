import sys
import os
import argparse
from pathlib import Path
from parse_data import get_suffix
import subprocess as sh
from common import debug

def get_sizes(folder):
    sizes = []
    current_path = Path(folder)
    for system_name in os.listdir(folder):
        if not(os.path.isdir(current_path / system_name)) or system_name == "plots":
            continue
        for message in os.listdir(current_path / system_name):
            for size_name in os.listdir(current_path / system_name / message):
                size = int(get_suffix(size_name))
                if size not in sizes:
                    sizes.append(size)
    return sorted(sizes)
    


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--folder", help = "Base folder", required = True)
    parser.add_argument("-m", "--message", help = "Workload message", default = "None")
    return parser.parse_args()

def run(args):
    try:
        sh.check_call(args)
        debug("SUCCESS: ran {}".format(args))
    except:
        debug("FAILED: to run {}".format(args))
        

def iterate_plot(out_folder, logfile, sizes, message):
    # full plot in req and gbps
    base_args = ["./plot.R", str(logfile)]
    
    rqs_args = ["./plot.R", str(logfile)]
    rqs_file = "{}/size.pdf".format(out_folder)
    rqs_args.extend([rqs_file, "size"])
    run(rqs_args)
    debug("Finished req/s plot")

    gbps_args = ["./plot.R", str(logfile)]
    gbps_file = "{}/size_gbps.pdf".format(out_folder)
    gbps_args.extend([gbps_file, "full"])
    run(gbps_args)
    debug("Finished gbps plot")

    for size in sizes:
        for mmt in ["mp99", "mavg", "avgmedian"]:
            mmt_name = "p99"
            if "mavg" in mmt:
                mmt_name = "avg"
            elif "median" in mmt:
                mmt_name = "median"
            current_args = ["./plot.R", str(logfile)]
            file_arg = "{}/facet_{}_{}.pdf".format(out_folder, size, mmt_name)
            current_args.extend([file_arg, "facet", str(size), message, mmt])
            run(current_args)

def main():
    args = parse_args()
    folder = Path(args.folder)
    logfile = folder / "log.log"
    # create logfile
    #run(["python3", "parse_data.py", "-l", args.folder, "-o", str(logfile)])

    # create plots folder
    out_folder = folder / "plots"
    if not os.path.exists(out_folder):
        os.mkdir(out_folder)
    sizes = get_sizes(args.folder)

    # make the plots
    iterate_plot(out_folder, logfile, sizes, args.message)

if __name__ == '__main__':
    main()
