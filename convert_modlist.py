#!/usr/bin/python3
import sqlite3
import yaml
import os
import errno
import io
from argparse import ArgumentParser
from sqlite3 import Error
from collections import defaultdict

def parse_args():
    parser = ArgumentParser()
    parser.add_argument('-f', '--filename', help='Name of html modlist to parse', required=True)
    parser.add_argument('-d', help='Debugmode', dest='debugmode', action='store_true')
    return parser.parse_args()


def load_config(args):
    if not args.debugmode:
        with open('config.yaml') as file:
            config = yaml.load(file)
        #config = yaml.load(file, Loader=yaml.FullLoader)
        return config
    else:
        config = defaultdict(dict)
        config['user']['username'] = 'DebugUser'
        config['user']['password'] = 'DebugUser'
        config['paths']['base_path'] = '.'
        config['paths']['mod_config_folder'] = 'configs'
        return config


def get_folder_name(mod_id, conn):
    folder_name = ''
    c = conn.cursor()
    try:
        c.execute('select rowid from mods where steam_id = {};'.format(mod_id))
        row = c.fetchone()
        if row is not None:
            folder_name = row
        else:
            c.execute('insert into mods (steam_id) values ({});'.format(mod_id))
            conn.commit()
            c.execute('select rowid from mods where steam_id={};'.format(mod_id))
            folder_name = c.fetchone()
    except Error as e:
        print(e)
    return folder_name[0]


def write_config(folder_names, config_name, env):
    mods = '"'
    path = os.path.join(env['paths']['base_path'], env['paths']['mod_config_folder'])
    config_path = os.path.join(path, config_name + '.conf')
    try:
        os.mkdir(path)
    except OSError as exc:
        if exc.errno != errno.EEXIST:
            print ('Creation of the directory {} failed'.format(path))
            raise
        else:
            pass            
    else:
        print ('Succesfully created {}'.format(path))
    
    for folder_name in folder_names:
        mods += 'mods/{}\;'.format(folder_name)
    mods += '"\n'

    with open('mod_config_template.conf', 'r') as template:
        with open(config_path, 'w') as target:
            for line in template:
                if line.startswith('steamuser'):
                    line = line.replace('USERNAME', env['user']['username'])
                if line.startswith('steampass'):
                    line = line.replace('PASSWORD', env['user']['password'])
                if line.startswith('mods'):
                    line = line.strip() + mods
                target.write(line)

    return 'Not implemented'


def main():
    download_link_line='<a href=\"http://steamcommunity.com/sharedfiles/filedetails/?id='
    mod_ids = []
    folder_names = []
    conn = sqlite3.connect('arma3_utils.db')
    args = parse_args()
    config = load_config(args)
    with open('modlist.html') as file:
        for line in file:
            if '<h1>' in line:
                modlist_name = line.lstrip().split('<strong>')[1].replace('</strong></h1>', '').rstrip()
                print(modlist_name)
            if download_link_line in line:
                line = line.lstrip()
                id = line.split()[1].split('=')[2].replace('\"','')
                mod_ids.append(id)

    for mod_id in mod_ids:
        folder_names.append(get_folder_name(mod_id, conn))
    config_written = write_config (folder_names, modlist_name, config)
    print(config_written)
    conn.close()


if __name__ == '__main__':
    main()
