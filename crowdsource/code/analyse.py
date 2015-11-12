from copy import deepcopy
from pprint import pprint
import os

from clusterlib.storage import sqlite3_loads
from scipy.sparse import coo_matrix
from sklearn.metrics import average_precision_score
from sklearn.metrics import roc_auc_score
import numpy as np
import pandas as pd

from launcher import OUTPUT_DIR
from launcher import PARAMETER_GRID
from launcher import WORKING_DIR
from main import get_sqlite3_path
from main import make_hash
from utils import scale


def _roc_auc_score(y_true, y_score):
    try:
        return roc_auc_score(y_true, y_score)
    except ValueError:
        return np.nan


METRICS = {"roc_auc_score": _roc_auc_score,
           "average_precision_score": average_precision_score}


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
        alive[kill - 1] = False  # we need the -1 since it's matlab indexing
        y_true = y_true[alive][:, alive]

    # Load predictions
    rows = []
    cols = []
    scores = []
    with open(f_prediction) as fhandle:
        # Skip head line
        fhandle.readline()

        for line in fhandle:
            line = line.strip()

            prefix, score = line.rsplit(",", 1)
            scores.append(float(score))
            row, col = prefix.split("_")[-2:]
            rows.append(int(row) - 1)
            cols.append(int(col) - 1)
    y_scores = scale(coo_matrix((scores, (rows, cols))).toarray())

    # Compute scores
    measures = dict((name, metric(y_true.ravel(), y_scores.ravel()))
                    for name, metric in METRICS.items())

    return measures


if __name__ == "__main__":

    all_jobs_done = sqlite3_loads(get_sqlite3_path())
    results = []

    for parameters in PARAMETER_GRID:
        job_hash = make_hash(parameters)
        if job_hash in all_jobs_done:
            fname = os.path.join(OUTPUT_DIR, "%s.csv" % job_hash)

            network = parameters["network"]
            if "normal-" in parameters["network"]:
                network = parameters["network"][:len("normal-") + 1]
            elif ("test" in parameters["network"] or
                    "valid" in parameters['network']):
                # We don't have the ground truth network
                continue

            for bursting_type in ["normal-bursting", "low-bursting",
                                  "high-bursting"]:
                if bursting_type in parameters["fluorescence"]:
                    ground_truth = os.path.join(WORKING_DIR, "datasets",
                                                bursting_type,
                                                "network_%s.txt" % network)
                    break
            else:
                ground_truth = os.path.join(WORKING_DIR, "datasets",
                                            "network_%s.txt" % network)

            ground_truth = os.path.join(WORKING_DIR, "datasets",
                                        "network_%s.txt" % network)
            measure = compute_scores(ground_truth, fname, parameters)
            row = deepcopy(parameters)
            row.update(measure)
            pprint(row)
            results.append(row)

    # Write all results
    results = pd.DataFrame(results)
    writer = pd.ExcelWriter(os.path.join(WORKING_DIR,
                                         "summary_connectomics.xls"))
    results.to_excel(writer)
    writer.save()
