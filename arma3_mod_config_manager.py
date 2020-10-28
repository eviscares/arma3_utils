#!/usr/bin/python3

import os
import re
import psutil
import shutil
import time
import subprocess
from argparse import ArgumentParser
from datetime import datetime
from urllib import request
import json

# Load Config from yaml file to make it more user friendly
with open('config.json') as file:
    config = json.load(file)

# Load the list of mods
with open('mods.json') as file:
    MODS = json.load(file)

# Neccessary variables that we need to establish
STEAM_USER = config['user']['username']
STEAM_PASS = config['user']['password']

BASE_PATH = config['paths']['base_path']
MOD_DIRECTORY = BASE_PATH + config['paths']['mod_directory']
KEY_DIRECTORY = BASE_PATH + config['paths']['key_directory']
CONFIG_PATH = BASE_PATH + config['paths']['config_file']
MODLIST_DIR = BASE_PATH + config['paths']['modlist_dir']

MOD_CONFIG_FOLDER = BASE_PATH + config['paths']['mod_config_folder']

LGSM_BINARY = BASE_PATH + config['lgsm_binary']

ARMA3_WORKSHOP_DIRECTORY = config['paths']['workshop_dir'] + str(config['arma3_workshop_id'])

LOG_PATH = BASE_PATH + config['paths']['log_path']

STEAM_CHANGELOG_URL = config['steam_changelog_url']

STEAM_CMD = config['steam_cmd']

#This is only for serving your modlist via webserver
WEB_ROOT =config['paths']['web_root']

# Regex Patterns
TITLE_PATTERN = re.compile(r"(?<=<div class=\"workshopItemTitle\">)(.*?)(?=<\/div>)", re.DOTALL)
LOGIN_PATTERN = re.compile(r'^\s\d+\:\d+\:\d+\s(Player)\s.*(connecting)\.$')
LOGOUT_PATTERN = re.compile(r'^\s\d+\:\d+\:\d+\s(Player)\s.*\s(disconnected)\.$')
UPDATE_PATTERN = re.compile(r"workshopAnnouncement.*?<p id=\"(\d+)\">", re.DOTALL)
KEY_PATTERN = re.compile(r'(key).*', re.I)

def parse_args():
    parser = ArgumentParser()

    subparsers = parser.add_subparsers(title='Commands', dest="command")

    # Create modlist without parameters
    subparser = subparsers.add_parser('generate_modlist')

    # Activate Config with parameters
    subparser = subparsers.add_parser('activate_config')
    subparser.add_argument('--name', help='Name of the Config file to activate', required=True)
    subparser.add_argument('--restart', help='Restart the arma3 server after config file was activated',
                           action='store_true')
    subparser.add_argument('--force', help='Restart the server even if players are on it.',
                           action='store_true')
    # Update Mods
    subparser = subparsers.add_parser('update_mods')

    return parser.parse_args()

def call_steamcmd(params):
    os.system("{} {}".format(STEAM_CMD, params))
    print("")

def mod_needs_update(mod_id, path):
    if os.path.isdir(path):
        response = request.urlopen("{}/{}".format(STEAM_CHANGELOG_URL, mod_id)).read()
        response = response.decode("utf-8")
        match = UPDATE_PATTERN.search(response)

        if match:
            updated_at = datetime.fromtimestamp(int(match.group(1)))
            created_at = datetime.fromtimestamp(os.path.getctime(path))

            return updated_at >= created_at

    return False

