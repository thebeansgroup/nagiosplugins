#!/usr/bin/env python
import sys
import textwrap
import subprocess
import os.path
from nagiosplugin import *

"""
Nagios plugin for checking free RAM. Returns detailed statistics for use by perfdata visualisation tools.
Stats are returned by parsing the output of `free`

Requirements
=============

This script requires the following python modules:

  * argparse (included with python 2.7, otherwise install with 'easy_install argparse')
"""

class RAM(NagiosPlugin):
    """
    A Nagios plugin to check RAM usage. Data is returned in perfdata format and is found using the 
    `free` command.
    """
    VERSION = '0.1'
    SERVICE = 'RAM'
    AUTHOR = 'Ally B'

    class Defaults(object):
        timeout = 3
        free_path = 'free'
        tail_path = 'tail'
        head_path = 'head'
        awk_path = 'awk'

    def __init__(self, opts):
        self.status = self.STATUS_UNKNOWN
        self.args = self.parse_args(opts)
        self.set_thresholds(self.args.warning, self.args.critical, self.args.time_periods)

    def parse_args(self, opts):
        """
        Parse given options and arguments
        """
        parser = self._default_parser(description=self.__doc__, version=self.VERSION, author=self.AUTHOR)

        parser.epilog="""Data is gathered by parsing the output of `free`. For more information on what the figures
            actually represent, read the `man` page for `free`."""

        parser.add_argument('--free-path', nargs='?', help="""Path to `free` binary. Default is to search
            the path.""", default=self.Defaults.free_path)
        parser.add_argument('--tail-path', nargs='?', help="""Path to `tail` binary. Default is to search
            the path.""", default=self.Defaults.tail_path)
        parser.add_argument('--head-path', nargs='?', help="""Path to `head` binary. Default is to search
            the path.""", default=self.Defaults.head_path)
        parser.add_argument('--awk-path', nargs='?', help="""Path to `awk` binary. Default is to search
            the path.""", default=self.Defaults.awk_path)
        parser.add_argument('-s', '--statistic', help=textwrap.dedent("""
        The statistic to check. Possible values are:

            total,
            used,
            free,
            shared,
            buffers,
            cached,
            used_less_buffers,
            free_plus_cache,
            swap_total,
            swap_used,
            swap_free
            """), nargs='?', required=True)

        args = parser.parse_args(opts)
        if 'verbose' not in args:
            args.verbose = False
        else:
            args.verbose = True

        return args

    def _get_statistic(self, statistic):
        "Returns a tuple containing the name of the specified statistic and its value."
        if not hasattr(self, 'statistic_retriever'):
            try:
                self.statistic_retriever = RAMStatistic(free_path = self.args.free_path,
                    tail_path = self.args.tail_path, head_path = self.args.head_path,
                    awk_path = self.args.awk_path)
            except Exception, error:
                raise NagiosPluginError("Error: %s" % (error))

        return self.statistic_retriever.get_statistic(statistic, self.args.verbose)

    def check(self):
        "Retrieves the required statistic value from the server, and finds out which status it corresponds to."
        self.statistic = self.args.statistic
        self.statistic_value = self._get_statistic(self.statistic)

        if self.args.verbose:
            print self.thresholds

        self.status = self._calculate_status(self.statistic_value)


class RAMStatistic(object):
    "Returns RAM usage"

    valid_stats = {
        'total': "%free% | %tail% -n 3 | %head% -n 1 | %awk% '{print $2}'",
        'used': "%free% | %tail% -n 3 | %head% -n 1 | %awk% '{print $3}'",
        'free': "%free% | %tail% -n 3 | %head% -n 1 | %awk% '{print $4}'",
        'shared': "%free% | %tail% -n 3 | %head% -n 1 | %awk% '{print $5}'",
        'buffers': "%free% | %tail% -n 3 | %head% -n 1 | %awk% '{print $6}'",
        'cached': "%free% | %tail% -n 3 | %head% -n 1 | %awk% '{print $7}'",
        'used_less_buffers': "%free% | %tail% -n 2 | %head% -n 1 | %awk% '{print $3}'",
        'free_plus_cache': "%free% | %tail% -n 2 | %head% -n 1 | %awk% '{print $4}'",
        'swap_total': "%free% | %tail% -n 1 | %awk% '{print $2}' ",
        'swap_used': "%free% | %tail% -n 1 | %awk% '{print $3}' ",
        'swap_free': "%free% | %tail% -n 1 | %awk% '{print $4}' ",
    }

    def __init__(self, free_path, tail_path, head_path, awk_path):
        """
        @param free_path Path to the `free` binary
        @param tail_path Path to the `tail` binary
        @param head_path Path to the `head` binary
        @param awk_path Path to the `awk` binary
        """
        self.free = free_path
        self.tail = tail_path
        self.head = head_path
        self.awk = awk_path

    def get_statistic(self, statistic, verbose=False):
        """
        Returns a statistic value.

        @param statistic The name of the statistic to retrieve
        @param vebose Whether to display verbose output
        """
        if not statistic in self.valid_stats:
            raise InvalidStatisticError("%s is not a valid statistic name." % statistic)

        command = self.valid_stats[statistic]

        # replace placeholders
        command = command.replace('%free%', self.free)
        command = command.replace('%tail%', self.tail)
        command = command.replace('%head%', self.head)
        command = command.replace('%awk%', self.awk)

        if verbose:
            print "Executing command: %s" % command

        stats = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True).stdout.read().strip()

        if verbose:
            print "Stats command returned '%s'" % stats

        return stats


if __name__ == '__main__':
    try:
        checker = RAM(sys.argv[1:])
        checker.check()
        status = checker.get_status()
        print checker.get_output()
        sys.exit(status)
    except (ThresholdValidatorError, InvalidStatisticError), e:
        print textwrap.fill(str(e), 80)
        sys.exit(NagiosPlugin.STATUS_UNKNOWN)
    except NagiosPluginError, e:
        print textwrap.fill("%s failed unexpectedly. Error was:" % (os.path.basename(__file__,)), 80)
        print textwrap.fill(str(e), 80)
        sys.exit(NagiosPlugin.STATUS_UNKNOWN)