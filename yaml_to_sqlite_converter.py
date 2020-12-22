#!/usr/bin/python3
import sqlite3
import yaml

with open('mods.yaml') as file:
    #MODS = yaml.load(file, Loader=yaml.FullLoader)
    MODS = yaml.load(file)

conn = sqlite3.connect('arma3_utils.db')
c = conn.cursor()

for steam_id in MODS.values():
    try:
        print("Inserting {}".format(steam_id))
        c.execute("INSERT INTO mods (steam_id) VALUES ({});".format(steam_id))
        conn.commit()
    except:
        print('Cant insert {}. Skipping...'.format(steam_id))

conn.commit()
conn.close()