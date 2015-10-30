import os
import sys
import argparse
import shlex
from pprint import pprint
from collections import defaultdict

from sklearn.grid_search import ParameterGrid

from clusterlib.scheduler import queued_or_running_jobs
from clusterlib.scheduler import submit
from clusterlib.storage import sqlite3_loads

from main import WORKING_DIR
from main import make_hash
from main import parse_arguments
from main import get_sqlite3_path


# Make the grid of parameters to evaluate -------------------------------------


ALL_FLUORESCENCE = []
for directory in [os.path.join(WORKING_DIR, "datasets"),
                  os.path.join(WORKING_DIR, "datasets", "normal-bursting"),
                  os.path.join(WORKING_DIR, "datasets", "low-bursting"),
                  os.path.join(WORKING_DIR, "datasets", "high-bursting")]:
    if os.path.exists(directory):
        for path in os.listdir(directory):
            if path.startswith("fluorescence_"):
                ALL_FLUORESCENCE.append(os.path.join(WORKING_DIR, "datasets",
                                                     path))

ALL_NETWORKS = [os.path.basename(os.path.splitext(x)[0]).split("_", 1)[1]
                for x in ALL_FLUORESCENCE]


OUTPUT_DIR = os.path.join(WORKING_DIR, "submission")

NORMAL = [{"output_dir": [OUTPUT_DIR],
           "network": [network],
           "fluorescence": [fluorescence],
           "method": ["simple", "tuned"],
           "directivity": [0, 1]}
          for fluorescence, network in zip(ALL_FLUORESCENCE, ALL_NETWORKS)]

HIDDEN_NEURON = [{"output_dir": [OUTPUT_DIR],
                  "network": [network],
                  "fluorescence": [fluorescence],
                  "method": ["simple", "tuned"],
                  "directivity": [0, 1],
                  "killing": range(1, 11)}
                 for fluorescence, network in zip(ALL_FLUORESCENCE,
                                                  ALL_NETWORKS)
                 if network in ("normal-3", "normal-4")]

PARAMETER_GRID = ParameterGrid(NORMAL + HIDDEN_NEURON)


# Useful constant for the job launch -------------------------------------

LOG_DIRECTORY = os.path.join(WORKING_DIR, "logs")

CLUSTER_MIN_TIME = 5
CLUSTER_MAX_TIME = 63
CLUSTER_MAX_N_JOBS = 1000

JOB_MIN_MEMORY = 4000
JOB_MIN_TIME = 100


def select_queue(memory, time):
    if time > CLUSTER_MAX_TIME * 24:
        raise ValueError("Cluster doesnn't accept more than %s days, got %s"
                         % (CLUSTER_MAX_TIME, time / 24))

    partitions = []
    if time < 6:
        partitions.append('Short')
    if time < 360:
        partitions.append("Long")
        partitions.append("XLong")

    return " -p %s " % ",".join(partitions)


