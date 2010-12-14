#!/usr/bin/env python
import sys
import re
import MySQLdb
import textwrap
import os.path
import time
from nagiosplugin import *

"""
Nagios plugin for checking mysql instances. Returns detailed
statistics for use by perfdata visualisation tools.

Requirements
=============

This script requires the following python modules:

  * argparse (included with python 2.7, otherwise install with 'easy_install argparse')
  * MySQLdb (install with 'easy_install mysql-python' if easy_install is present)

Notes
=====

It's useful to monitor the following statistics:

  * Uptime
  * Com_delete - delta'd by time
  * Com_insert - delta'd by time
  * Com_replace - delta'd by time
  * Com_select - delta'd by time
  * Com_update - delta'd by time
  * Connections - delta'd by time
  * Max_used_connections
  * Qcache_free_memory
  * Qcache_lowmem_prunes - delta'd by time
  * Questions - delta'd by time
  * Select_full_join - delta'd by time
  * Table_locks_immediate - delta'd by time
  * Table_locks_waited - delta'd by time
  * Threads_cached
  * Threads_connected
  * Threads_created
  * Threads_running
"""

class MySQLStats(NagiosPlugin):
    """
    A Nagios plugin to check MySQL statistics. It can monitor any of the variables returned by the
    SHOW GLOBAL STATUS command. Supports finding delta values between invocations of this script to
    get changes per second.
    """
    VERSION = '0.1'
    SERVICE = 'MySQL'
    AUTHOR = 'Ally B'

    class Defaults(object):
        timeout = 3
        hostname = 'localhost'
        port = 3306
        delta_file_path = '/var/nagios/check_mysql_stats_plugin_delta'
        delta_precision = 2

    def parse_args(self, opts):
        """
        Parse given options and arguments
        """
        parser = self._default_parser(description=self.__doc__, version=self.VERSION, author=self.AUTHOR,
            hostname=self.Defaults.hostname, port=self.Defaults.port, delta_file_path=self.Defaults.delta_file_path,
            delta_precision=self.Defaults.delta_precision, timeout=self.Defaults.timeout)

        parser.add_argument('-u', '--username', nargs='?', help="User name to connect with.", required=True)
        parser.add_argument('--password', nargs='?', help="Password to connect with.", required=True)
        parser.add_argument('-s', '--statistic', help="""The statistic to check. One of the variable names
        returned by the SHOW GLOBAL STATUS mysql command.""", nargs='?', required=True)

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
                if self.args.verbose:
                    print "Connecting to database with details: ", self.args
                self.statistic_retriever = MySQLStatistic(self.args.hostname, self.args.port, self.args.username,
                    self.args.password, self.args.timeout)
            except Exception, error:
                raise NagiosPluginError("Error: %s" % (error))

        return self.statistic_retriever.get_statistic(statistic, self.args.verbose)

    def _get_delta(self, statistic, current_value):
        "Returns the delta for a statistic"
        previous_value = self._get_value_from_last_invocation(statistic)
        delta_value = 0

        # calculate delta, catching division by zero errors
        try:
            delta = NumberUtils.string_to_number(current_value) - NumberUtils.string_to_number(previous_value['value'])
            delta_time = round(time.time() - previous_value['time'])
            delta_value = round(delta / delta_time, self.args.delta_precision)
        except (KeyError, ZeroDivisionError):
            pass

        self.statistic_collection[statistic] = current_value

        try:
            self.statistic_collection.persist()
        except IOError, error:
            raise NagiosPluginError("%s.\nProbably means we were unable to write to file %s" % (str(error), self.args.delta_file))

        return delta_value

    def check(self):
        "Retrieves the required statistic value from the server, and finds out which status it corresponds to."
        self.statistic = self.args.statistic
        self.statistic_value = self._get_statistic(self.statistic)

        if hasattr(self.args, 'delta_time'):
            self.statistic_value = self._get_delta(self.statistic, self.statistic_value)
            self.statistic += '_per_second'

        self.status = self._calculate_status(self.statistic_value)


class MySQLStatistic(object):
    "Returns statistics from a memcache server"
    def __init__(self, host, port, username, password, timeout):
        self.mysql = MySQLdb.Connect(host=host, port=port, user=username, passwd=password,
            connect_timeout=timeout)

    def get_statistic(self, statistic, verbose=False):
        """
        Returns a statistic value.

        @param statistic The name of the statistic to retrieve
        @param vebose Whether to display verbose output
        """
        if not re.match("^[a-z_A-Z]+$", statistic):
            raise InvalidStatisticError("%s is not a valid statistic name." % statistic)

        sql = "SHOW GLOBAL STATUS LIKE '%s'" % statistic

        if verbose:
            print "Executing SQL statement: %s" % sql

        cursor = self.mysql.cursor()
        cursor.execute(sql)

        stats = cursor.fetchone()

        if not stats:
            raise UnexpectedResponseError("""Nothing returned for statistic '%s'. Run SHOW GLOBAL STATUS to make sure it's a
valid statistic name.""" % statistic)
        elif len(stats) != 2:
            raise UnexpectedResponseError("Expected 2 responses from the server, received %d" % len(stats))

        if verbose:
            print "Received: ", stats

        return stats[1]


if __name__ == '__main__':
    try:
        checker = MySQLStats(sys.argv[1:])
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