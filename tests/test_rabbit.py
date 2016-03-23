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

""" Main rabbit test module """

import json
import logging
import sys
import unittest
import urllib2

from mock import Mock, patch
from collectd_rabbitmq.rabbit import RabbitMQStats
from collectd_rabbitmq.utils import Auth, Config, ConnectionInfo
from tests.utils import create_mock_url_repsonse, MockURLResponse


class TestGetInfo(unittest.TestCase):
    """
    Test the get info method.
    """

    def setUp(self):
        self.stats = RabbitMQStats(Mock())

    @patch('collectd_rabbitmq.rabbit.urllib2.urlopen')
    def test_get_info(self, mock_urlopen):
        """
        Asserts that get_info returns the proper data from url.

        Args:
        :param mock_urlopen: A patched urllib object
        """
        url = "http://test"
        test_value = ['test', 'json']
        mock_response = MockURLResponse(json.dumps(test_value))
        mock_urlopen.return_value = mock_response
        result = self.stats.get_info(url)
        self.assertIsNotNone(result)
        self.assertEqual(test_value, result)

    def test_get_info_bad_url(self):
        """
        Asserts that get_info returns None if url is incorrect.
        """
        url = "test"
        result = self.stats.get_info(url)
        self.assertIsNone(result)

    @patch('collectd_rabbitmq.rabbit.urllib2.urlopen')
    def test_get_info_httpd_exception(self, mock_urlopen):
        """
        Asserts that get_info returns None on HTTP Error.

        Args:
        :param mock_urlopen: A patched urllib object
        """
        url = "http://test"
        mock_urlopen.side_effect = urllib2.HTTPError(url,
                                                     500,
                                                     'Internal Server Error',
                                                     None, None)
        result = self.stats.get_info(url)
        self.assertIsNone(result)

    @patch('collectd_rabbitmq.rabbit.urllib2.urlopen')
    def test_get_info_url_exception(self, mock_urlopen):
        """
        Asserts that get_info returns None on URLError.

        Args:
        :param mock_urlopen: A patched urllib object
        """
        url = "http://test"
        mock_urlopen.side_effect = urllib2.URLError("URL Error ")
        result = self.stats.get_info(url)
        self.assertIsNone(result)

    @patch('collectd_rabbitmq.rabbit.urllib2.urlopen')
    def test_get_info_url_bad_json(self, mock_urlopen):
        """
        Asserts that get_info returns None on bad json.

        Args:
        :param mock_urlopen: A patched urllib object
        """
        url = "http://test"
        mock_response = MockURLResponse('{"test":test}')
        mock_urlopen.return_value = mock_response
        result = self.stats.get_info(url)
        self.assertIsNone(result)


class TestBaseClass(unittest.TestCase):
    """
    Base class for Stats test.
    """

    def setUp(self):
        self.conn = ConnectionInfo(host="example.com",
                                   port=15672,
                                   scheme="http")
        self.auth = Auth()
        self.conf = Config(self.auth, self.conn)
        self.stats = RabbitMQStats(self.conf)

        self.test_stats = dict(
            vhost="test_vhost",
            message_stats=dict(
                publish_in=10,
                publish_in_details=dict(rate=0.0),
                publish_out=10,
                publish_out_details=dict(rate=0.0)
            ))


class TestVhost(TestBaseClass):
    """
    Test vhost items.
    """

    def setUp(self):
        TestBaseClass.setUp(self)
        self.test_vhosts = [
            dict(name='/'),
            dict(name='test_vhosta'),
            dict(name='test_vhostb')]

    @patch('collectd_rabbitmq.rabbit.urllib2.urlopen')
    def test_vhots(self, mock_urlopen):
        """
        Asserts that get_vhosts returns all vhosts data.

        Args:
        :param mock_urlopen: A patched urllib object
        """
        mock_response = MockURLResponse(json.dumps(self.test_vhosts))
        mock_urlopen.return_value = mock_response
        vhosts = self.stats.get_vhosts()
        self.assertEqual(len(vhosts), len(self.test_vhosts))

    @patch('collectd_rabbitmq.rabbit.urllib2.urlopen')
    def test_vhots_names(self, mock_urlopen):
        """
        Asserts that get_vhosts returns all vhosts data.

        Args:
        :param mock_urlopen: A patched urllib object
        """
        mock_response = MockURLResponse(json.dumps(self.test_vhosts))
        mock_urlopen.return_value = mock_response
        vhost_names = self.stats.get_vhost_names()
        self.assertIn('%2F', vhost_names)
        self.assertIn('test_vhosta', vhost_names)
        self.assertIn('test_vhostb', vhost_names)


