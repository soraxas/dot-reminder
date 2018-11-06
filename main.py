import sys
import os
import re
import glob
from helpers import *
import filefilters

try:
    import configparser
except ImportError:
    import ConfigParser as configparser


def main(args):
    """Main function."""
    config = Configuration()
    config.verbosity = args['verbosity']

    backuped_files = []
    # try to read from stdin
    if not os.isatty(0):
        # reading from terminal
        for line in sys.stdin:
            backuped_files.append(line.rstrip())

    config.backuped_files = backuped_files

    configParse = configparser.SafeConfigParser(allow_no_value=True)
    configParse.optionxform = str

    if configParse.read(args['config']):
        config.apps_dir = configParse.get('core', 'APPS_DIR')

        if configParse.has_option('core', 'METHOD'):
            config.method = configParse.get('core', 'METHOD')

        if config.method == 'symlink':
            # must provide a command config
            config.symlink_dir = configParse.get('core', 'SYMLINK_DIR')
        elif config.method == 'command':
            # must provide a command config
            config.command = configParse.get('core', 'COMMAND')

        if configParse.has_section('ignore_paths'):
            for path in configParse.options('ignore_paths'):
                config.ignores.append(path)
    else:
        print("Failed to read config file '{}'".format(args['config']))
        exit(1)

    # Get the command line arg
    app_db = ApplicationsDatabase(config)

    apps_to_backup = app_db.get_app_names()
    apps_to_ignore = []
    # Remove the specified apps to ignore
    for app_name in apps_to_ignore:
        apps_to_backup.discard(app_name)

    # build filefilters
    if config.method == 'base':
        file_filter = filefilters.BaseFilter(config=config)
    elif config.method == 'symlink':
        file_filter = filefilters.SymlinkFilter(config=config)
    elif config.method == 'command':
        file_filter = filefilters.CommandFilter(config=config)
    else:
        raise Exception("Unrecognised method: {}!".format(config.method))

    os.chdir(os.path.expanduser('~'))
    # List each application
    for app_name in sorted(apps_to_backup):
        app_files = list_backupable_app(
            files=app_db.get_files(app_name),
            config=config,
            file_filter=file_filter
        )
        # We skip if none of the file exists (assume not installed), or verbose level >= 3
        app_not_installed = all(f[0] is Status.NOT_EXISTS for f in app_files)
        if config.verbosity < 3 and app_not_installed:
            continue
        lines = []
        for b_file in sorted(app_files):
            if args['minimal']:
                if b_file[0] is Status.BACKUP_ABLE:
                    print(b_file[1])
            # verbosity level 1 includes backuped file, level 2 includes non existing files
            elif (b_file[0] is Status.BACKUP_ABLE
                  or b_file[0] is Status.BROKEN_LINK
                  or config.verbosity >= 1 and b_file[0] is Status.EXISTS
                  or config.verbosity >= 2 and b_file[0] is Status.NOT_EXISTS):
                if app_not_installed:
                    # switch the status if this app is not something we care much
                    b_file[0] = Status.NOT_INSTALLED
                formatted_status = fmt_status(b_file)
                lines.append(" >> {:<22}: {:<20}".format(
                    formatted_status[0], formatted_status[1]))
        if len(lines) > 0:
            print("[ {} ]".format(ColorFormatCodes.BOLD + app_db.get_name(
                app_name) + ColorFormatCodes.NORMAL))
            print("\n".join(lines))


class ApplicationsDatabase(object):
    """Database containing all the configured applications."""

    def __init__(self, conf):
        # main apps dir
        config_files = []
        for _apps_dir in conf.apps_dir.split(','):
            # clean white space
            _apps_dir = _apps_dir.strip()
            apps_dir = os.path.join(
                os.path.dirname(os.path.realpath(__file__)), _apps_dir)
            config_files.extend([
                os.path.join(apps_dir, filename)
                for filename in os.listdir(apps_dir)
                if filename.endswith('.cfg')
            ])
        # Build the dict that will contain the properties of each application
        self.apps = dict()
        for config_file in set(config_files):
            config = configparser.SafeConfigParser(allow_no_value=True)
            # Needed to not lowercase the configuration_files in the ini files
            config.optionxform = str
            if config.read(config_file):
                # Get the filename without the directory name
                filename = os.path.basename(config_file)
                # The app name is the cfg filename with the extension
                app_name = filename[:-len('.cfg')]
                # Start building a dict for this app
                self.apps[app_name] = dict()
                # Add the fancy name for the app, for display purpose
                app_pretty_name = config.get('application', 'name')
                self.apps[app_name]['name'] = app_pretty_name
                # Add the configuration files
                self.apps[app_name]['configuration_files'] = set()
                if config.has_section('configuration_files'):
                    for path in config.options('configuration_files'):
                        if path.startswith('/'):
                            raise ValueError('Unsupported absolute path: {}'
                                             .format(path))
                        self.apps[app_name]['configuration_files'].add(path)
                # Add the XDG configuration files
                xdg_config_home = os.environ.get('XDG_CONFIG_HOME')
                if xdg_config_home:
                    if not os.path.exists(xdg_config_home):
                        raise ValueError('$XDG_CONFIG_HOME: {} does not exist'
                                         .format(xdg_config_home))
                    home = os.path.expanduser('~/')
                    if not xdg_config_home.startswith(home):
                        raise ValueError('$XDG_CONFIG_HOME: {} must be '
                                         'somewhere within your home '
                                         'directory: {}'.format(
                                             xdg_config_home, home))
                    if config.has_section('xdg_configuration_files'):
                        for path in config.options('xdg_configuration_files'):
                            if path.startswith('/'):
                                raise ValueError('Unsupported absolute path: '
                                                 '{}'.format(path))
                            path = os.path.join(xdg_config_home, path)
                            path = path.replace(home, '')
                            (self.apps[app_name]['configuration_files']
                             .add(path))

    def get_name(self, name):
        """Return the fancy name of an application."""
        return self.apps[name]['name']

    def get_files(self, name):
        """Return the list of config files of an application."""
        return self.apps[name]['configuration_files']

    def get_app_names(self):
        """Return application names."""
        app_names = set()
        for name in self.apps:
            app_names.add(name)
        return app_names


def list_backupable_app(files, config, file_filter):
    """
    Backup the application config files.
    """
    # For each file used by the application
    backupable_files = []
    for _filename in list(files):
        for filename in glob.glob(_filename):
            # print(filename)

            # ignore the user defined files
            if any(re.match(ignore, filename) for ignore in config.ignores):
                continue

            status = None
            # check for backuped files given from pipe:
            if filename in config.backuped_files:
                status = Status.EXISTS

            # If the file exists and is not already a link pointing to Original file
            if status is None:
                status = file_filter.get_status(filename)

            if status is None:
                status = Status.NOT_EXISTS

            backupable_files.append([status, filename])
    return backupable_files
