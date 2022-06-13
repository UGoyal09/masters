import time
from copy import deepcopy
from os import walk

import matplotlib.pyplot as plt
import psycopg2

from classifier import RFClassifier
from config import parse_config
from db_models import db_connect
from trajectory_comparator import compare_trajectories
from URF.main import random_forest_cluster, plot_cluster_result


def fetch_port_coord(connection, port):
    q = """
        SELECT
            st_x(position) as lon,
            st_y(position) as lat
        FROM ports
        WHERE locode=%s
    """
    cursor = connection.cursor()
    cursor.execute(q, [port])
    connection.commit()

    return cursor.fetchall()


def fetch_sample(connection):
    q = """
        SELECT
            voyage_id,
            departure_port,
            st_x(b.position) as departure_lon,
            st_y(b.position) as departure_lat,
            arrival_port,
            st_x(c.position) as arrival_lon,
            st_y(c.position) as arrival_lat,
            st_x(points) AS lon,
            st_y(points) AS lat
        FROM (
            SELECT
                voyage_id,
                departure_port,
                arrival_port,
                (st_dumppoints (trajectory)).geom AS points
            FROM sampled_trajectory_voyages
            WHERE voyage_id=4401
        ) a
        LEFT JOIN ports as b ON (b.locode = a.departure_port)
        LEFT JOIN ports as c ON (c.locode = a.arrival_port)
    """
    cursor = connection.cursor()
    cursor.execute(q)
    connection.commit()

    return cursor.fetchall()


def fetch_random_trajectories(connection, limit):
    q = """
        SELECT
            voyage_id,
            departure_port,
            st_x(b.position) as departure_lon,
            st_y(b.position) as departure_lat,
            arrival_port,
            st_x(c.position) as arrival_lon,
            st_y(c.position) as arrival_lat,
            st_x(points) AS lon,
            st_y(points) AS lat
        FROM (
            SELECT
                voyage_id,
                departure_port,
                arrival_port,
                (st_dumppoints (trajectory)).geom AS points
            FROM sampled_trajectory_voyages
            WHERE departure_port != arrival_port
            LIMIT %s
        ) a
        LEFT JOIN ports as b ON (b.locode = a.departure_port)
        LEFT JOIN ports as c ON (c.locode = a.arrival_port)
    """
    cursor = connection.cursor()
    cursor.execute(q, [limit])
    connection.commit()

    return cursor.fetchall()


def fetch_trajectories(connection, port):
    q = """
        SELECT
            voyage_id,
            departure_port,
            st_x(b.position) as departure_lon,
            st_y(b.position) as departure_lat,
            arrival_port,
            st_x(c.position) as arrival_lon,
            st_y(c.position) as arrival_lat,
            st_x(points) AS lon,
            st_y(points) AS lat
        FROM (
            SELECT
                voyage_id,
                departure_port,
                arrival_port,
                (st_dumppoints (trajectory)).geom AS points
            FROM
                sampled_trajectory_voyages
            WHERE
                departure_port = %s
                AND arrival_port != %s) a
        LEFT JOIN ports as b ON (b.locode = a.departure_port)
        LEFT JOIN ports as c ON (c.locode = a.arrival_port)
    """
    cursor = connection.cursor()
    cursor.execute(q, [port, port])
    connection.commit()

    return cursor.fetchall()


def parse_data(data):
    voyages = {}
    for id, from_p, from_lon, from_lat, to_p, to_lon, to_lat, lon, lat in data:
        if id in voyages:
            voyages[id]["trajectory"].append([lon, lat])
        else:
            voyages[id] = {
                "from": {
                    "port": from_p,
                    "coords": [from_lon, from_lat],
                },
                "to": {
                    "port": to_p,
                    "coords": [to_lon, to_lat],
                },
                "trajectory": [[lon, lat]]
            }

    return voyages


def most_similar_trajectory(sample, trajectories):
    comparison_features = compare_trajectories(sample, trajectories)

    print(comparison_features)
    classifier = RFClassifier(comparison_features, labeled_columns=[
                              "d1", "d2", "d3", "d4", "dr"], target_column="same_destination")

    X_train, X_test, y_train, y_test = classifier.train_test_split()

    # X = classifier.X
    # print(len(X))
    # clf, prox_mat, cluster_ids = random_forest_cluster(
    #     X.values, k=3, max_depth=20, random_state=0)
    #
    # plot_cluster_result(prox_mat, cluster_ids, marker=None)
    # print(prox_mat)

    classifier.fit_model(X_train, y_train)
    accuracy, results = classifier.predict(X_test, y_test)

    print("\n[main] accuracy:", accuracy)

    classifier.print_feature_importance()

    print("\n[main] results")
    print(results.loc[results["same_destination"] == True])

    # print("\n[main] results")
    # print(classifier.proximityMatrix(normalize=True))
    # plt.matshow(classifier.proximityMatrix(normalize=True))
    # plt.colorbar()
    # plt.show()


def main():
    external_db_config = parse_config("external-database")
    conn = db_connect(external_db_config)
    if conn == None:
        print("Could not connect to DB, exiting")
        return

    sample = parse_data(fetch_sample(conn))
    trajectories = parse_data(fetch_trajectories(conn, "SGSIN"))
    # pick a random sample
    # _, sample = trajectories.popitem()

    most_similar_trajectory(sample[4401], trajectories)

    # ml_data = []
    # total = 0
    # start = time.time()

    # for every trajectory, create a comparison feature to every other trajectory
    # for key, sample in trajectories.items():
    #     t_copy = deepcopy(trajectories)
    #     t_copy.pop(key)
    #     comparison_features = create_comparison_features(t_copy, sample)
    #
    #     # data = {
    #     #     # "departure_port": sample["from"]["port"],
    #     #     # "arrival_port": sample["to"]["port"],
    #     #     # "sample": np.array(sample["trajectory"]),
    #     #     # "historical_trajectories": np.array(comparison_features),
    #     # }
    #     ml_data.append(comparison_features)
    #     total += len(comparison_features)
    #     break

    # print("generated {:d} samples with {:d} comparison samples in {:.4f}".format(
    #     len(ml_data), total, time.time()-start))


if __name__ == "__main__":
    main()
