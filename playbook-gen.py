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
        self.force = self.args.force
        self.config_file = self.args.config_file.name
        self.parse_read_config()
        self.hosts = self.helper.get_host_names(self.config_parse)
        self.varfile, self.var_file_name = self.helper.validate_params(
                self.config_parse, self.hosts, self.group_name, self.dest_dir, self.force)
        self.create_inventory_file()
        if not self.varfile:
            print "Provide either configuration specific to each hosts " \
                    "or provide common configurations for all. Exiting!"
            sys.exit(0)
        if self.varfile == 'group_vars':
            GroupVarsGen(self.config_parse, self.dest_dir, self.group_name, self.var_file_name[0])


    def parse_arguments(self):
        parser = argparse.ArgumentParser(version='1.0')
        parser.add_argument('-c', dest='config_file',
                help="Configuration file",
                type=argparse.FileType('rt'),
                required=True)
        parser.add_argument('-d', dest='dest_dir',
                help="Directory to save backend setup playbooks.",
                default='playbooks')
        parser.add_argument('-f', dest='force', const='y',
            default='n',
            action='store',
            nargs='?',
            help="Force files and directories to be " \
                    "overwritten if already exists.")
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

    def validate_params(self, config_parse, hosts, group_name, dirname, force):
        self.force = force
        self.group_name = group_name
        self.hosts = hosts
        self.config_parse = config_parse
        self.dirname = dirname
        self.create_required_files_and_dirs()
        return self.varfile, self.filepath

    def mk_dir(self, dirlists):
        for each in dirlists:
            if not os.path.isdir(each):
                self.exec_cmds('mkdir', each)
            elif self.force == 'n':
                print "Directory %s already exists. Use -f option to overwrite" % each
                sys.exit(0)
            else:
                continue

    def touch_files(self, filelists):
        for each in filelists:
            try:
                os.remove(each)
            except OSError:
                pass
            self.exec_cmds('touch', each)

    def create_required_files_and_dirs(self):
        options = self.config_get_sections(self.config_parse)
        set_options = set(options)
        set_host_options = set(self.hosts)
        other_sections = [x for x in options if x != 'hosts']
        if not other_sections:
            self.varfile = None
            self.filepath = None
        elif set_options.intersection(set_host_options):
            if set_host_options.issubset(set_options):
                self.varfile = 'host_vars'
                self.filepath = self.hosts
                print "Creating host_vars for all the hosts"
            else:
                print "Give configurations for all the hosts. Exiting!"
                sys.exit(0)
        else:
            self.varfile = 'group_vars'
            self.filepath = [self.get_file_dir_path(self.dirname,
                                         self.varfile + '/' + self.group_name)]
        if self.varfile:
            dirlist = [ self.dirname,
                    self.get_file_dir_path(self.dirname, self.varfile)]
            self.mk_dir(dirlist)
            self.touch_files(self.filepath)

    def insufficient_param_count(self, section, count):
        print "Please provide %s names for %s devices else leave the field empty" % (section, count)
        return False

    def write_unassociated_data(self, section, options, yamlfile):
        data = {}
        data[section]  = options
        self.write_yaml(data, yamlfile, False)

    def write_device_data(self, config_parse, yamlfile):
        self.config_parse = config_parse
        self.yamlfile = yamlfile
        options = self.config_get_options(self.config_parse, 'devices')
        self.write_unassociated_data('devices', options, self.yamlfile)
        return len(options)

    def write_optional_data(self, group_options, device_count, varfile):
        self.group_options = group_options
        self.device_count = device_count
        self.varfile = varfile
        self.write_vg_data()
        self.write_pool_data()
        self.write_lv_data()
        self.write_lvols_data()
        self.write_mountpoints_data()
        self.write_mntpath_data()
        return True

    def get_var_file_write_options(self, section, section_name):
        if section in self.group_options:
            options = (self.varfile == 'group') and self.config_get_options(self.config_parse, section) or ''
            if len(options) < self.device_count:
                return self.insufficient_param_count(section_name, self.device_count)
        else:
            options = []
            pattern = {'vgs': 'RHS_vg',
                       'pools': 'RHS_pool',
                       'lvs': 'RHS_lv',
                       'mountpoints': '/rhs/brick'
                      }[section]
            for i in range(1, self.device_count + 1):
                options.append(pattern + str(i))
        return options

    def write_vg_data(self):
        self.vgs = self.get_var_file_write_options('vgs', 'volume group')
        self.write_unassociated_data('vgs', self.vgs, self.yamlfile)

    def write_pool_data(self):
        self.pools = self.get_var_file_write_options('pools', 'logical pool')
        data = []
        for i, j in zip(self.pools, self.vgs):
            pools = {}
            pools['pool'] = i
            pools['vg'] = j
            data.append(pools)
        data_dict = dict(pools = data)
        self.write_yaml(data_dict, self.yamlfile, True)

    def write_lv_data(self):
        self.lvs = self.get_var_file_write_options('lvs', 'logical volume')
        data = []
        for i, j, k in zip(self.pools, self.vgs, self.lvs):
            pools = {}
            pools['pool'] = i
            pools['vg'] = j
            pools['lv'] = k
            data.append(pools)
        data_dict = dict(lvpools = data)
        self.write_yaml(data_dict, self.yamlfile, True)

    def write_lvols_data(self):
        self.lvols = ['/dev/' + i + '/' + j for i, j in zip(self.vgs, self.lvs)]
        data_dict = {}
        data_dict['lvols'] = self.lvols
        self.write_yaml(data_dict, self.yamlfile, False)

    def write_mountpoints_data(self):
        self.mntpts = self.get_var_file_write_options('mountpoints', 'volume group')
        data_dict = {}
        data_dict['mountpoints'] = self.mntpts
        self.write_yaml(data_dict, self.yamlfile, True)

    def write_mntpath_data(self):
        self.devices = []
        for i, j in zip(self.vgs, self.lvs):
            self.devices.append('/dev/%s/%s' % (i, j))
        data = []
        for i, j in zip(self.mntpts, self.devices):
            mntpath = {}
            mntpath['path'] = i
            mntpath['device'] = j
            data.append(mntpath)
        data_dict = dict(mntpath = data)
        self.write_yaml(data_dict, self.yamlfile, True)


    def get_host_names(self, config_parse):
        try:
            return self.config_get_options(config_parse, 'hosts')
        except:
            print "Cannot find the section hosts in the config. The generator can't proceed. Exiting!"
            sys.exit(0)

    def write_yaml(self, data_dict, yml_file, data_flow):
        with open(yml_file, 'a+') as outfile:
            if not data_flow:
                outfile.write(yaml.dump(data_dict, default_flow_style=data_flow))
            else:
                outfile.write(yaml.dump(data_dict))


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
    def __init__(self, config_parse, dirname, group_name, filename):
        self.group_vars_file_path = filename
        self.helper = HelperMethods()
        self.config_parse = config_parse
        self.dirname = dirname
        self.group_name = group_name
        ret = self.create_group_vars()
        if not ret:
            print "Not creating group vars since no common option for devices provided"
            sys.exit(0)

    def create_group_vars(self):
        options = self.helper.config_get_sections(self.config_parse)
        self.hosts = self.helper.get_host_names(self.config_parse)
        host_options = self.hosts + ['hosts']
        group_options = [val for val in options if val not in host_options]
        if 'devices' in group_options:
            self.device_count = self.helper.write_device_data(self.config_parse, self.group_vars_file_path)
            self.varfile = 'group'
        else:
            return False
        group_options.remove('devices')
        return self.helper.write_optional_data(group_options, self.device_count, self.varfile)



if __name__ == '__main__':
    PlaybookGen()
