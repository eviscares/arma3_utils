#!/usr/bin/python3
import sqlite3
from sqlite3 import Error

class arma3_db:
    """Simple class to manage the sqlite db"""

    db_file = ""

    def create_connection(self):
        """ create a database connection to a SQLite database """
        conn = None
        try:
            conn = sqlite3.connect(self.db_file)
            print(sqlite3.version)
            c = conn.cursor()
            c.execute("CREATE TABLE IF NOT EXISTS mods ( " \
                      "steam_id integer unique" \
                      ");")
        except Error as e:
            print(e)
        finally:
            if conn:
                conn.close()


    if __name__ == '__main__':
        create_connection(r"arma3_utils.db")