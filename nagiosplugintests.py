"Unit tests for nagiosplugin"

import unittest
from nagiosplugin import *

class ThresholdParserTests(unittest.TestCase):
    "Tests for the ThresholdParser class"

    # thresholds that should validate
    validThresholds = (
        '10',
        '10:',
        '@10:',
        '~:10',
        '10:20',
        '@10:20',
        '@~:10'
    )

    # thresholds that shouldn't validate
    invalidThresholds = (
        ':10',
        'ab:cd',
        '10:@'
    )

    # start and end point values of the ranges specified in 'validThresholds'
    validParseThresholdValues = (
        [0, 10, False],
        [10, Maths.INFINITY, False],
        [10, Maths.INFINITY, True],
        [Maths.NEGATIVE_INFINITY, 10, False],
        [10, 20, False],
        [10, 20, True],
        [Maths.NEGATIVE_INFINITY, 10, True]
    )

    # thresholds that should validate but whose high values are lower than their low values
    # and should therefore fail to parse
    invalidParseThresholds = (
        '10:0',
        '20:10',
        '0:-20'
    )

    # values that should match the given ranges
    matchingRangeValues = [
        {'start': 0, 'end': 10, 'invert': False, 'values': [-9999, -10, -1, 11, 20, 9999]},
        {'start': 10, 'end': Maths.INFINITY, 'invert': False, 'values': [-10, 0, 9]},
        {'start': 10, 'end': Maths.INFINITY, 'invert': True, 'values': [10, 500, 9999]},
        {'start': Maths.NEGATIVE_INFINITY, 'end': 10, 'invert': False, 'values': [11, 20, 100]},
        {'start': 10, 'end': 20, 'invert': False, 'values': [-8, -3, 0, 4, 9, 21, 40]},
        {'start': 10, 'end': 20, 'invert': True, 'values': [10, 14, 18, 20]},
        {'start': Maths.NEGATIVE_INFINITY, 'end': 10, 'invert': True, 'values': [-9999, -23, -2, 0, 8, 10]}
    ]

    # values that should not match the given ranges
    nonMatchingRangeValues = [
        {'start': 0, 'end': 10, 'invert': False, 'values': [0, 8, 10]},
        {'start': 10, 'end': Maths.INFINITY, 'invert': False, 'values': [10, 200, 9999]},
        {'start': 10, 'end': Maths.INFINITY, 'invert': True, 'values': [-9999, -8, 0, 9]},
        {'start': Maths.NEGATIVE_INFINITY, 'end': 10, 'invert': False, 'values': [-999, -2, 0, 9, 10]},
        {'start': 10, 'end': 20, 'invert': False, 'values': [10, 14, 18, 20]},
        {'start': 10, 'end': 20, 'invert': True, 'values': [-9, -3, 0, 9, 21, 999]},
        {'start': Maths.NEGATIVE_INFINITY, 'end': 10, 'invert': True, 'values': [11, 22, 9999]}
    ]

    def testValidThresholdsForValidity(self):
        "Validate method should return True for valid values"
        for threshold in self.validThresholds:
            try:
                self.assertTrue(ThresholdParser.validate(threshold))
            except AssertionError, error:
                raise AssertionError(str(error) + ' for value: ' + threshold)

    def testInvalidThresholdsForValidity(self):
        "Validate method should raise a ThresholdValidatorError for invalid values"
        for threshold in self.invalidThresholds:
            try:
                # we need a lamda here or else the Error gets thrown while assertRaises is being
                # evaluated, and therefore before assertRaises can catch the Error. The lambda allows
                # the code to be passed as a function which can then be executed in its own right.
                self.assertRaises(ThresholdValidatorError, lambda: ThresholdParser.validate(threshold))
            except AssertionError, error:
                raise AssertionError(str(error) + ' for value: ' + threshold)

    def testParseValidThresholds(self):
        "Parses valid thresholds to make sure the correct values are returned"
        i = 0
        for threshold in self.validThresholds:
            try:
                (start, end, invert_range) = ThresholdParser.parse(threshold)
                self.assertEquals(self.validParseThresholdValues[i][0], start)
                self.assertEquals(self.validParseThresholdValues[i][1], end)
                self.assertEquals(self.validParseThresholdValues[i][2], invert_range)
            except AssertionError, error:
                raise AssertionError("%s for value %s (start %s, end %s, invert_range %s)" % (str(error), threshold,
                    start, end, invert_range))

            i += 1
    
    def testParseInvalidThresholds(self):
        "Parse method should raise a ThresholdValidatorError if the high value is lower than the low value"
        for threshold in self.invalidParseThresholds:
            try:
                self.assertRaises(ThresholdValidatorError, lambda: ThresholdParser.parse(threshold))
            except AssertionError, error:
                raise AssertionError(str(error) + ' for value: ' + threshold)

    def testMatchineValueMatchesRange(self):
        "value_matches_range should return True for values that are in the range"
        for parameters in self.matchingRangeValues:
            for value in parameters['values']:
                try:
                    self.assertTrue(ThresholdParser.value_matches_range(parameters['start'], parameters['end'],
                        parameters['invert'], value))
                except AssertionError, error:
                    raise AssertionError(str(error) + ' for values: ' + value)

    def testNonMatchineValueMatchesRange(self):
        "value_matches_range should return False for values that are not in the range"
        for parameters in self.nonMatchingRangeValues:
            for value in parameters['values']:
                try:
                    self.assertFalse(ThresholdParser.value_matches_range(parameters['start'], parameters['end'],
                        parameters['invert'], value))
                except AssertionError, error:
                    raise AssertionError(str(error) + ' for values: ' + value)

if __name__ == "__main__":
    unittest.main()