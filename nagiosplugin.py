import re

class ThresholdParserError(Exception):
    pass


class ThresholdValidatorError(ThresholdParserError):
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
            raise ThresholdValidatorError("'%s' is not a valid threshold value" % string)

    @staticmethod
    def parse(range):
        """
        Parses a threshold to find the start and end points of the range.
        
        returns a tuple (start, end) of the range. Values may be integers or 'Maths' constants.
        """
        start = 0

        # strip the leading '@' if it's present
        if range.startswith('@'):
            range = range.lstrip('@')

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

        return (start, end)

    def invert_range(self, threshold):
        """
        Returns whether we should alert if the value is between start and end points
        (inclusive). If False, we will alert if the value is outside the range (excluding
        end points).
        """
        if threshold.startswith('@'):
            return True;
        else:
            return False;

    def get_status(self, value):
        "Returns the status code for the configured thresholds and the supplied value."
        pass


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


class NagiosPlugin(object):
    """
    Base class for Nagios plugins providing reusable methods such as
    comparing a given value to specified warning and critical thresholds/ranges.
    """

    ## Status codes for Nagios
    STATUS_OK = 0
    STATUS_WARNING = 1
    STATUS_ERROR = 2
    STATUS_UNKNOWN = 3

    def set_thresholds(self, warning, critical):
        "Sets the warning and critical thresholds"
        self.thresholds = Thresholds(warning, critical)

    def get_status(self, value):
        "Returns the status of the service by comparing the given value to the thresholds"
        pass