class TestStatsBaseClass(TestBaseClass):
    """
    Base class for Stats test.
    """

    def setUp(self):
        TestBaseClass.setUp(self)
        self.stats.get_vhost_names = Mock()
        self.stats.get_vhost_names.return_value = ['test_vhost']


class TestGetStats(TestBaseClass):
    """
    Tests the get stats method.
    """

    def test_get_stats_bad_type(self):
        """
        Asserts that a Value error is raise if type is incorrect.

        Args:
        :param mock_urlopen: A patched urllib object
        """
        self.assertRaises(ValueError, self.stats.get_stats,
                          'cheese', 'test', 'test_vhost')


class TestExchanges(TestStatsBaseClass):
    """
    Test the exchange stats.
    """
    @patch('collectd_rabbitmq.rabbit.urllib2.urlopen')
    def test_get_exchange_stats(self, mock_urlopen):
        """
        Asserts that exchange returns proper stats.

        Args:
        :param mock_urlopen: A patched urllib object
        """
        self.test_stats['name'] = 'test_exchange'
        mock_response = MockURLResponse(self.test_stats)
        mock_urlopen.return_value = mock_response
        stats = self.stats.get_exchange_stats('test_exchange')
        self.assertTrue(stats)

    @patch('collectd_rabbitmq.rabbit.urllib2.urlopen')
    def test_get_all_exchange_stats(self, mock_urlopen):
        """
        Asserts that exchange returns proper stats.

        Args:
        :param mock_urlopen: A patched urllib object
        """
        self.stats.get_exchanges = Mock()
        self.stats.get_exchanges.return_value = [dict(name='e1'),
                                                 dict(name='e2'),
                                                 dict(name='e3')]
        self.test_stats['name'] = 'test_exchange'
        mock_response = MockURLResponse(self.test_stats)
        mock_urlopen.return_value = mock_response
        stats = self.stats.get_exchange_stats()
        self.assertTrue(stats)


class TestQueues(TestStatsBaseClass):
    """
    Test the exchange stats.
    """

    @patch('collectd_rabbitmq.rabbit.urllib2.urlopen')
    def test_get_queue_stats(self, mock_urlopen):
        """
        Asserts that queue returns proper stats.

        Args:
        :param mock_urlopen: A patched urllib object
        """
        self.test_stats['name'] = 'test_queue'
        mock_response = MockURLResponse(self.test_stats)
        mock_urlopen.return_value = mock_response
        stats = self.stats.get_queue_stats('test_queue')
        self.assertTrue(stats)

    @patch('collectd_rabbitmq.rabbit.urllib2.urlopen')
    def test_get_all_queue_stats(self, mock_urlopen):
        """
        Asserts that queue returns proper stats.

        Args:
        :param mock_urlopen: A patched urllib object
        """
        self.stats.get_queues = Mock()
        self.stats.get_queues.return_value = [dict(name='q1'),
                                              dict(name='q2'),
                                              dict(name='q3')]
        self.test_stats['name'] = 'test_queue'
        mock_response = MockURLResponse(self.test_stats)
        mock_urlopen.return_value = mock_response
        stats = self.stats.get_queue_stats()
        self.assertTrue(stats)