def compute_memory_time(to_launch, show_log_error=True, verbose=True):
    # Create log direcotyr if needed
    if not os.path.exists(LOG_DIRECTORY):
        os.makedirs(LOG_DIRECTORY)

    # Get path of all logs
    log_paths = defaultdict(list)
    for fname in os.listdir(LOG_DIRECTORY):
        log_paths[fname.split(".", 1)[0]].append(fname)

    # Get time and memory from empirical evidences (logs)
    time = dict()
    memory = dict()

    for job_hash, parameters in to_launch.items():
        n_memory_error = 0
        n_time_error = 0
        if job_hash in log_paths:
            for fname in log_paths[job_hash]:
                with open(os.path.join(LOG_DIRECTORY, fname)) as fhandle:
                    log_file = fhandle.read().lower()
                    if "memory" in log_file:
                        n_memory_error += 1
                    if "time limit" in log_file:
                        n_time_error += 1

        memory[job_hash] = JOB_MIN_MEMORY + n_memory_error * 1000
        time[job_hash] = JOB_MIN_TIME + 2 ** n_time_error

        # Take into account scheduler
        time[job_hash] = max(CLUSTER_MIN_TIME, time[job_hash])

        if verbose and (n_memory_error > 0 or n_time_error > 0):
            print(job_hash, end=" ")
            if n_memory_error > 0:
                print("memory was increased %s time to %s"
                      % (n_memory_error, memory[job_hash]), end=" ")
            if n_time_error > 0:
                print("time was increased %s time to %s"
                      % (n_time_error, time[job_hash]), end=" ")
            print()

        if show_log_error:
            for fname in sorted(log_paths[job_hash])[-1:]:
                with open(os.path.join(LOG_DIRECTORY, fname)) as fhandle:
                    log_to_print = fhandle.read().strip()
                    if (log_to_print != "" and
                            "memory" not in log_to_print.lower() and
                            "time limit" not in log_to_print.lower()):
                        print(fname)
                        print(log_to_print)

    return time, memory

if __name__ == "__main__":
    # Argument parser
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--debug', default=False, action="store_true")
    parser.add_argument('-v', '--verbose', default=False, action="store_true")
    parser.add_argument('-l', '--logs', default=False, action="store_true",
                        help="Show log if any")

    args = vars(parser.parse_args())

    # Create log direcotyr if needed
    if not os.path.exists(LOG_DIRECTORY):
        os.makedirs(LOG_DIRECTORY)

    # Get the list of jobs that has to be launched
    all_jobs_running = set(queued_or_running_jobs())
    all_jobs_done = sqlite3_loads(get_sqlite3_path())
    n_jobs_running = 0
    n_jobs_done = 0
    to_launch = dict()

    for parameters in PARAMETER_GRID:
        job_hash = make_hash(parameters)

        if job_hash in all_jobs_done:
            n_jobs_done += 1
        elif job_hash in all_jobs_running:
            n_jobs_running += 1
        elif job_hash in to_launch:
            print("current parameters")
            print(parameters)
            raise ValueError("We have a hash collision")
        else:
            to_launch[make_hash(parameters)] = parameters

    # Compute time and memory requirements
    time, memory = compute_memory_time(to_launch, show_log_error=args["logs"])

    # Launch if necessary experiments
    max_n_launch = max(CLUSTER_MAX_N_JOBS - len(all_jobs_running), 0)
    n_jobs_launched = 0

    for job_hash, parameters in list(to_launch.items())[:max_n_launch]:
        cmd_parameters = " ".join("--%s %s" % (key, parameters[key])
                                  for key in sorted(parameters))

        scripts_args = parse_arguments(shlex.split(cmd_parameters))
        if make_hash(scripts_args) != job_hash:
            pprint(scripts_args)
            pprint(parameters)
            raise ValueError("hash are not equal, all parameters are "
                             "not specified.")

        cmd = submit(job_command=" ".join([sys.executable,
                                           os.path.abspath("main.py"),
                                           cmd_parameters]),
                     job_name=job_hash,
                     time="%s:00:00" % time[job_hash],
                     memory=memory[job_hash],
                     log_directory=LOG_DIRECTORY,
                     backend="slurm")

        cmd += select_queue(memory[job_hash], time[job_hash])

        if not args["debug"]:
            os.system(cmd)
            n_jobs_launched += 1

        elif args["verbose"]:
            print("[launched] %s " % (job_hash, ))
            print(cmd)

    print("\nSummary launched")
    print("------------------")
    print("n_jobs_runnings = %s" % n_jobs_running)
    print("n_jobs_done = %s" % n_jobs_done)
    print("n_jobs_launched = %s" % n_jobs_launched)
    print("n_jobs_remaining = %s" %
          (len(PARAMETER_GRID) - n_jobs_running - n_jobs_done, ))
    print("n_total_jobs = %s" % len(PARAMETER_GRID))
