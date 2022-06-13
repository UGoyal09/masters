import numpy as np
import traj_dist.distance as tdist


def most_similar_trajectory(comparator, trajectories):
    distances = {}

    comp = np.array(comparator["trajectory"])
    for v_id, hv in trajectories.items():
        ht = np.array(hv["trajectory"])
        distances[v_id] = int(round(tdist.sspd(comp, ht, "spherical")))

    if len(distances) == 0:
        return None, None

    id, dist = min(distances.items(), key=lambda x: x[1])

    return trajectories[id], dist


def parse_voyages(trajectories):
    voyages = {}
    for id, arrival_port, lon, lat in trajectories:
        if id in voyages:
            voyages[id]["trajectory"].append([lon, lat])
        else:
            voyages[id] = {
                "id": id,
                "arrival_port": arrival_port,
                "trajectory": [[lon, lat]],
            }

    return voyages