# TODO: Pull this apart, so that the frontend handles which mods get updated, and the backend just updates
def update_mods():
    for mod_name, mod_id in MODS.items():
        path = "{}/{}".format(ARMA3_WORKSHOP_DIRECTORY, mod_id)

        # Check if mod needs to be updated
        if os.path.isdir(path):

            if mod_needs_update(mod_id, path):
                # Delete existing folder so that we can verify whether the
                # download succeeded
                shutil.rmtree(path)
            else:
                print("No update required for \"{}\" ({})... SKIPPING".format(mod_name, mod_id))
                continue

        # Keep trying until the download actually succeeded
        tries = 0
        while os.path.isdir(path) is False and tries < 10:
            print("Updating \"{}\" ({}) | {}".format(mod_name, mod_id, tries + 1))

            steam_cmd_params = " +login {} {}".format(STEAM_USER, STEAM_PASS)
            steam_cmd_params += " +workshop_download_item {} {} validate".format(
                config['arma3_workshop_id'],
                mod_id
            )
            steam_cmd_params += " +quit"
            call_steamcmd(steam_cmd_params)
            # Sleep for a bit so that we can kill the script if needed
            time.sleep(5)
            tries = tries + 1
        if tries >= 10:
            print("!! Updating {} failed after {} tries !!".format(mod_name, tries))


def lowercase_workshop_dir():
    os.system("(cd {} && find . -depth -exec rename -v 's/(.*)\/([^\/]*)/$1\/\L$2/' {{}} \;)".format(ARMA3_WORKSHOP_DIRECTORY))


def create_mod_symlinks():
    for mod_name, mod_id in MODS.items():
        link_path = "{}{}".format(MOD_DIRECTORY, mod_name)
        real_path = "{}/{}".format(ARMA3_WORKSHOP_DIRECTORY, mod_id)

        if os.path.isdir(real_path):
            if not os.path.islink(link_path):
                os.symlink(real_path, link_path)
                print("Creating symlink '{}'...".format(link_path))
        else:
            print("Mod '{}' does not exist! ({})".format(mod_name, real_path))

def copy_keys():
    # Check for broken symlinks
    for key in os.listdir(KEY_DIRECTORY):
        key_path = "{}/{}".format(KEY_DIRECTORY, key)
        if os.path.islink(key_path) and not os.path.exists(key_path):
            print("Removing outdated server key '{}'".format(key))
            os.unlink(key_path)
    # Update/add new key symlinks
    for mod_name, mod_id in MODS.items():
        real_path = "{}/{}".format(ARMA3_WORKSHOP_DIRECTORY, mod_id)
        if not os.path.isdir(real_path):
            print("Couldn't copy key for mod '{}', directory doesn't exist.".format(mod_name))
        else:
            dirlist = os.listdir(real_path)
            keyDirs = [x for x in dirlist if re.search(KEY_PATTERN, x)]

            if keyDirs:
                keyDir = keyDirs[0]
                if os.path.isfile("{}/{}".format(real_path, keyDir)):
                    # Key is placed in root directory
                    key = keyDir
                    key_path = os.path.join(KEY_DIRECTORY, key)
                    if not os.path.exists(key_path):
                        print("Creating symlink to key for mod '{}' ({})".format(mod_name, key))
                        os.symlink(os.path.join(real_path, key), key_path)
                else:
                    # Key is in a folder
                    for key in os.listdir(os.path.join(real_path, keyDir)):
                        real_key_path = os.path.join(real_path, keyDir, key)
                        key_path = os.path.join(KEY_DIRECTORY, key)
                        if not os.path.exists(key_path):
                            print("Creating symlink to key for mod '{}' ({})".format(mod_name, key))
                            os.symlink(real_key_path, key_path)
            else:
                print("!! Couldn't find key folder for mod {} !!".format(mod_name))

def generate_modlist():
    prev_line = ''
    mod_list = {}
    with open(CONFIG_PATH) as f:
        for line in f:
            if line.startswith('mods='):
                mod_line = line
                if prev_line.startswith('#'):
                    comment_line = prev_line
            prev_line = line
    if comment_line:
        mod_list['title'] = comment_line.strip('#').strip()
    mod_line = mod_line.strip('mods=').replace('\"','').strip().replace('mods/','').replace('\\','').split(';')
    mod_line.remove('')
    
    for mod in mod_line:
        mod_list[mod] = os.readlink('{}{}'.format(MOD_DIRECTORY, mod)).split('/')[-1]
    return mod_list

