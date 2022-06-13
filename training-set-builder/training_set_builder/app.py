import time
import traceback

from matplotlib.pyplot import axis

# from training_set_builder.common.config import parse_config
from training_set_builder.common.data_manager import get_mstd, get_voyages, add_incomplete_trajectories
from training_set_builder.db.models import (db_connect, get_latest_ml_sample,
                                            insert_training_sample)


def batch_process(conn, from_id, batch_size):
    print("="*70)
    print("[batch_process] batch processing from {:d} to {:d}".format(
        from_id, from_id+batch_size))

    try:
        timer = time.time()
        voyages = get_voyages(conn, from_id, batch_size)
        print("[batch_process] get_voyages: {:.3f}s".format(time.time()-timer))

        num_processed = len(voyages)
        last_id = int(voyages["id"].max())

        voyages = add_incomplete_trajectories(voyages)

        timer = time.time()
        df = get_mstd(conn, voyages, comp_method="sspd")
        print("[batch_process] get_mstd: {:.3f}s".format(time.time()-timer))

        timer = time.time()
        batch_insert(conn, df)
        print("[batch_process] insert: {:.3f}s".format(time.time()-timer))
    except BaseException as e:
        traceback.print_exc()
        raise e

    return last_id, num_processed


def batch_insert(conn, df):
    # drop unwanted columns before insert
    df = df.dropna()
    df = df.drop(columns=["trajectory",
                          "departure_port_coords",
                          "arrival_port_coords"])

    # re-order columns for insert
    df = df[[
        "id",
        "imo",
        "season",
        "sub_segment",
        "departure_port",
        "trajectory_length",
        "sspd_mstd",
        "sspd_dist",
        "mstd_id",
        "arrival_port",
        "probablity",
        "distance_ratio",
    ]]

    print("    [batch_insert] inserting {:d} samples".format(len(df)))
    insert_training_sample(conn, df.values)


def run():
    batch_size = 500

    start_id = 3224814
    stop_id =  None

    try:
        # external_db_config = parse_config("external-database")
        conn = db_connect()

        # start_id = get_latest_ml_sample(conn)
        # if start_id is None:
        #     start_id = 0

        print("[main] starting batch process of ml_data from id: ", start_id)

        from_id = start_id
        while True:
            last_id, num_processed = batch_process(conn, from_id, batch_size)

            if num_processed < batch_size:
                break

            if stop_id is not None and last_id >= stop_id:
                print("[main] hit stop condition at id: ", last_id)
                break

            from_id = last_id

    except BaseException as e:
        print("[main] An error occured: ", e)
        exit()
