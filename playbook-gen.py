#!/usr/bin/python
import sys
import os
import argparse
import ConfigParser

class PlaybookGen(object):
    def __init__(self):
        self.args = self.parse_arguments()
        self.dest_dir = self.get_file_dir_path('.', self.args.dest_dir or 'playbooks')
        if not os.path.isdir(self.dest_dir):
            self.exec_cmds('mkdir', self.dest_dir)
        self.config_file = self.args.config_file.name
        self.parse_read_config()
        self.get_host_names()
        self.create_inventory_file()


    def parse_arguments(self):
        parser = argparse.ArgumentParser(version='1.0')
        parser.add_argument('-c', dest='config_file',
                help="Configuration file",
                type=argparse.FileType('rt'),
                required=True)
        parser.add_argument('-d', dest='dest_dir',
                help="Directory to save backend setup playbooks.",
                default='playbooks')
        try:
            return parser.parse_args()
        except IOError as msg:
            parser.error(str(msg))

    def get_file_dir_path(self, basedir, newdir):
        return os.path.join(os.path.realpath(basedir), newdir)

    def exec_cmds(self, cmd, opts):
        try:
            os.system(cmd + ' ' + opts)
        except:
            print "Command %s failed. Exiting!" % cmd
            sys.exit()


    def parse_read_config(self):
        self.config_parse = self.call_config_parser()
        self.config_parse.read(self.config_file)

    def call_config_parser(self):
        return ConfigParser.ConfigParser(allow_no_value=True)

    def get_host_names(self):
        self.hosts = self.config_get_options('hosts')
        if not self.hosts:
            print "Cannot find the section hosts in the config. The generator can't proceed. Exiting!"
            sys.exit(0)

    def config_get_options(self, section):
        try:
            return self.config_parse.options(section)
        except ConfigParser.NoSectionError as e:
            print e

    def create_inventory_file(self):
        self.inventory_file = self.get_file_dir_path(self.dest_dir, 'ansible_hosts')
        config = self.call_config_parser()
        config.add_section('rhs-servers')
        for host in self.hosts:
            config.set('rhs-servers', host)
        try:
            with open(self.inventory_file, 'wb') as inventoryfile:
                config.write(inventoryfile)
        except:
            print "Failed to create inventory file. Exiting!"
            sys.exit(0)

    def config_section_map(section, option):
        try:
            return self.config_parse.get(section, option)
        except (ConfigParser.NoSectionError, ConfigParser.NoOptionError) as e:
            print e


if __name__ == '__main__':
    PlaybookGen()
