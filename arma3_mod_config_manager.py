#!/usr/bin/python3

import os
import re
import yaml
from argparse import ArgumentParser
from urllib import request

# Load Config from yaml file to make it more user friendly
with open('config.yaml') as file:
    config = yaml.load(file, Loader=yaml.FullLoader)

BASE_PATH = config['folders']['base_path']
MOD_DIRECTORY = BASE_PATH + config['folders']['mod_directory']
CONFIG_PATH = BASE_PATH + config['folders']['config_directory']
MOD_CONFIG_FOLDER = BASE_PATH + config['folders']['mod_config_folder']
TITLE_PATTERN = re.compile(r"(?<=<div class=\"workshopItemTitle\">)(.*?)(?=<\/div>)", re.DOTALL)

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
    return parser.parse_args()

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
    modlist_path = BASE_PATH + modlist_filename
    f = open(modlist_path, "w+")
    f.write(('<?xml version="1.0" encoding="utf-8"?>\n'
             '<html>\n\n'
             '<!--Created using modlist_generator.py by eviscares, based on the work of marceldev89 and Freddo3000.-->\n'
             '<head>\n'
             '<meta name="arma:Type" content="{}" />\n'
             '<meta name="arma:PresetName" content="{}" />\n'
             '<meta name="generator" content="modlist_generator.py"/>\n'
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
            '<span>Created using modlist_generator.py by eviscares, based on the work of marceldev89 and Freddo3000.</span>\n'
            '</div>\n'
            '</body>\n'
            '</html>\n'
            )

def main():
    args = parse_args()
    if args.command=='generate_modlist':
        print('generate_preset(generate_modlist())')
    if args.command=='activate_config':
        print('Activating {}.'.format(args.command, args.name))
        #create symlink
        if args.restart:
            print('Restarting server')
            #restart the server

if __name__ == '__main__':
    main()
