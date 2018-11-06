import os

class Status:
    BACKUP_ABLE = "Backup-able"
    EXISTS = "Backup-ed"
    NOT_EXISTS = "Not exists"
    NOT_INSTALLED = "Not installed"
    BROKEN_LINK = "WARNING: Broking link. You might want to fix it"


class Configuration():
    def __init__(self):
        self.apps_dir = None
        self.method = 'base'
        self.command = None
        self.symlink_dir = None
        self.ignores = []
        self.backuped_files = []
        self.verbosity = 0


class ColorFormatCodes:
    BLACK = "\033[1;30m"
    RED = "\033[1;31m"
    BLUE = "\033[1;34m"
    CYAN = "\033[1;36m"
    GREEN = "\033[0;32m"
    BROWN = "\033[0;33m"
    MAGENTA = "\033[0;35m"
    LIGHT_GREY = "\033[0;37m"
    RESET = "\033[0;0m"
    BOLD = "\033[;1m"
    REVERSE = "\033[;7m"
    NORMAL = '\033[0m'


############################################################
##                      FILES SYSTEM                      ##
############################################################


def prefix_home_path(filename):
    return os.path.join(os.environ['HOME'], filename)


def is_actual_file(filepath):
    """Return true if the given path is an actual file or directory."""
    return os.path.isfile(filepath) or os.path.isdir(filepath)


def is_link(filepath):
    """Return true if the given path is a link."""
    return os.path.islink(filepath)


############################################################
##                         FORMAT                         ##
############################################################


def fmt_file(str):
    return ColorFormatCodes.CYAN + str + ColorFormatCodes.NORMAL


def fmt_status(file_status):
    col = {
        Status.BACKUP_ABLE: ColorFormatCodes.GREEN,
        Status.EXISTS: ColorFormatCodes.BLUE,
        Status.NOT_EXISTS: ColorFormatCodes.MAGENTA,
        Status.NOT_INSTALLED: ColorFormatCodes.BROWN,
        Status.BROKEN_LINK: ColorFormatCodes.RED
    }.get(file_status[0], ColorFormatCodes.NORMAL)
    return [col + s + ColorFormatCodes.NORMAL for s in file_status]


def header(str):
    return ColorFormatCodes.RED + str + ColorFormatCodes.NORMAL


def bold(str):
    return ColorFormatCodes.BOLD + str + ColorFormatCodes.NORMAL
