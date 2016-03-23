#!/usr/bin/python
# -*- coding: iso-8859-15 -*-

# Copyright (c) 2014 The New York Times Company
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

""" Test module for utilitys"""

import logging
import sys
import unittest

from collectd_rabbitmq import utils


class TestFilterDictionary(unittest.TestCase):
    """
    Test class for filter_dictionary method.
    """

    def test_filter_dictionary(self):
        """
        Asserts that dictionary is filtered properly.
        """
        test_dict = dict(one='test1',
                         two='test2',
                         three='test3')
        test_keys = ['one', 'two']
        filtered = utils.filter_dictionary(test_dict, test_keys)
        self.assertNotIn('three', filtered.keys())

    def test_filter_no_keys(self):
        """
        Asserts that dictionary is filtered properly.
        """
        test_dict = dict(one='test1',
                         two='test2',
                         three='test3')
        filtered = utils.filter_dictionary(test_dict, None)
        self.assertEquals(filtered, dict())

    def test_filter_no_dictionary(self):
        """
        Asserts that dictionary is filtered properly.
        """
        test_keys = ['one', 'two']
        filtered = utils.filter_dictionary(None, test_keys)
        self.assertEquals(filtered, dict())


class TestConnectionInfo(unittest.TestCase):
    """
    Test class for collection object.
    """

    def setUp(self):
        self.conn = utils.ConnectionInfo(host="example.com",
                                         port=15672,
                                         scheme="http")

    def test_url_setter(self):
        """
        Assert the the url is parse and stored properly.
        """
        self.conn.url = "https://test.com:2112"
        self.assertEqual(self.conn.host, "test.com")
        self.assertEqual(self.conn.port, 2112)
        self.assertEqual(self.conn.scheme, "https")


class TestConfig(unittest.TestCase):
    """
    Test class for config object.
    """

    def setUp(self):
        self.conn = utils.ConnectionInfo(host="example.com",
                                         port=15672,
                                         scheme="http")
        self.auth = utils.Auth()

    def test_config_url(self):
        """
        Assert that host and port are set from URL.
        """
        conf = utils.Config(None, self.conn)
        self.assertEquals(conf.connection.host, "example.com")
        self.assertEquals(conf.connection.scheme, "http")
        self.assertEquals(conf.connection.port, 15672)

    def test_config_ignored(self):
        """
        Asserts that ignored_data is properly ignored.
        """
        ignored_data = dict(exchange=['a.*', 'b.*'])
        conf = utils.Config(self.auth, self.conn, ignored_data)
        self.assertTrue(conf.is_ignored('exchange', 'abc'))

    def test_config_not_ignored(self):
        """
        Asserts that ignored_data is properly ignored.
        """
        ignored_data = dict(exchange=['a.*', 'b.*'])
        conf = utils.Config(self.auth, self.conn, ignored_data)
        self.assertFalse(conf.is_ignored('exchange', 'notignored'))

if __name__ == '__main__':

    logging.basicConfig(stream=sys.stderr)
    logging.getLogger().setLevel(logging.DEBUG)
    unittest.main()
