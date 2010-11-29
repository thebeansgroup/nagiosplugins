#!/usr/bin/env python
import argparse
import sys
from nagiosplugin import NagiosPlugin

"""
Nagios plugin for checking memcached instances. Returns detailed memcached
statistics for use by perfdata visualisation tools.

Requirements
=============

This script requires the following python modules:

  * argparse (included with python 2.7, otherwise install with 'easy_install argparse')
  * memcache (install with 'easy_install python-memcached' if easy_install is present)
"""


class MemcachedStats(NagiosPlugin):
    """
    Returns internal statistics from a Memcached instance in a format that can be used
    by Nagios and perfdata.
    """
    version = '0.1a'

    class Defaults(object):
        timeout = 3
        hostname = 'localhost'
        port = 11211

    def __init__(self, opts):
        NagiosPlugin.__init__(self)
        self.args = self.parse_args(opts)
        self.set_thresholds(self.args.warning, self.args.critical)

    def parse_args(self, opts):
        """
        Parse given options and arguments
        """
        parser = argparse.ArgumentParser(description="""A Nagios plugin to check memcached statistics. It
        monitors: bytes used, bytes written, cache hits, cache hits (%), cache misses, number of current items,
        evictions, gets, sets, total connections, total items, uptime.""")

        # standard nagios arguments
        parser.add_argument('-V', '--version', action='version', version='Version %s, Ally B' % MemcachedStats.version)
        parser.add_argument('-t', '--timeout', type=float, nargs='?', default=MemcachedStats.Defaults.timeout,
            help="""Time in seconds within which the server must return its status, otherwise an error will be returned.
            Default is %d.""" % MemcachedStats.Defaults.timeout)
        # warning and critical arguments can take ranges - see:
        # http://nagiosplug.sourceforge.net/developer-guidelines.html#THRESHOLDFORMAT
        parser.add_argument('-w', '--warning', nargs='?', help="Warning threshold/range")
        parser.add_argument('-c', '--critical', nargs='?', help="Critical threshold/range")
        parser.add_argument('-H', '--hostname', nargs='?', default=MemcachedStats.Defaults.hostname,
            help="""Hostname of the machine running memcached.
            Default is %s.""" % MemcachedStats.Defaults.hostname)
        parser.add_argument('-p', '--port', nargs='?', default=MemcachedStats.Defaults.port,
            help="""Port on which memcached is listening.
            Default is %d.""" % MemcachedStats.Defaults.port)
        return parser.parse_args(opts)

    def get_stats(self):
        pass

if __name__ == '__main__':
    checker = MemcachedStats(sys.argv[1:])
    try:
        checker.get_stats()
    except Exception, e:
        print "Error:", e
        sys.exit(3)