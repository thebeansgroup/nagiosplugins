"Unit tests for nagiosplugin"

import unittest
from nagiosplugin import *

class ThresholdParserTests(unittest.TestCase):
    "Tests for the ThresholdParser class"

    # thresholds that should validate
    validThresholds = (
        '10',
        '10:',
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
        [0, 10],
        [10, Maths.INFINITY],
        [Maths.NEGATIVE_INFINITY, 10],
        [10, 20],
        [10, 20],
        [Maths.NEGATIVE_INFINITY, 10]
    )

    # thresholds that should validate but whose high values are lower than their low values
    # and should therefore fail to parse
    invalidParseThresholds = (
        '10:0',
        '20:10',
        '0:-20'
    )

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
                (start, end) = ThresholdParser.parse(threshold)
                self.assertEquals(self.validParseThresholdValues[i][0], start)
                self.assertEquals(self.validParseThresholdValues[i][1], end)
            except AssertionError, error:
                raise AssertionError("%s for value %s (start %s, end %s)" % (str(error), threshold, start, end))

            i += 1
    
    def testParseInvalidThresholds(self):
        "Parse method should raise a ThresholdValidatorError if the high value is lower than the low value"
        for threshold in self.invalidParseThresholds:
            try:
                self.assertRaises(ThresholdValidatorError, lambda: ThresholdParser.parse(threshold))
            except AssertionError, error:
                raise AssertionError(str(error) + ' for value: ' + threshold)


if __name__ == "__main__":
    unittest.main()