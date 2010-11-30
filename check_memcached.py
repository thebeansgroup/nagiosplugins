#!/usr/bin/env python
import argparse
import sys
import memcache
import cPickle as pickle
from UserDict import IterableUserDict
from time import time
from nagiosplugin import *

"""
Nagios plugin for checking memcached instances. Returns detailed memcached
statistics for use by perfdata visualisation tools.

Requirements
=============

This script requires the following python modules:

  * argparse (included with python 2.7, otherwise install with 'easy_install argparse')
  * memcache (install with 'easy_install python-memcached' if easy_install is present)

Notes
=====

It's useful to monitor the following statistics:

  * uptime
  * curr_items
  * total_items
  * bytes
  * cmd_get
  * get_hits - percentage of time delta
  * total_connections - delta'd by time
  * cmd_set - delta'd by time
  * get_misses - delta'd by time
  * evictions - delta'd by time
  * bytes_written - delta'd by time
"""

class InvalidStatisticError(NagiosPluginError):
    "Indicates that the script was invoked to check a statistic that doesn't exist"
    pass


class TimestampedStatisticCollection(IterableUserDict):
    "Persistable store for a collection of time-stamped statistics"
    def __init__(self, path):
        "Path is the path to persist data to"
        IterableUserDict.__init__(self)
        self.path = path
        self.__load()

    def __load(self):
        "Loads the data from the store"
        try:
            file = open(self.path, 'r+')
            self.data = pickle.load(file)
            file.close()
        except IOError:
            pass

    def persist(self):
        """
        Persists the collection.
        
        @throws IOError if it can't write to the file
        """
        file = open(self.path, 'w+')
        pickle.dump(self.data, file)
        file.close()

    def __setitem__(self, key, value):
        "Creates a tuple consisting of the current time stamp and the value and stores that tuple under the key."
        data = {"time": time(), "value": value}
        return IterableUserDict.__setitem__(self, key, data)