def generate_preset(mod_list):
    if 'title' in mod_list:
        modlist_filename = '{}.html'.format(mod_list['title'].replace(' ', '_').lower())
    else:
        modlist_filename = 'modlist.html'
    modlist_path = MODLIST_DIR + modlist_filename
    if os.path.isfile(modlist_path):
        os.remove(modlist_path)
    try:
        f = open(modlist_path, "w+")
        f.write(('<?xml version="1.0" encoding="utf-8"?>\n'
                 '<html>\n\n'
                 '<!--Created using arma3_utils by eviscares, based on the work of marceldev89 and Freddo3000.-->\n'
                 '<head>\n'
                 '<meta name="arma:Type" content="{}" />\n'
                 '<meta name="arma:PresetName" content="{}" />\n'
                 '<meta name="generator" content="arma3_utils"/>\n'
                 ' <title>Arma 3</title>\n'
                 '<link href="https://fonts.googleapis.com/css?family=Roboto" rel="stylesheet" type="text/css" />\n'
                 '<style>\n'
                 'body {{\n'
                 'margin: 0;\n'
                 'padding: 0;\n'
                 'color: #fff;\n'
                 'background: #000;\n'
                 '}}\n'
                 'body, th, td {{\n'
                 'font: 95%/1.3 Roboto, Segoe UI, Tahoma, Arial, Helvetica, sans-serif;\n'
                 '}}\n'
                 'td {{\n'
                 'padding: 3px 30px 3px 0;\n'
                 '}}\n'
                 'h1 {{\n'
                 'padding: 20px 20px 0 20px;\n'
                 'color: white;\n'
                 'font-weight: 200;\n'
                 'font-family: segoe ui;\n'
                 'font-size: 3em;\n'
                 'margin: 0;\n'
                 '}}\n'
                 'h2 {{'
                 'color: white;'
                 'padding: 20px 20px 0 20px;'
                 'margin: 0;'
                 '}}'
                 'em {{\n'
                 'font-variant: italic;\n'
                 'color:silver;\n'
                 '}}\n'
                 '.before-list {{\n'
                 'padding: 5px 20px 10px 20px;\n'
                 '}}\n'
                 '.mod-list {{\n'
                 'background: #282828;\n'
                 'padding: 20px;\n'
                 '}}\n'
                 '.optional-list {{\n'
                 'background: #222222;\n'
                 'padding: 20px;\n'
                 '}}\n'
                 '.dlc-list {{\n'
                 'background: #222222;\n'
                 'padding: 20px;\n'
                 '}}\n'
                 '.footer {{\n'
                 'padding: 20px;\n'
                 'color:gray;\n'
                 '}}\n'
                 '.whups {{\n'
                 'color:gray;\n'
                 '}}\n'
                 'a {{\n'
                 'color: #D18F21;\n'
                 'text-decoration: underline;\n'
                 '}}\n'
                 'a:hover {{\n'
                 'color:#F1AF41;\n'
                 'text-decoration: none;\n'
                 '}}\n'
                 '.from-steam {{\n'
                 'color: #449EBD;\n'
                 '}}\n'
                 '.from-local {{\n'
                 'color: gray;\n'
                 '}}\n'
                 ).format("Modpack", mod_list['title']))

        f.write(('</style>\n'
                 '</head>\n'
                 '<body>\n'
                 '<h1>Arma 3  - {} <strong>{}</strong></h1>\n'
                 '<p class="before-list">\n'
                 '<em>Drag this file or link to it to Arma 3 Launcher or open it Mods / Preset / Import.</em>\n'
                 '</p>\n'
                 '<h2 class="list-heading">Required Mods</h2>'
                 '<div class="mod-list">\n'
                 '<table>\n'
                 ).format("Modpack", mod_list['title']))

        for mod_name, mod_id in mod_list.items():
            if mod_id not in mod_list['title']:
                mod_url = "http://steamcommunity.com/sharedfiles/filedetails/?id={}".format(mod_id)
                response = request.urlopen(mod_url).read()
                response = response.decode("utf-8")
                match = TITLE_PATTERN.search(response)
                if match:
                    mod_title = match.group(1)
                    f.write(('<tr data-type="ModContainer">\n'
                                '<td data-type="DisplayName">{}</td>\n'
                                '<td>\n'
                                '<span class="from-steam">Steam</span>\n'
                                '</td>\n'
                                '<td>\n'
                                '<a href="{}" data-type="Link">{}</a>\n'
                                '</td>\n'
                                '</tr>\n'
                                ).format(mod_title, mod_url, mod_url))

        f.write('</table>\n'
                '</div>\n'
                '<div class="footer">\n'
                '<span>Created using arma3_utils by eviscares, based on the work of marceldev89 and Freddo3000.</span>\n'
                '</div>\n'
                '</body>\n'
                '</html>\n'
                )
    except (OSError, IOError):
        print('Problem writing to {}'.format(modlist_path))

