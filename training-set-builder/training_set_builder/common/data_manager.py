from inspect import currentframe
import time
import math
import traceback
from math import radians, cos, sin, asin, sqrt
import numpy as np
import pandas as pd

from training_set_builder.db.models import (fetch_voyages_to_process,
                                            fetch_voyages_with_traj,
                                            fetch_similar_trajectories,
                                            fetch_coordinate_for_mstd_port)
from training_set_builder.trajectory_comparison.comparator import \
    most_similar_trajectory


def get_voyages(conn, start_id, limit):
    try:
        ids = fetch_voyages_to_process(conn, start_id, limit)
        voyages = fetch_voyages_with_traj(conn, ids)
    except BaseException as e:
        raise e

    if voyages is None:
        return None

    data = parse_trajectories(voyages)

    return pd.DataFrame(data, columns=[
        "id",
        "imo",
        "season",
        "sub_segment",
        "departure_port",
        "departure_port_coords",
        "arrival_port",
        "arrival_port_coords",
        "trajectory",
        "trajectory_length",
    ])


def add_incomplete_trajectories(df):
    """generate trajectories of different lengths

    Given array of coords, with indicies:
    [i, i, i, i, i, i, i, i]
     0  1  2  3  4  5  6  7

    We want to create the following trajectories
     0  1
     0  1  2  3
     0  1  2  3  4  5
     0  1  2  3  4  5  6  7 # this one is the original

    Given the following length/parts=4, we want the trajectories to stop at the
    indicies:
    8/4 = 2  : [2, 4, 6]
    9/4 = 2  : [2, 4, 6]
    12/4 = 3 : [3, 6, 9]
    """

    parts = 4

    ret_df = pd.DataFrame(columns=df.columns)

    for _, r in df.iterrows():
        row = r.copy(deep=True)

        traj = row["trajectory"]
        length = len(traj)

        if length < parts:
            # skip trajectories we cant divide by parts
            continue

        inc = math.floor(length/parts)

        # we cant make trajectories of length 1
        if inc <= 1:
            # so use parts/2 as new parts in these cases
            # there are less splits in these cases
            inc = math.floor(length/(parts/2))

        for i in range(inc, length, inc):
            new_traj = traj[:i]
            if len(new_traj) < 2:
                print("warning: generated trajectory was invalid")
                continue

            row["trajectory"] = new_traj
            row["trajectory_length"] = len(new_traj)
            ret_df = ret_df.append(row, ignore_index=True)

    ret_df = ret_df.sort_values(by=["id"], ascending=True)
    ret_df.reset_index(inplace=True)
    return ret_df


def get_mstd(conn, df, comp_method="sspd"):
    """ calculates most similar trajectory's destination for every row in df

        Parameters:
            conn:           database connection
            df:             dataframe containing the rows:
                                - id
                                - trajectory
                                - destination_port
            comp_method:    method used to calculate mstd (default=sspd)
        Returns:
            df: copy of input df with added columns:
                - {comp_method}_mstd (string)
                - {comp_method}_dist (float)
    """

    print("    [get_mtsd] calculating mstd using {:s}".format(comp_method))

    df["{:s}_mstd".format(comp_method)] = None
    df["{:s}_dist".format(comp_method)] = np.nan
    # df["probablity"] = np.nan
    # df["distance_ratio"] = np.nan

    cached_mst = {}

    for index, row in df.iterrows():
        progressBar("    progress:", index+1, len(df))
        try:
            cmp_trajs = get_similar_trajectories(conn, row, cached_mst)
        except BaseException as e:
            raise e

        mst, dist = most_similar_trajectory(
            row, cmp_trajs, method=comp_method)
        if mst is None:
            print("\n    warning: mst for {:d} was none\n".format(row["id"]))
            continue

        

        probablity = get_probablities(cmp_trajs, mst)
        distance_from_departure_port = haversine(row['departure_port_coords'],row['trajectory'])
        mstd_arrival_port_coords = fetch_coordinate_for_mstd_port(conn, mst['arrival_port'])
        distance_to_mstd_arrival_port = haversine(mstd_arrival_port_coords, row['trajectory'])
        ratio = distance_to_mstd_arrival_port/distance_from_departure_port



        df.loc[index, "mstd_id"] = mst["id"]
        df.loc[index, "{:s}_mstd".format(comp_method)] = mst["arrival_port"]
        df.loc[index, "{:s}_dist".format(comp_method)] = dist
        df.loc[index, "probablity"] = probablity
        df.loc[index, "distance_ratio"] = ratio

       
        print("")# clear the progressBar

    return df

# =========================== Helpers ===========================

def get_probablities(cmp_trajs, mst):
    count = 0
    for index,ports in cmp_trajs.items():
        if mst['arrival_port'] == np.array(ports['arrival_port']):
            count = count+1
    probablity = count/len(cmp_trajs)

    return probablity


def get_similar_trajectories(conn, voyage, cached_mst):
    v_id = voyage["id"]
    if v_id in cached_mst:
        return cached_mst[voyage["id"]]

    try:
        trajectories = fetch_similar_trajectories(conn, {
            "id": v_id,
            "departure_port": voyage["departure_port"],
        })
    except BaseException as e:
        raise e

    cached_mst[v_id] = trajectories

    return trajectories

def haversine(port,current_position):
    """
    Calculate the great circle distance in kilometers between two points 
    on the earth (specified in decimal degrees)
    """
    length = len(current_position)
    lon1 = port[0]
    lat1 = port[1]
    lon2 = current_position[length-1][0]
    lat2 = current_position[length-1][1]
    # convert decimal degrees to radians 
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    # haversine formula 
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a)) 
    r = 6371 # Radius of earth in kilometers. Use 3956 for miles. Determines return value units.
    return c * r

def parse_trajectories(data):
    voyages = {}
    for id, fp, flon, flat,sea, tp, tlon, tlat, lon, lat, subs, imo in data:
        if id in voyages:
            voyages[id]["trajectory"].append([lon, lat])
            voyages[id]["trajectory_length"] += 1
        else:
            voyages[id] = {
                "id": id,
                "imo": imo,
                "season":sea,
                # "mmsi": mmsi,
                "sub_segment": subs,
                "departure_port": fp,
                "departure_port_coords": [flon, flat],
                "arrival_port": tp,
                "arrival_port_coords": [tlon, tlat],
                "trajectory": [[lon, lat]],
                "trajectory_length": 1,
                # "arrival_terminal": at,
                # "departure_terminal": dt,
                # "destination_port_is_import": dpi,
                # "vessel_age": va,
            }

    return voyages.values()


def progressBar(prefix, current, total, barLength=20):
    percent = float(current) * 100 / total
    arrow = "=" * int(percent/100 * barLength - 1) + ">"
    spaces = " " * (barLength - len(arrow))

    print("%s [%s%s] %d %%" % (prefix, arrow, spaces, percent), end="\r")