class TestIgnoredQueues(TestStatsBaseClass):
    """
    Test the ignored queues.
    """

    def setUp(self):
        TestStatsBaseClass.setUp(self)
        data_to_ignore = dict(queue=["a.*", "b.*", "c.*"])
        conf = Config(self.auth, self.conn, data_to_ignore)
        self.stats = RabbitMQStats(conf)
        self.stats.get_vhost_names = Mock()
        self.stats.get_vhost_names.return_value = ['test_vhost']

    @patch('collectd_rabbitmq.rabbit.urllib2.urlopen')
    def test_get_filterd_queue_stats(self, mock_urlopen):
        """
        Asserts that queue stats are filtered.

        Args:
        :param mock_urlopen: A patched urllib object
        """
        self.stats.get_queues = Mock()
        self.stats.get_queues.return_value = [
            dict(name='a1'), dict(name='a2'), dict(name='a3'),
            dict(name='b1'), dict(name='b2'), dict(name='b3'),
            dict(name='c1'), dict(name='c2'), dict(name='c3'),
            dict(name='d1'), dict(name='d2'), dict(name='d3'),
            dict(name='e1'), dict(name='e2'), dict(name='e3'),
            dict(name='f1'), dict(name='f2'), dict(name='f3'),
        ]

        mock_urlopen.side_effect = create_mock_url_repsonse
        stats = self.stats.get_queue_stats()
        self.assertNotIn('a1', stats.keys())
        self.assertNotIn('a2', stats.keys())
        self.assertNotIn('a3', stats.keys())

        self.assertNotIn('b1', stats.keys())
        self.assertNotIn('b2', stats.keys())
        self.assertNotIn('b3', stats.keys())

        self.assertNotIn('c1', stats.keys())
        self.assertNotIn('c2', stats.keys())
        self.assertNotIn('c3', stats.keys())

        self.assertIn('d1', stats.keys())
        self.assertIn('d2', stats.keys())
        self.assertIn('d3', stats.keys())

        self.assertIn('e1', stats.keys())
        self.assertIn('e2', stats.keys())
        self.assertIn('e3', stats.keys())

        self.assertIn('f1', stats.keys())
        self.assertIn('f2', stats.keys())
        self.assertIn('f3', stats.keys())

    @patch('collectd_rabbitmq.rabbit.urllib2.urlopen')
    def test_get_exchanges(self, mock_urlopen):
        """
        Asserts that get_exchanges returns the proper data.

        Args:
        :param mock_urlopen: A patched urllib object
        """
        mock_urlopen.side_effect = create_mock_url_repsonse
        exchanges = self.stats.get_exchanges("test_vhost")
        self.assertIsNotNone(exchanges)


class TestIgnoredExchanges(TestStatsBaseClass):
    """
    Test the ignored exchanges.
    """

    def setUp(self):
        TestStatsBaseClass.setUp(self)
        data_to_ignore = dict(exchange=["a.*", "b.*", "c.*"])
        conf = Config(self.auth, self.conn, data_to_ignore)
        self.stats = RabbitMQStats(conf)
        self.stats.get_vhost_names = Mock()
        self.stats.get_vhost_names.return_value = ['test_vhost']

    @patch('collectd_rabbitmq.rabbit.urllib2.urlopen')
    def test_get_filterd_exchange_stats(self, mock_urlopen):
        """
        Asserts that exchange stats are filtered.

        Args:
        :param mock_urlopen: A patched urllib object
        """
        self.stats.get_exchanges = Mock()
        self.stats.get_exchanges.return_value = [
            dict(name='a1'), dict(name='a2'), dict(name='a3'),
            dict(name='b1'), dict(name='b2'), dict(name='b3'),
            dict(name='c1'), dict(name='c2'), dict(name='c3'),
            dict(name='d1'), dict(name='d2'), dict(name='d3'),
            dict(name='e1'), dict(name='e2'), dict(name='e3'),
            dict(name='f1'), dict(name='f2'), dict(name='f3'),
        ]

        mock_urlopen.side_effect = create_mock_url_repsonse
        stats = self.stats.get_exchange_stats()
        self.assertNotIn('a1', stats.keys())
        self.assertNotIn('a2', stats.keys())
        self.assertNotIn('a3', stats.keys())

        self.assertNotIn('b1', stats.keys())
        self.assertNotIn('b2', stats.keys())
        self.assertNotIn('b3', stats.keys())

        self.assertNotIn('c1', stats.keys())
        self.assertNotIn('c2', stats.keys())
        self.assertNotIn('c3', stats.keys())

        self.assertIn('d1', stats.keys())
        self.assertIn('d2', stats.keys())
        self.assertIn('d3', stats.keys())

        self.assertIn('e1', stats.keys())
        self.assertIn('e2', stats.keys())
        self.assertIn('e3', stats.keys())

        self.assertIn('f1', stats.keys())
        self.assertIn('f2', stats.keys())
        self.assertIn('f3', stats.keys())

    @patch('collectd_rabbitmq.rabbit.urllib2.urlopen')
    def test_get_queue(self, mock_urlopen):
        """
        Asserts that get_queues returns the proper data.

        Args:
        :param mock_urlopen: A patched urllib object
        """
        mock_urlopen.side_effect = create_mock_url_repsonse
        queues = self.stats.get_queues("test_vhost")
        self.assertIsNotNone(queues)

if __name__ == '__main__':

    logging.basicConfig(stream=sys.stderr)
    logging.getLogger().setLevel(logging.DEBUG)
    unittest.main()