def activate_config(config_name):
    config_to_activate = MOD_CONFIG_FOLDER + config_name
    try:
        os.symlink(config_to_activate, CONFIG_PATH)
    except FileExistsError:
        os.remove(CONFIG_PATH)
        os.symlink(config_to_activate, CONFIG_PATH)
    generate_preset(generate_modlist())
    modlist = MODLIST_DIR + config_name.replace('cfg', 'html')
    if os.path.isdir(WEB_ROOT) and os.path.isfile(modlist):
        if os.path.islink(WEB_ROOT + 'modlist.html') and not os.path.exists(WEB_ROOT + 'modlist.html'):
            print('Removing old modlist.')
            os.unlink(WEB_ROOT + 'modlist.html')
        print('Linking {} to {}'.format(modlist, WEB_ROOT + 'modlist.html' ))
        try:
            os.symlink(modlist, WEB_ROOT)
        except PermissionError:
            print('Can not link, check your permissions.')

def check_running(process_name):
    for proc in psutil.process_iter():
        try:
            if process_name.lower() in proc.name().lower():
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False

def check_empty():
    player_list = []
    with open(LOG_PATH) as f:
        for line in f:
            if LOGIN_PATTERN.match(line):
                player_list.append(line.split()[2])
            if LOGOUT_PATTERN.match(line):
                if line.split()[2] in player_list:
                    player_list.remove(line.split()[2])
    if len(player_list) == 0:
        return True
    else:
        return False

def restart_server(args):
    if config['lgsm_binary'] != '' and os.path.isfile(LGSM_BINARY):
        if check_running(config['lgsm_binary']):
            print("{} is running. Parsing logs to see if it is empty.".format(LGSM_BINARY))
            if check_empty() or args.force:
                subprocess.run([LGSM_BINARY, 'restart'])
            else:
                print('Server not empty and --force not supplied.')
        else:
            print('Server not running.')
    else:
        print('No lgsm binary configured, or binary not found. \
             Can not automatically restart.')


def main():
    args = parse_args()
    if args.command=='generate_modlist':
        generate_preset(generate_modlist())
    if args.command=='activate_config':
        print('Activating config {}'.format(args.name))
        activate_config(args.name)
    if args.command=='update_mods':
        print('Checking for updates...')
        update_mods()
        print('Converting to lowercase...')
        lowercase_workshop_dir()
        print('Creating symlinks for mod folders...')
        create_mod_symlinks()
        print('Creating symlinks for keys...')
        copy_keys()
    try:
        if args.restart:
            print('Restarting server...')
            restart_server(args)
    except AttributeError:
        pass


       
if __name__ == '__main__':
    main()
