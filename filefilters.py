import os
import subprocess
from helpers import *


class BaseFilter(object):
    """Basic filter class that does not filter out anythin."""

    def __init__(self, **kwargs):
        self.config = kwargs["config"]

    def get_status(self, filename):
        home_filepath = prefix_home_path(filename)
        if os.path.exists(home_filepath):
            return Status.BACKUP_ABLE


class CommandFilter(BaseFilter):
    """This execute a command at $HOME, and take the output as a filter to
    filter out backuped files."""

    def __init__(self, **kwargs):
        super(CommandFilter, self).__init__(**kwargs)
        out = subprocess.run(
            self.config.command,
            shell=True,
            cwd=os.path.expanduser("~"),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        ).stdout
        self.tracked = set(out.decode().split())

    def get_status(self, filename):
        home_filepath = prefix_home_path(filename)
        if filename in self.tracked:
            return Status.EXISTS
        elif os.path.exists(home_filepath):
            return Status.BACKUP_ABLE


class SymlinkFilter(BaseFilter):
    """This check for backuped file by checking symlink status."""

    def get_status(self, filename):
        home_filepath = prefix_home_path(filename)
        backup_filepath = self.add_symlink_path(filename)
        if is_actual_file(home_filepath):
            # The following 3 conditions denotes it is already in a state that we WANT
            # (so we negate it if all three matches)
            if not (
                os.path.islink(backup_filepath)
                and is_actual_file(home_filepath)
                and os.path.samefile(home_filepath, backup_filepath)
            ):
                return Status.BACKUP_ABLE

        if os.path.islink(home_filepath):
            return Status.BROKEN_LINK

        if os.path.exists(backup_filepath) and os.path.samefile(
            home_filepath, backup_filepath
        ):
            return Status.EXISTS

    def add_symlink_path(self, filename):
        return os.path.join(self.config.symlink_dir, filename)
