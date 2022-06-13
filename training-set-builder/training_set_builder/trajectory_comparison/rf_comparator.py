import numpy as np
import pandas as pd
from haversine import haversine
from numpy import arccos, array, cross, dot, pi
from numpy.linalg import det, norm


def dist_ratio(port_a, port_b, point):
    return haversine(port_a, point, unit="m") / haversine(point, port_b, unit="m")


def point_line_dist(A, B, P):
    """ segment line AB, point P, where each one is an array([x, y]) """
    A = np.array(A)
    B = np.array(B)
    P = np.array(P)
    if all(A == B):
        return norm(P-A)
    if all(A == P) or all(B == P):
        return 0
    if arccos(dot((P - A) / norm(P - A), (B - A) / norm(B - A))) > pi / 2:
        return norm(P - A)
    if arccos(dot((P - B) / norm(P - B), (A - B) / norm(A - B))) > pi / 2:
        return norm(P - B)
    return norm(cross(A-B, A-P))/norm(B-A)


def traj_compare(sample, complete):
    """traj_compare creates a comparison feature

    sample trajectory: { trajectory: [] }
    complete trajectory: { from: { coords: [] }, to: { coords: [] }, trajectory: [] }
    returns comparison_feature and if the trajectories did share the same
    destination port
    """

    sample_t = sample["trajectory"]
    hist_t = complete["trajectory"]
    from_coords = complete["from"]["coords"]
    to_coords = complete["to"]["coords"]

    same_destination = False
    if sample["to"]["port"] == complete["to"]["port"]:
        same_destination = True

    # should include d1, d2, d3 i.e. distances from every st point to ht vec
    # trajectory_cf = []
    trajectory_cf = {}

    j = 1
    # for every point in sample trajectory
    for s_point in sample_t:
        dists = []
        # for every point in historical trajectory
        for i, h_point in enumerate(hist_t):
            if i > 0:
                dists.append(point_line_dist(
                    hist_t[len(hist_t)-1], h_point, s_point
                ))
        # trajectory_cf.append(min(dists))
        trajectory_cf["d"+str(j)] = min(dists)
        j += 1

    trajectory_cf["dr"] = dist_ratio(
        from_coords, to_coords, sample_t[len(sample_t)-1])
    # trajectory_cf.append(dist_ratio(
    #     from_coords, to_coords, sample_t[len(sample_t)-1]))

    return trajectory_cf, same_destination


def compare_trajectories(sample, historical):
    comparison_features = []
    for k, ht in historical.items():
        training_sample, same_dest = traj_compare(sample, ht)
        training_sample["same_destination"] = same_dest
        if same_dest == True:
            print(k)
        comparison_features.append(training_sample)

    return pd.DataFrame(comparison_features)
