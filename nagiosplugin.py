import re
import cPickle as pickle
from time import time
from UserDict import IterableUserDict

class NagiosPluginError(Exception):
    "Base class for plugin errors"
    pass


class InvalidStatisticError(NagiosPluginError):
    "Indicates that the script was invoked to check a statistic that doesn't exist"
    pass


class UnexpectedResponseError(NagiosPluginError):
    "Indicates that the script received a response from the service that it didn't expect"
    pass


class ThresholdValidatorError(NagiosPluginError):
    "Thrown when a threshold fails validation"
    pass


class Maths(object):
    "Constants for infinity and negative infinity"
    INFINITY = 'infinity'
    NEGATIVE_INFINITY = 'negative_infinity'


class ThresholdParser(object):
    "Utility class for validating and parsing nagios threshold strings"

    @staticmethod
    def validate(string):
        "Validates a threshold string"
        if re.match(r"^@?((\d+|~):?)?(\d+)?$", string):
            return True
        else:
            raise ThresholdValidatorError("'%s' is not a valid threshold value." % string)

    @staticmethod
    def parse(range):
        """
        Parses a threshold to find the start and end points of the range.
        
        returns a tuple (start, end, alert_inside_range). Values may be integers or 'Maths' constants. Tuple
        values are:

        start - start of the range
        end - end of the range
        alert_inside_range - if True a value should match if: start <= value <= end. If False, a value should
                match if value < start or end < value.
        """
        start = 0

        # strip the leading '@' if it's present
        if range.startswith('@'):
            invert_range = True
            range = range.lstrip('@')
        else:
            invert_range = False

        # if the string contains a :, split it into low and high values
        if ':' in range:
            values = range.split(':')

            if values[0] == '~':
                start = Maths.NEGATIVE_INFINITY
            else:
                start = int(values[0])

            if values[1] == '':
                end = Maths.INFINITY
            else:
                end = int(values[1])

            # if the high is lower than the low, raise an error
            if end != Maths.INFINITY and start != Maths.NEGATIVE_INFINITY and end < start:
                raise ThresholdValidatorError("%s must be <= %s in range %s" % (values[0], values[1], range))

        else:
            end = int(range)

        return (start, end, invert_range)

    @staticmethod
    def value_matches_range(start, end, alert_inside_range, value):
        """
        Returns a boolean indicating whether the supplied value should trigger an alert.
        
        alert_inside_range - if True a value should match if start <= value <= end. 
            If False, a value should match if value < start or end < value.
        """
        if alert_inside_range:
            # if start == Maths.NEGATIVE_INFINITY, 'value' will always be greater than it.
            if start == Maths.NEGATIVE_INFINITY or start <= value:
                # if end == Maths.INFINITY, value will always be less than it
                if value <= end or end == Maths.INFINITY:
                    return True
        else:
            if (start != Maths.NEGATIVE_INFINITY and value < start) or (end != Maths.INFINITY and value > end):
                return True

        return False



class Thresholds(object):
    """
    Encapsulates nagios threshold values. Values are validated to make sure
    they match http://nagiosplug.sourceforge.net/developer-guidelines.html#THRESHOLDFORMAT

    Given a value, a status can be returned.
    """
    def __init__(self, warning, critical):
        self.warning = warning
        self.critical = critical

        # validate thresholds to make sure the given values are acceptable
        self._validate_thresholds()

    def _validate_thresholds(self):
        "Validates that the given thresholds are OK"
        # first, validate both threshold strings
        if self.warning != None:
            ThresholdParser.validate(self.warning)
            self.warning_values = ThresholdParser.parse(self.warning)

        if self.critical != None:
            ThresholdParser.validate(self.critical)
            self.critical_values = ThresholdParser.parse(self.critical)

    def value_is_critical(self, value):
        "Returns a boolean indicating whether the given value lies inside the configured critical range"
        try:
            return ThresholdParser.value_matches_range(self.critical_values[0], self.critical_values[1], self.critical_values[2], value)
        except AttributeError:
            return False

    def value_is_warning(self, value):
        "Returns a boolean indicating whether the given value lies inside the configured warning range"
        try:
            return ThresholdParser.value_matches_range(self.warning_values[0], self.warning_values[1], self.warning_values[2], value)
        except AttributeError:
            return False


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


class NumberUtils(object):
    "Utility methods for working with numbers"
    @staticmethod
    def string_to_number(string):
        "Converts a numeric string to a number"
        try:
            return int(string)
        except ValueError:
            return float(string)
        except TypeError:
            return 0


class NagiosPlugin(object):
    """
    Base class for Nagios plugins providing reusable methods such as
    comparing a given value to specified warning and critical thresholds/ranges.
    """

    ## Status codes for Nagios
    STATUS_OK = 0
    STATUS_WARNING = 1
    STATUS_CRITICAL = 2
    STATUS_UNKNOWN = 3

    ## Strings that correspond to the above status codes 
    STATUS_CODE_STRINGS = ['OK', 'WARNING', 'CRITICAL', 'UNKNOWN']

    def __init__(self, opts):
        self.status = self.STATUS_UNKNOWN
        self.args = self.parse_args(opts)
        self.set_thresholds(self.args.warning, self.args.critical)
        self.statistic_collection = TimestampedStatisticCollection(self.args.delta_file)

    def set_thresholds(self, warning, critical):
        "Sets the warning and critical thresholds"
        self.thresholds = Thresholds(warning, critical)

    def get_status(self):
        "Returns the nagios status code for the latest check."
        return self.status

    def _calculate_status(self, value):
        "Returns the status of the service by comparing the given value to the thresholds"
        if self.thresholds.value_is_critical(value):
            return self.STATUS_CRITICAL
        
        if self.thresholds.value_is_warning(value):
            return self.STATUS_WARNING

        return self.STATUS_OK

    def _get_statistic(self):
        "Returns a statistic in perfdata format"
        pass
    
    def _format_perfdata(self, statistic, value):
        "Returns data in perfdata format"
        return "'%s'=%s" % (statistic, value)

    def _get_value_from_last_invocation(self, statistic):
        "Returns the value the desired statistic had on the previous invocation of this script."
        value = {}

        if statistic in self.statistic_collection:
            value = self.statistic_collection[statistic]

        return value

    def get_output(self):
        """
        Returns an output string for nagios. Prior to calling this method, self.statistic and
        self.statistic_value should have been set (probably in the 'check' method).
        """
        statistic = self._format_perfdata(self.statistic, self.statistic_value)
        output_statistic = statistic.replace("'", '')
            
        return "%s %s - %s | %s" % (self.SERVICE, self.STATUS_CODE_STRINGS[self.status], output_statistic, statistic)