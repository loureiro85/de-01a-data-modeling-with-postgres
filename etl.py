import glob
import os

import pandas as pd
import psycopg2

from sql_queries import (artist_table_insert, logartist_table_insert, song_select,
                         song_table_insert, songplay_table_insert, time_table_insert,
                         user_table_insert)


def process_song_file(cur, filepath):
    """Process song files by reading and inserting in DB.

    Steps:
    - Read song files in JSON format;
    - Insert data into 'songs' table;
    - Insert data into 'artists' table.
    """

    # open song file
    df = pd.read_json(filepath, typ='series')

    # insert song record
    song_data = df[[
        'song_id',
        'title',
        'artist_id',
        'year',
        'duration'
    ]].values
    cur.execute(song_table_insert, song_data)

    # insert artist record
    artist_data = df[[
        'artist_id',
        'artist_name',
        'artist_location',
        'artist_latitude',
        'artist_longitude'
    ]].values
    cur.execute(artist_table_insert, artist_data)


def process_log_file(cur, filepath):
    """Process log files by reading and inserting in DB.

    Steps:
    - Read log files in JSON format;
    - Filter by 'NextSong' page action;
    - Convert timestamp format to datetime;
    - Insert data into 'time' table;
    - Insert data into 'users' table;
    - Insert data into 'songplays' table;
    """

    # read log file
    df = pd.read_json(filepath, lines=True)

    # filter by NextSong page action
    df = df[df['page'] == 'NextSong']

    # convert timestamp column to datetime
    t = pd.to_datetime(df['ts'])
    df['ts_timestamp'] = pd.to_datetime(df['ts'])

    # insert time data records
    time_data = (
        t.values,
        t.dt.hour.values,
        t.dt.day.values,
        t.dt.isocalendar().week.values,
        t.dt.month.values,
        t.dt.year.values,
        t.dt.weekday.values
    )
    column_labels = (
        'start_time',
        'hour',
        'day',
        'week',
        'month',
        'year',
        'weekday'
    )
    time_df = pd.DataFrame(data=time_data).T
    time_df.columns = column_labels

    # Cast datatypes
    time_df = time_df.astype({
        'hour': int,
        'day': int,
        'week': int,
        'month': int,
        'year': int,
        'weekday': int,
    })

    for i, row in time_df.iterrows():
        cur.execute(time_table_insert, list(row))

    # load user table
    user_df = df[[
        'userId',
        'firstName',
        'lastName',
        'gender',
        'level'
    ]]

    # insert user records
    for i, row in user_df.iterrows():
        cur.execute(user_table_insert, row)

    # insert songplay records
    for index, row in df.iterrows():

        # get songid and artistid from song and artist tables
        cur.execute(song_select, (row.song, row.artist, row.length))
        # cur.execute(song_select, (row.song, row.artist))
        results = cur.fetchone()

        if results:
            songid, artistid = results
        else:
            songid, artistid = None, None

        # insert songplay record
        songplay_data = (
            # index,  # TODO replace with auto indexing
            row['ts_timestamp'],
            row['userId'],
            row['level'],
            songid,
            artistid,
            row['sessionId'],
            row['location'],
            row['userAgent']
        )
        cur.execute(songplay_table_insert, songplay_data)

        logartist_data = (row['artist'],)
        cur.execute(logartist_table_insert, logartist_data)


def process_data(cur, conn, filepath, func):
    """Process data by iterating over several files in filepath."""

    # get all files matching extension from directory
    all_files = []
    for root, dirs, files in os.walk(filepath):
        files = glob.glob(os.path.join(root, '*.json'))
        for f in files:
            all_files.append(os.path.abspath(f))

    # get total number of files found
    num_files = len(all_files)
    print('{} files found in {}'.format(num_files, filepath))

    # iterate over files and process
    for i, datafile in enumerate(all_files, 1):
        func(cur, datafile)
        conn.commit()
        print('{}/{} files processed.'.format(i, num_files))


def main():
    """Reads JSON files specified in filepaths and writes to SQL tables."""

    conn = psycopg2.connect("host=127.0.0.1 dbname=sparkifydb user=student password=student")
    cur = conn.cursor()

    process_data(cur, conn, filepath='data/song_data', func=process_song_file)
    process_data(cur, conn, filepath='data/log_data', func=process_log_file)

    conn.close()


if __name__ == "__main__":
    main()
