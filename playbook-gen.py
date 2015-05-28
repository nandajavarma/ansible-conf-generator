#!/usr/bin/python
import sys
import os
import argparse
import ConfigParser
import yaml

class PlaybookGen(object):
    def __init__(self):
        self.helper = HelperMethods()
        self.group_name = 'rhs-servers'
        self.args = self.parse_arguments()
        self.dest_dir = self.helper.get_file_dir_path('.', self.args.dest_dir or 'playbooks')
        if not os.path.isdir(self.dest_dir):
            self.helper.exec_cmds('mkdir', self.dest_dir)
        self.config_file = self.args.config_file.name
        self.parse_read_config()
        self.hosts = self.helper.get_host_names(self.config_parse)
        self.create_inventory_file()
        GroupVarsGen(self.config_parse, self.dest_dir, self.group_name)


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

    def parse_read_config(self):
        self.config_parse = self.helper.call_config_parser()
        self.config_parse.read(self.config_file)


    def create_inventory_file(self):
        self.inventory_file = self.helper.get_file_dir_path(self.dest_dir, 'ansible_hosts')
        self.helper.parse_config_write(self.group_name, self.hosts, self.inventory_file)

class HelperMethods(object):

    def get_host_names(self, config_parse):
        try:
            return self.config_get_options(config_parse, 'hosts')
        except:
            print "Cannot find the section hosts in the config. The generator can't proceed. Exiting!"
            sys.exit(0)

    def write_yaml(self, data_dict, yml_file):
        print data_dict
        with open(yml_file, 'w') as outfile:
            outfile.write(yaml.dump(data_dict, default_flow_style=False))


    def config_section_map(self, config_parse, section, option):
        try:
            return config_parse.get(section, option)
        except (ConfigParser.NoSectionError, ConfigParser.NoOptionError) as e:
            print e

    def config_get_options(self, config_parse, section):
        try:
            return config_parse.options(section)
        except ConfigParser.NoSectionError as e:
            print e

    def config_get_sections(self, config_parse):
        try:
            return config_parse.sections()
        except ConfigParser.Error as e:
            print e

    def get_file_dir_path(self, basedir, newdir):
        return os.path.join(os.path.realpath(basedir), newdir)

    def exec_cmds(self, cmd, opts):
        try:
            os.system(cmd + ' ' + opts)
        except:
            print "Command %s failed. Exiting!" % cmd
            sys.exit()

    def call_config_parser(self):
        return ConfigParser.ConfigParser(allow_no_value=True)

    def parse_config_write(self, section, options, filename):
        config = self.call_config_parser()
        config.add_section(section)
        for option in options:
            config.set(section, option)
        try:
            with open(filename, 'wb') as file:
                config.write(file)
        except:
            print "Failed to create file %s. Exiting!" % filename
            sys.exit(0)

class GroupVarsGen(object):
    def __init__(self, config_parse, dirname, group_name):
        self.helper = HelperMethods()
        self.config_parse = config_parse
        self.dirname = dirname
        self.group_name = group_name
        self.group_vars_dir = self.helper.get_file_dir_path(self.dirname, 'group_vars')
        self.helper.exec_cmds('mkdir', self.group_vars_dir)
        self.group_vars_file_path = self.helper.get_file_dir_path(self.group_vars_dir, self.group_name)
        self.helper.exec_cmds('touch', self.group_vars_file_path)
        self.create_group_vars()

    def create_group_vars(self):
        options = self.helper.config_get_sections(self.config_parse)
        self.hosts = self.helper.get_host_names(self.config_parse)
        host_options = self.hosts + ['hosts']
        group_options = [val for val in options if val not in host_options]
        data = {}
        for section in group_options:
            options = self.helper.config_get_options(self.config_parse, section)
            data[section]  = options
            self.helper.write_yaml(data, self.group_vars_file_path)



if __name__ == '__main__':
    PlaybookGen()
