import os
import sys
import argparse
import shlex
from pprint import pprint
from copy import deepcopy

import numpy as np
from scipy.sparse import coo_matrix

from sklearn.grid_search import ParameterGrid

from clusterlib.scheduler import queued_or_running_jobs
from clusterlib.scheduler import submit
from clusterlib.storage import sqlite3_loads

from sklearn.metrics import average_precision_score
from sklearn.metrics import roc_auc_score

from main import WORKING_DIR
from main import make_hash
from main import parse_arguments
from main import get_sqlite3_path
from utils import scale

LOG_DIRECTORY = os.path.join(WORKING_DIR, "logs")

ALL_FLUORESCENCE = [os.path.join(WORKING_DIR, "datasets", x)
                    for x in os.listdir(os.path.join(WORKING_DIR,
                                                     "datasets"))
                    if (x.startswith("fluorescence_"))]

ALL_NETWORKS = [os.path.basename(os.path.splitext(x)[0]).split("_", 1)[1]
                for x in ALL_FLUORESCENCE]


OUTPUT_DIR = os.path.join(WORKING_DIR, "submission")

NORMAL = [{
    "output_dir": [OUTPUT_DIR],
    "network": [network],
    "fluorescence": [fluorescence],
    "method": ["simple", "tuned"],
    "directivity": [0, 1],
} for fluorescence, network in zip(ALL_FLUORESCENCE, ALL_NETWORKS)]

HIDDEN_NEURON = [{
    "output_dir": [OUTPUT_DIR],
    "network": [network],
    "fluorescence": [fluorescence],
    "method": ["simple", "tuned"],
    "directivity": [0, 1],
    "killing": range(1, 11),
}
for fluorescence, network in zip(ALL_FLUORESCENCE, ALL_NETWORKS)
if network in ("normal-3", "normal-4")
]

PARAMETER_GRID = ParameterGrid(NORMAL + HIDDEN_NEURON)

TIME = dict()
MEMORY = dict()

def _roc_auc_score(y_true, y_score):
    try:
        return roc_auc_score(y_true, y_score)
    except ValueError:
        return np.nan

METRICS = {
    "roc_auc_score": _roc_auc_score,
    "average_precision_score": average_precision_score,
}




def compute_scores(f_ground_truth, f_prediction, parameters):

    # Load ground truth
    raw_graph = np.loadtxt(f_ground_truth, delimiter=",")
    row = raw_graph[:, 0] - 1
    col = raw_graph[:, 1] - 1
    data = raw_graph[:, 2]
    valid_index = data > 0
    y_true = coo_matrix((data[valid_index],
                         (row[valid_index], col[valid_index])),
                        shape=(1000, 1000))

    y_true = y_true.toarray()

    if parameters.get("killing", None):

        # load name_kill_var
        killing_file = os.path.join(WORKING_DIR, "datasets", "hidden-neurons",
                                    "{0}_kill_{1}.txt"
                                    "".format(parameters["network"],
                                              parameters["killing"]))
        kill = np.loadtxt(killing_file, dtype=np.int)

        # make a mask
        alive = np.ones((y_true.shape[0],), dtype=bool)
        alive[kill - 1] = False  # we need to make -1 since it's matlab indexing
        y_true = y_true[alive, alive]
        print(y_true.sum())


    # Load predictions
    rows = []
    cols = []
    scores = []
    with open(f_prediction) as fhandle:
        fhandle.next()

        for line in fhandle:
            line = line.strip()

            prefix, score = line.rsplit(",", 1)
            scores.append(float(score))
            row, col = prefix.split("_")[-2:]
            rows.append(int(row) - 1)
            cols.append(int(col) - 1)
    y_scores = scale(coo_matrix((scores, (rows, cols))).toarray())

    print(y_true.shape)
    print(y_scores.shape)

    # Compute scores
    measures = dict((name, metric(y_true.ravel(), y_scores.ravel()))
                    for name, metric in METRICS.items())

    return measures



if __name__ == "__main__":

    # Argument parser
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--debug', default=False, action="store_true")
    parser.add_argument('-v', '--verbose', default=False, action="store_true")
    parser.add_argument('-s', '--scores', default=False, action="store_true",
                        help="compute scores")

    args = vars(parser.parse_args())


    # Create log direcotyr if needed
    if not os.path.exists(LOG_DIRECTORY):
        os.makedirs(LOG_DIRECTORY)

    # Get running jobs
    all_jobs_running = set(queued_or_running_jobs())
    all_jobs_done = sqlite3_loads(get_sqlite3_path())

    # Intialize some counter for reporting
    n_jobs_running = 0
    n_jobs_done = 0
    n_jobs_launched = 0

    results = []

    # Launch if necessary experiments
    for parameters in PARAMETER_GRID:
        job_hash = make_hash(parameters)

        if job_hash in all_jobs_running:
            n_jobs_running +=1

        elif job_hash in all_jobs_done:
            n_jobs_done += 1

            if args["scores"]:
                fname = os.path.join(OUTPUT_DIR, "%s.csv" % job_hash)


                network = parameters["network"]
                if "normal-" in parameters["network"]:
                    network = parameters["network"][:len("normal-") + 1]
                elif "test" in parameters["network"]:
                    continue
                elif "valid" in parameters['network']:
                    continue
                else:
                    raise ValueError("Unknown network")

                ground_truth = os.path.join(WORKING_DIR, "datasets",
                                            "network_%s.txt" % network)
                measure = compute_scores(ground_truth, fname, parameters)
                row = deepcopy(parameters)
                row.update(measure)
                pprint(row)
                results.append(row)


        else:
            n_jobs_launched += 1
            cmd_parameters = " ".join("--%s %s" % (key, parameters[key])
                                      for key in sorted(parameters))

            scripts_args = parse_arguments(shlex.split(cmd_parameters))
            if make_hash(scripts_args) != job_hash:
                pprint(scripts_args)
                pprint(parameters)
                raise ValueError("hash are not equal, all parameters are "
                                 "not specified.")

            cmd = submit(job_command="%s main.py %s"
                                     % (sys.executable, cmd_parameters),
                         job_name=job_hash,
                         time="100:00:00",
                         memory=24000,
                         log_directory=LOG_DIRECTORY,
                         backend="slurm")

            if not args["debug"]:
                os.system(cmd)
            elif args["verbose"]:
                print("[launched] %s" % job_hash)
                print(cmd)

                if os.path.exists(os.path.join(LOG_DIRECTORY,
                                               "%s.txt" % job_hash)):
                    os.system("cat %s" % os.path.join(LOG_DIRECTORY,
                                                      "%s.txt" % job_hash))

    print("\nSummary launched")
    print("------------------")
    print("n_jobs_runnings = %s" % n_jobs_running)
    print("n_jobs_done = %s" % n_jobs_done)
    print("n_jobs_launched = %s" % n_jobs_launched)

    if args["scores"]:
        import pandas as pd
        results = pd.DataFrame(results)

        writer = pd.ExcelWriter(os.path.join(WORKING_DIR,
                                             "summary_connectomics.xls"))
        results.to_excel(writer)
        writer.save()