class MemcachedStats(NagiosPlugin):
    """
    Returns internal statistics from a Memcached instance in a format that can be used
    by Nagios and perfdata.
    """
    VERSION = '0.1'
    SERVICE = 'Memcached'
    ## a constant for a special metric we calculate ourselves
    CACHE_HITS_PERCENTAGE = 'cache_hits_percentage'

    class Defaults(object):
        timeout = 3
        hostname = 'localhost'
        port = 11211
        delta_file_path = '/var/nagios/check_memcached_plugin_delta'

    def __init__(self, opts):
        NagiosPlugin.__init__(self)
        self.args = self.parse_args(opts)
        self.set_thresholds(self.args.warning, self.args.critical)
        self.memcache = memcache.Client(['%s:%d' % (self.args.hostname, self.args.port)])

        if hasattr(self.args, 'delta_time'):
            self.statistic_collection = TimestampedStatisticCollection(self.args.delta_file)

    def parse_args(self, opts):
        """
        Parse given options and arguments
        """
        parser = argparse.ArgumentParser(description="""A Nagios plugin to check memcached statistics. It
        monitors: bytes used, bytes written, cache hits, cache hits (%), cache misses, number of current items,
        evictions, gets, sets, total connections, total items, uptime.""")

        # standard nagios arguments
        parser.add_argument('-V', '--version', action='version', version='Version %s, Ally B' % MemcachedStats.VERSION)
        parser.add_argument('-t', '--timeout', type=float, nargs='?', default=MemcachedStats.Defaults.timeout,
            help="""Time in seconds within which the server must return its status, otherwise an error will be returned.
            Default is %d.""" % MemcachedStats.Defaults.timeout)
        # warning and critical arguments can take ranges - see:
        # http://nagiosplug.sourceforge.net/developer-guidelines.html#THRESHOLDFORMAT
        parser.add_argument('-v', '--verbose', default=argparse.SUPPRESS, nargs='?', help="Whether to display verbose output")
        parser.add_argument('-w', '--warning', nargs='?', help="Warning threshold/range")
        parser.add_argument('-c', '--critical', nargs='?', help="Critical threshold/range")
        parser.add_argument('-H', '--hostname', nargs='?', default=MemcachedStats.Defaults.hostname,
            help="""Hostname of the machine running memcached.
            Default is %s.""" % MemcachedStats.Defaults.hostname)
        parser.add_argument('-p', '--port', nargs='?', default=MemcachedStats.Defaults.port, type=int,
            help="""Port on which memcached is listening. Default is %d.""" % MemcachedStats.Defaults.port)
        parser.add_argument('--delta-file', nargs='?', default=MemcachedStats.Defaults.delta_file_path,
            help="""Path to store statistics between invocations for calculating deltas.
            Default is: %s""" % MemcachedStats.Defaults.delta_file_path)
        parser.add_argument('-d', '--delta-time', default=argparse.SUPPRESS, nargs='?',
            help="""Whether to report changes in values between invocations divided by the time since the
            last invocation.""")
        parser.add_argument('-s', '--statistic', help="""The statistic to check. Use one of the following
        keywords:
            accepting_conns
            auth_cmds
            auth_errors
            bytes
            bytes_read
            bytes_written
            cas_badval
            cas_hits
            cas_misses
            cmd_flush
            cmd_get
            cmd_set
            conn_yields
            connection_structures
            curr_connections
            curr_items
            decr_hits
            decr_misses
            delete_hits
            delete_misses
            evictions
            get_hits
            get_misses
            incr_hits
            incr_misses
            limit_maxbytes
            listen_disabled_num
            pid
            pointer_size
            rusage_system
            rusage_user
            threads
            time
            total_connections
            total_items
            uptime
            version,
            
        or the special value:
            cache_hits_percentage
        """)
        return parser.parse_args(opts)

    def _get_value_from_last_invocation(self):
        "Returns the value the desired statistic had on the previous invocation of this script."
        value = {}
        
        if self.args.statistic in self.statistic_collection:
            value = self.statistic_collection[self.args.statistic]

        return value

    def _get_statistic(self):
        "Returns a tuple containing the name of a statistic and its value ."
        server_stats = self.memcache.get_stats()

        # if no stats were returned, return False
        try:
            stats = server_stats[0][1]
        except IndexError:
            if 'verbose' in self.args:
                print "Unable to connect to memcache server. Check the host and port and make sure \nmemcached is running."
            raise NagiosPluginError("Unable to connect to memcache server. Check the host and port and make sure \nmemcached is running.")

        if self.args.statistic in stats.keys():
            return (self.args.statistic, stats[self.args.statistic])
        else:
            raise InvalidStatisticError("No statistic called '%s' was returned by the memcache server." % self.args.statistic)

    def _string_to_number(self, string):
        "Converts a numeric string to a number"
        try:
            return int(string)
        except ValueError:
            return float(string)

    def check(self):
        "Retrieves the required statistic value from memcache, and finds out which status it corresponds to."
        (self.statistic, self.statistic_value) = self._get_statistic()

        if hasattr(self.args, 'delta_time'):
            old_value = self._get_value_from_last_invocation()

            if 'value' in old_value:

                delta = self._string_to_number(old_value['value']) - self._string_to_number(self.statistic_value)
                delta_time = time() - old_value['time']
                self.statistic_collection[self.statistic] = self.statistic_value
                self.statistic_value = delta / delta_time
            else:
                self.statistic_collection[self.statistic] = self.statistic_value

            try:
                self.statistic_collection.persist()
            except IOError, error:
                raise NagiosPluginError("%s.\nProbably means we were unable to write to file %s" % (str(error), self.args.delta_file))
        
        self.status = self._calculate_status(self.statistic_value)


if __name__ == '__main__':
    try:
        checker = MemcachedStats(sys.argv[1:])
        checker.check()
        status = checker.get_status()
        data = checker.get_output()
        print data
        sys.exit(status)
    except (ThresholdValidatorError, InvalidStatisticError), e:
        print e
        sys.exit(NagiosPlugin.STATUS_UNKNOWN)
    except NagiosPluginError, e:
        print "%s failed unexpectedly. Error was:\n%s" % (__file__, str(e))
        sys.exit(NagiosPlugin.STATUS_UNKNOWN)