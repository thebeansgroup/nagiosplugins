#!/usr/bin/env python
import sys
import memcache
import textwrap
import os.path
import time
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
  * cmd_get - delta'd by time
  * get_hits - percentage of time delta
  * total_connections - delta'd by time
  * cmd_set - delta'd by time
  * get_misses - delta'd by time
  * evictions - delta'd by time
  * bytes_written - delta'd by time
"""


class MemcachedStats(NagiosPlugin):
    """
    A Nagios plugin to check memcached statistics. Statistics are returned in perfdata formate.
    The following can be monitored: bytes used, bytes written, cache hits,
    cache hits (%), cache misses, number of current items, evictions, gets, sets, total connections,
    total items, uptime.
    """
    VERSION = '0.1'
    SERVICE = 'Memcached'
    AUTHOR = 'Ally B'
    ## a constant for a special metric we calculate ourselves
    CACHE_HITS_PERCENTAGE = 'cache_hits_percentage'

    class Defaults(object):
        timeout = 3
        hostname = 'localhost'
        port = 11211
        delta_file_path = '/var/nagios/check_memcached_plugin_delta'
        delta_precision = 2

    def parse_args(self, opts):
        """
        Parse given options and arguments
        """
        parser = self._default_parser(description=self.__doc__, version=self.VERSION, author=self.AUTHOR,
            hostname=self.Defaults.hostname, port=self.Defaults.port, delta_file_path=self.Defaults.delta_file_path,
            delta_precision=self.Defaults.delta_precision)

        parser.add_argument('-s', '--statistic', nargs='?', required=True,
            help="""The statistic to check. Use one of the following keywords:
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
        
        args = parser.parse_args(opts)
        if 'verbose' not in args:
            args.verbose = False
        else:
            args.verbose = True

        return args

    def _get_statistic(self, statistic):
        "Returns a tuple containing the name of the specified statistic and its value."
        if not hasattr(self, 'memcache_statistic'):
            self.memcache_statistic = MemcacheStatistic(self.args.hostname, self.args.port)

        # calculate the cache hits percentage special statistic
        if statistic == self.CACHE_HITS_PERCENTAGE:
            get_hits = self._get_statistic('get_hits')
            cmd_get = self._get_statistic('cmd_get')
            # use separate values for get_hits and cmd_get compared to ordinary invocations to check those
            # statistics
            delta_cache_hits = NumberUtils.string_to_number(self._get_delta('get_hits_hit_cache_perc', get_hits))
            delta_gets = NumberUtils.string_to_number(self._get_delta('cmd_get_hit_cache_perc', cmd_get))

            try:
                cache_hits_percentage = round(delta_cache_hits * 100 / delta_gets, 2)
            except ZeroDivisionError:
                cache_hits_percentage = 0

            if self.args.verbose:
                print "cache hits: %s, gets: %s" % (get_hits, cmd_get)
                print "delta_cache_hits: %s, delta_gets: %s" % (delta_cache_hits, delta_gets)
                print "cache hits %%: %s" % (cache_hits_percentage)

            return cache_hits_percentage
        else:
            return self.memcache_statistic.get_statistic(statistic, self.args.verbose)

    def _get_delta(self, statistic, current_value):
        "Returns the delta for a statistic"
        previous_value = self._get_value_from_last_invocation(statistic)
        delta_value = 0

        # if we're trying to get the delta of the cache_hits_percentage, just divide by delta time since
        # it's already derived from delta values

        try:
            if statistic == self.CACHE_HITS_PERCENTAGE:
                delta = current_value
            else:
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
        "Retrieves the required statistic value from memcache, and finds out which status it corresponds to."
        self.statistic = self.args.statistic
        self.statistic_value = self._get_statistic(self.statistic)

        if hasattr(self.args, 'delta_time'):
            self.statistic_value = self._get_delta(self.statistic, self.statistic_value)
            self.statistic += '_per_second'
        
        self.status = self._calculate_status(self.statistic_value)


class MemcacheStatistic(object):
    "Returns statistics from a memcache server"
    def __init__(self, server, port):
        self.memcache = memcache.Client(['%s:%d' % (server, port)])

    def get_statistic(self, statistic, verbose=False):
        """
        Returns a statistic value.

        @param statistic The name of the statistic to retrieve
        @param vebose Whether to display verbose output
        """
        server_stats = self.memcache.get_stats()

        # if no stats were returned, raise an Error
        try:
            stats = server_stats[0][1]
        except IndexError:
            if verbose:
                print "Unable to connect to memcache server. Check the host and port and make sure \nmemcached is running."
            raise NagiosPluginError("Unable to connect to memcache server. Check the host and port and make sure \nmemcached is running.")

        if statistic in stats.keys():
            return stats[statistic]
        else:
            raise InvalidStatisticError("No statistic called '%s' was returned by the memcache server." % statistic)



if __name__ == '__main__':
    try:
        checker = MemcachedStats(sys.argv[1:])
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