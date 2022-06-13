import traceback

import psycopg2
from psycopg2 import extras
import numpy as np


def insert_training_sample(connection, data):
    """ insert sample into external db """

    q = """
        INSERT into lng_training_data(
            voyage_id,
            imo,
            season,
            sub_segment,
            departure_port,
            trajectory_length,
            sspd_mstd,
            sspd_dist,
            mstd_id,
            arrival_port,
            probablity,
            distance_ratio
        ) VALUES %s
    """

    try:
        cursor = connection.cursor()
        extras.execute_values(
            cursor, q, data, template=None, page_size=100
        )
        connection.commit()
    except (Exception, psycopg2.DatabaseError) as error:
        cursor.close()
        print("\n[execute] an error occured:\n")
        traceback.print_exc()
        raise error


def get_latest_ml_sample(connection):
    q = "SELECT voyage_id FROM lng_training_data ORDER BY voyage_id DESC LIMIT 1"
    try:
        result = get(connection, q)
    except Exception as e:
        raise e

    if result is None:
        return None

    return result[0]


def fetch_voyages_to_process(connection, start_id, limit):
    q = """
        SELECT id FROM "lng_voyages"
        WHERE id > %s
        ORDER BY id ASC
        LIMIT %s
    """

    try:
        result = select(connection, q, [start_id, limit])
    except Exception as e:
        raise e

    return result


def fetch_voyages_with_traj(connection, voyage_ids):
    q = """
        SELECT
            id,
            departure_port,
            departure_lon,
            departure_lat,
            season,
            arrival_port,
            arrival_lon,
            arrival_lat,
            st_x(points) AS lon,
            st_y(points) AS lat,
            sub_segment,
            imo
        FROM (
            SELECT
                -- voyage info
                a.id as id,
                a.imo as imo,
                (st_dumppoints (a.trajectory)).geom AS points,

                -- departure port position and id
                st_x(b.position) as departure_lon,
                st_y(b.position) as departure_lat,
                b.locode as departure_port,

                -- arrival port position and id
                st_x(c.position) as arrival_lon,
                st_y(c.position) as arrival_lat,
                c.locode as arrival_port,

                a.sub_segment,
                a.season

            FROM "lng_voyages" a

            LEFT JOIN ports as b ON (b.locode = a.departure_port)
            LEFT JOIN ports as c ON (c.locode = a.arrival_port)

            WHERE a.id in %s
        ) f
        ORDER BY id ASC
    """

    ids = tuple(i[0] for i in voyage_ids)
    try:
        result = select(connection, q, (ids,))
    except Exception as e:
        raise e

    return result


def fetch_similar_trajectories(connection, voyage):
    q = """
        SELECT
            id,
            arrival_port,
            st_x(points) AS lon,
            st_y(points) AS lat
        FROM (
            SELECT
                id,
                arrival_port,
                (st_dumppoints (trajectory)).geom AS points
            FROM "lng_voyages" a
            WHERE
                id != %s
                AND departure_port = %s
        ) c
    """

    try:
        result = select(
            connection, q, [voyage["id"], voyage["departure_port"]])
    except Exception as e:
        raise e

    voyages = {}
    for id, arrival_port, lon, lat in result:
        if id in voyages:
            voyages[id]["trajectory"].append([lon, lat])
        else:
            voyages[id] = {
                "id": id,
                "arrival_port": arrival_port,
                "trajectory": [[lon, lat]],
            }

    return voyages

def fetch_coordinate_for_mstd_port(connection, arrival_port):
    q = """
        SELECT
                st_x(b.position) as arrival_lon,
                st_y(b.position) as arrival_lat
        FROM
            "ports" b
        WHERE
            b.locode = %s
    """

    try:
        result = select(connection, q, [arrival_port])
        mstd_arrival_port_coords = []
    except Exception as e:
        raise e

    for  arrival_lon, arrival_lat in result:
        mstd_arrival_port_coords = [arrival_lon, arrival_lat]    
    
    return mstd_arrival_port_coords


def db_connect():
    print("[db_connect] connecting to database")
    conn = None
    try:
        conn = psycopg2.connect(
            host="localhost",
            database="postgres",
            user="postgres",
            port="5432",
            password="agra12345",
            sslmode="disable")

    except (Exception, psycopg2.DatabaseError) as error:
        print("\n[db_connect] error while connecting to DB:\n")
        traceback.print_exc()
        if conn is not None:
            conn.close()

        raise error

    print("[db_connect] Successfully established connection")

    return conn


def select(connection, q, args=None):
    try:
        cursor = connection.cursor()
        cursor.execute(q, args)
        connection.commit()

        result = cursor.fetchall()
        cursor.close()

        return result
    except (Exception, psycopg2.DatabaseError) as error:
        cursor.close()
        connection.close()
        print("\n[select] an error occured:\n")
        traceback.print_exc()
        raise error


def get(connection, q, args=None):
    try:
        cursor = connection.cursor()
        cursor.execute(q, args)
        connection.commit()

        result = cursor.fetchone()
        cursor.close()

        return result
    except (Exception, psycopg2.DatabaseError) as error:
        cursor.close()
        connection.close()
        print("\n[select] an error occured:\n")
        traceback.print_exc()
        raise error
