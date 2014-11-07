#!/usr/bin/env python

# Authors: Aaron Qiu <zqiu@ulg.ac.be>,
#          Antonio Sutera <a.sutera@ulg.ac.be>,
#          Arnaud Joly <a.joly@ulg.ac.be>,
#          Gilles Louppe <g.louppe@ulg.ac.be>,
#          Vincent Francois <v.francois@ulg.ac.be>
#
# License: BSD 3 clause

import numpy as np
import os

WORKING_DIR = os.path.join(os.environ["HOME"],
                           "scikit_learn_data/connectomics")


def kill(X, name, var):

    n_samples, n_nodes = X.shape

    name = name[len("fluorescence_"):]

    # load name_kill_var
    killing_file = os.path.join(WORKING_DIR, "datasets", "hidden-neurons",s
                                "{0}_kill_{1}.txt".format(name, var))
    kill = np.loadtxt(killing_file, dtype=np.int)

    # make a mask
    alive = np.ones((n_nodes,), dtype=bool)
    alive[kill] = False

    # kill neurons
    X_kill = X[:, alive]

    # Checks
    n_samples_kill, n_nodes_kill = X_kill.shape
    if (n_nodes - len(kill)) != n_nodes_kill:
        raise ValueError("Kill nodes should match.")
    if n_samples != n_samples_kill:
        raise ValueError("Number of samples should be the same")

    return X_kill
