#!/bin/env python
"Unit tests for nagiosplugin"

import time
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

    def testValidThresholdsForValidity(self):
        "Validate method returns True for valid values"
        for threshold in self.validThresholds:
            try:
                self.assertTrue(ThresholdParser.validate(threshold))
            except AssertionError, error:
                raise AssertionError(str(error) + ' for value: ' + threshold)

    def testInvalidThresholdsForValidity(self):
        "Validate method raises a ThresholdValidatorError for invalid values"
        # thresholds that shouldn't validate
        invalidThresholds = (
            ':10',
            'ab:cd',
            '10:@'
        )

        for threshold in invalidThresholds:
            try:
                # we need a lamda here or else the Error gets thrown while assertRaises is being
                # evaluated, and therefore before assertRaises can catch the Error. The lambda allows
                # the code to be passed as a function which can then be executed in its own right.
                self.assertRaises(ThresholdValidatorError, lambda: ThresholdParser.validate(threshold))
            except AssertionError, error:
                raise AssertionError(str(error) + ' for value: ' + threshold)

    def testParseValidThresholds(self):
        "Parses valid thresholds to make sure the correct values are returned"
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

        i = 0
        for threshold in self.validThresholds:
            try:
                (start, end, invert_range) = ThresholdParser.parse(threshold)
                self.assertEquals(validParseThresholdValues[i][0], start)
                self.assertEquals(validParseThresholdValues[i][1], end)
                self.assertEquals(validParseThresholdValues[i][2], invert_range)
            except AssertionError, error:
                raise AssertionError("%s for value %s (start %s, end %s, invert_range %s)" % (str(error), threshold,
                    start, end, invert_range))

            i += 1
    
    def testParseInvalidThresholds(self):
        "Parse method raises a ThresholdValidatorError if the high value is lower than the low value"
        # thresholds that should validate but whose high values are lower than their low values
        # and should therefore fail to parse
        invalidParseThresholds = (
            '10:0',
            '20:10',
            '0:-20'
        )

        for threshold in invalidParseThresholds:
            try:
                self.assertRaises(ThresholdValidatorError, lambda: ThresholdParser.parse(threshold))
            except AssertionError, error:
                raise AssertionError(str(error) + ' for value: ' + threshold)

    def testMatchineValueMatchesRange(self):
        "value_matches_range returns True for values that are in the range"
        # values that should match the given ranges
        matchingRangeValues = [
            {'start': 0, 'end': 10, 'invert': False, 'values': [-9999, -10, -1, 11, 20, 9999]},
            {'start': 10, 'end': Maths.INFINITY, 'invert': False, 'values': [-10, 0, 9]},
            {'start': 10, 'end': Maths.INFINITY, 'invert': True, 'values': [10, 500, 9999]},
            {'start': Maths.NEGATIVE_INFINITY, 'end': 10, 'invert': False, 'values': [11, 20, 100]},
            {'start': 10, 'end': 20, 'invert': False, 'values': [-8, -3, 0, 4, 9, 21, 40]},
            {'start': 10, 'end': 20, 'invert': True, 'values': [10, 14, 18, 20]},
            {'start': Maths.NEGATIVE_INFINITY, 'end': 10, 'invert': True, 'values': [-9999, -23, -2, 0, 8, 10]},
        ]

        for parameters in matchingRangeValues:
            for value in parameters['values']:
                try:
                    self.assertTrue(ThresholdParser.value_matches_range(parameters['start'], parameters['end'],
                        parameters['invert'], value))
                except AssertionError, error:
                    raise AssertionError(str(error) + ' for values: ' + str(value))

    def testNonMatchineValueMatchesRange(self):
        "value_matches_range returns False for values that are not in the range"
        # values that should not match the given ranges
        nonMatchingRangeValues = [
            {'start': 0, 'end': 10, 'invert': False, 'values': [0, 8, 10]},
            {'start': 10, 'end': Maths.INFINITY, 'invert': False, 'values': [10, 200, 9999]},
            {'start': 10, 'end': Maths.INFINITY, 'invert': True, 'values': [-9999, -8, 0, 9]},
            {'start': Maths.NEGATIVE_INFINITY, 'end': 10, 'invert': False, 'values': [-999, -2, 0, 9, 10]},
            {'start': 10, 'end': 20, 'invert': False, 'values': [10, 14, 18, 20]},
            {'start': 10, 'end': 20, 'invert': True, 'values': [-9, -3, 0, 9, 21, 999]},
            {'start': Maths.NEGATIVE_INFINITY, 'end': 10, 'invert': True, 'values': [11, 22, 9999]},
            {'start': 0, 'end': 80002000, 'invert': False, 'values': ['4449364']},
        ]

        for parameters in nonMatchingRangeValues:
            for value in parameters['values']:
                try:
                    self.assertFalse(ThresholdParser.value_matches_range(parameters['start'], parameters['end'],
                        parameters['invert'], value))
                except AssertionError, error:
                    raise AssertionError(str(error) + ' for values: ' + str(value))
                
    def testCompleteTimePeriods(self):
        "time_periods_cover_24_hours returns True for valid time periods that cover an entire day."
        # time period definitions that cover 24 hours
        completeTimePeriods = [
            '00:00-08:00,08:00-16:00,16:00-24:00',
            '24:00-12:00,12:00-00:00',
            '00:00-24:00',
            '00:00-23:59',
            '24:00-00:00'
        ]

        for complete_time_period in completeTimePeriods:
            time_period_list = complete_time_period.split(',')
            try:
                self.assertTrue(ThresholdParser.time_periods_cover_24_hours(time_period_list))
            except AssertionError, error:
                raise AssertionError(str(error) + ' for time periods: ' + str(time_period_list))

    def testIncompleteTimePeriods(self):
        "time_periods_cover_24_hours returns False for valid time periods that don't cover an entire day."
        # time period definitions that don't cover 24 hours
        incompleteTimePeriods = [
            '00:00-08:00,08:00-16:00,16:00-23:58',
            '24:00-12:00,13:00-00:00',
            '00:00-23:00',
            '00:00-23:00,23:00-24:00,00:00-02:00',
            '00:01-00:00'
        ]

        for incomplete_time_period in incompleteTimePeriods:
            time_period_list = incomplete_time_period.split(',')
            try:
                self.assertFalse(ThresholdParser.time_periods_cover_24_hours(time_period_list))
            except AssertionError, error:
                raise AssertionError(str(error) + ' for time periods: ' + str(time_period_list))

    def testInvalidTimePeriods(self):
        "time_periods_cover_24_hours raises a ThresholdTimePeriodError when invalid periods are given."
        # invalid time period definitions
        invalidTimePeriods = [
            '10:00-08:00',
            '12:00-10:00,13:00-00:00',
            '23:00-12:00,12:00-23:00'
        ]

        for invalid_time_period in invalidTimePeriods:
            time_period_list = invalid_time_period.split(',')
            try:
                self.assertRaises(ThresholdTimePeriodError,
                    lambda: ThresholdParser.time_periods_cover_24_hours(time_period_list))
            except AssertionError, error:
                raise AssertionError(str(error) + ' for value: ' + time_period_list)

    def testGetThresholdsForTime(self):
        "get_thresholds_for_time returns the correct warning and critical values for a given time."
        # warning and critical thresholds, critical thresholds along with time periods and the current time. We'll
        # test to make sure the correct warning and critical values are returned.
        #
        # Time values are formatted '%Y:%H:%M'. The year must be > 1970
        thresholdsForTimes = [
            {'warning': '10,20,30', 'critical': '50,60,70', 'time_periods': '00:00-08:00,08:00-16:00,16:00-24:00',
                'time': '2010:07:56', 'expected_warning': '10', 'expected_critical': '50'},
            {'warning': '10,20,30', 'critical': '50,60,70', 'time_periods': '00:00-08:00,08:00-16:00,16:00-24:00',
                'time': '2010:11:32', 'expected_warning': '20', 'expected_critical': '60'},
            {'warning': '10,20,30', 'critical': '50,60,70', 'time_periods': '00:00-08:00,08:00-16:00,16:00-24:00',
                'time': '2010:18:32', 'expected_warning': '30', 'expected_critical': '70'},
        ]

        for values in thresholdsForTimes:
            timestamp = time.mktime(time.strptime(values['time'], "%Y:%H:%M"))
            try:
                (warning, critical) = ThresholdParser.get_thresholds_for_time(warning=values['warning'], critical=values['critical'],
                    time_periods=values['time_periods'], timestamp=timestamp)
                self.assertEquals(warning, values['expected_warning'])
                self.assertEquals(critical, values['expected_critical'])
            except AssertionError, error:
                raise AssertionError(str(error) + ' for values: ' + str(values))

    def testGetThresholdsForTime(self):
        "get_thresholds_for_time returns the correct warning and critical values for a given time."
        # Invalid parameter combinations for get_thresholds_for_time
        invalidParametersForGetThresholdsForTime = [
            {'warning': '10,20,30', 'critical': '50,60', 'time_periods': '00:00-08:00,08:00-16:00,16:00-24:00',
                'time': '2010:07:56', 'expected_warning': '10', 'expected_critical': '50'},
            {'warning': '10,20,30', 'critical': '50,60,70', 'time_periods': '08:00-16:00,16:00-24:00',
                'time': '2010:11:32', 'expected_warning': '20', 'expected_critical': '60'},
            {'warning': '20,30', 'critical': '50,60,70', 'time_periods': '00:00-08:00,08:00-16:00,16:00-24:00',
                'time': '2010:18:32', 'expected_warning': '30', 'expected_critical': '70'},
        ]

        for values in invalidParametersForGetThresholdsForTime:
            timestamp = time.mktime(time.strptime(values['time'], "%Y:%H:%M"))
            try:
                self.assertRaises(ThresholdTimePeriodError,
                    lambda: ThresholdParser.get_thresholds_for_time(warning=values['warning'], critical=values['critical'],
                    time_periods=values['time_periods'], timestamp=timestamp))
            except AssertionError, error:
                raise AssertionError(str(error) + ' for values: ' + str(values))

    def testGetTimePeriodIndex(self):
        "get_time_period_index returns the correct index"
        time_periods = [
            { 'time_periods': ['00:00-08:00', '08:00-16:00', '16:00-24:00'], 'timestamp': 10, 'expected_index': 0 },
            { 'time_periods': ['00:00-08:00', '08:00-16:00', '16:00-24:00'], 'timestamp': 29000, 'expected_index': 1 },
            { 'time_periods': ['00:00-08:00', '08:00-16:00', '16:00-24:00'], 'timestamp': 60000, 'expected_index': 2 },
        ]
        for values in time_periods:
            try:
                self.assertEquals(ThresholdParser.get_time_period_index(values['time_periods'], values['timestamp']),
                    values['expected_index'])
            except AssertionError, error:
                raise AssertionError(str(error) + ' for values: ' + str(values))

if __name__ == "__main__":
    unittest.main()