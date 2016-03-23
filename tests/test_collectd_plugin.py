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

import logging  # noqa
import os  # noqa
import sys  # noqa
import unittest  # noqa

from mock import MagicMock, Mock, patch

# Updating path so that the mock collectd gets added
sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import collectd  # noqa

from collectd_rabbitmq import collectd_plugin  # noqa
from tests.utils import create_mock_url_repsonse  # noqa
from tests.utils import create_mock_node_url_repsonse, get_message_stats_data  # noqa


class TestCollectdPluginCallbacks(unittest.TestCase):
    """
    Test the collectd callbacks
    """

    def test_read(self):
        """
        Asserts that read runs when plugin is loaded
        """
        collectd_plugin.PLUGIN = MagicMock()
        collectd_plugin.PLUGIN.read = MagicMock()
        collectd_plugin.read()
        self.assertTrue(collectd_plugin.PLUGIN.read.called)

    @patch.object(collectd_plugin.CollectdPlugin, 'read')
    def test_read_no_plugin(self, mock_read):
        """
        Asserts that read does not run when plugin is not loaded

        Args:
        :param mock_read a patched method from a :mod:`CollectdPlugin`.
        """
        collectd_plugin.PLUGIN = None
        collectd_plugin.read()
        self.assertFalse(mock_read.called)

    @patch.object(collectd_plugin.CollectdPlugin, '__new__')
    def test_init_plugin(self, mock_plugin):
        """
        Asserts that init create the plugin.
        """
        collectd_plugin.init()
        self.assertTrue(mock_plugin.called)
        self.assertIsNotNone(collectd_plugin.PLUGIN)


class BaseTestCollectdPlugin(unittest.TestCase):
    """
    Test the configuration.
    """

    def setUp(self):
        username = collectd.Config('Username', ('admin',))
        password = collectd.Config('Password', ('admin',))
        realm = collectd.Config('Realm', ('RabbitMQ Management',))
        host = collectd.Config('Host', ('localhost',))
        port = collectd.Config('Port', ('15672',))
        ignore_queues = [
            collectd.Config('Regex', ('amq-gen-.*',)),
            collectd.Config('Regex', ('tmp-.*',)),
        ]
        ignore_exchanges = [
            collectd.Config('Regex', ('amq.*',)),
        ]
        ignore_queue = collectd.Config('Ignore', ('queue',), ignore_queues)
        ignore_exchange = collectd.Config('Ignore', ('exchange',),
                                          ignore_exchanges)
        self.module = collectd.Config('Module',
                                      ('rabbitmq',),
                                      [username,
                                       password,
                                       host,
                                       port,
                                       realm,
                                       ignore_queue,
                                       ignore_exchange])
        collectd_plugin.configure(self.module)
        self.collectd_plugin = collectd_plugin.CollectdPlugin()


class TestCollectdPluginConfig(BaseTestCollectdPlugin):
    """
    Test the configuration.
    """

    def test_config(self):
        """
        Asserts that configuration is populated properly.
        """
        self.assertIsNotNone(collectd_plugin.CONFIG)
        self.assertIsNotNone(collectd_plugin.CONFIG.connection)
        self.assertIsNotNone(collectd_plugin.CONFIG.data_to_ignore)
        self.assertEquals(len(collectd_plugin.CONFIG.data_to_ignore), 2)


class TestCollectdPluginExchanges(BaseTestCollectdPlugin):
    """
    Test the exchange stats are dispatched properly.
    """

    @patch.object(collectd_plugin.rabbit.RabbitMQStats, 'get_vhosts')
    @patch('collectd_rabbitmq.rabbit.urllib2.urlopen')
    def test_dispatch_exchanges(self, mock_urlopen, mock_vhosts):
        """
        Assert exchanges are dispatched with the correct data.
        Args:
        :param mock_urlopen: a patched :mod:`rabbit.urllib2.urlopen` object
        :param mock_vhosts: a patched method from a :mod:`CollectdPlugin`
        """
        self.collectd_plugin.rabbit.get_exchanges = Mock()
        self.collectd_plugin.rabbit.get_exchanges.return_value = [
            dict(name='TestExchange1'),
            dict(name='TestExchange2'),
        ]

        mock_urlopen.side_effect = create_mock_url_repsonse
        mock_vhosts.return_value = [dict(name='test_vhost')]

        self.collectd_plugin.dispatch_values = MagicMock()
        self.collectd_plugin.dispatch_exchanges('test_vhost')

        e1_stats = get_message_stats_data('TestExchange1')['message_stats']
        e2_stats = get_message_stats_data('TestExchange2')['message_stats']

        self.collectd_plugin.dispatch_values.assert_any_call(
            e1_stats['publish_in'], 'rabbitmq_test_vhost', 'exchanges',
            'TestExchange1', 'publish_in'
        )

        self.collectd_plugin.dispatch_values.assert_any_call(
            e1_stats['publish_in_details']['rate'], 'rabbitmq_test_vhost',
            'exchanges', 'TestExchange1', 'publish_in_details', 'rate'
        )

        self.collectd_plugin.dispatch_values.assert_any_call(
            e1_stats['publish_out'], 'rabbitmq_test_vhost', 'exchanges',
            'TestExchange1', 'publish_out'
        )

        self.collectd_plugin.dispatch_values.assert_any_call(
            e1_stats['publish_out_details']['rate'], 'rabbitmq_test_vhost',
            'exchanges', 'TestExchange1', 'publish_out_details', 'rate'
        )

        self.collectd_plugin.dispatch_values.assert_any_call(
            e2_stats['publish_in'], 'rabbitmq_test_vhost', 'exchanges',
            'TestExchange2', 'publish_in'
        )

        self.collectd_plugin.dispatch_values.assert_any_call(
            e2_stats['publish_in_details']['rate'], 'rabbitmq_test_vhost',
            'exchanges', 'TestExchange2', 'publish_in_details', 'rate'
        )

        self.collectd_plugin.dispatch_values.assert_any_call(
            e2_stats['publish_out'], 'rabbitmq_test_vhost', 'exchanges',
            'TestExchange2', 'publish_out'
        )

        self.collectd_plugin.dispatch_values.assert_any_call(
            e2_stats['publish_out_details']['rate'], 'rabbitmq_test_vhost',
            'exchanges', 'TestExchange2', 'publish_out_details', 'rate'
        )


class TestCollectdPluginQueues(BaseTestCollectdPlugin):
    """
    Test the queue stats are dispatched properly.
    """
    @patch.object(collectd_plugin.rabbit.RabbitMQStats, 'get_vhosts')
    @patch('collectd_rabbitmq.rabbit.urllib2.urlopen')
    def test_dispatch_queues(self, mock_urlopen, mock_vhosts):
        """
        Assert queues are dispatched with the correct data.
        Args:
        :param mock_urlopen: a patched :mod:`rabbit.urllib2.urlopen` object
        :param mock_vhosts: a patched method from a :mod:`CollectdPlugin`
        """
        self.collectd_plugin.rabbit.get_queues = Mock()
        self.collectd_plugin.rabbit.get_queues.return_value = [
            dict(name='TestQueue1'),
            dict(name='TestQueue2'),
        ]

        mock_urlopen.side_effect = create_mock_url_repsonse
        mock_vhosts.return_value = [dict(name='test_vhost')]

        self.collectd_plugin.dispatch_values = MagicMock()
        self.collectd_plugin.dispatch_queues('test_vhost')

        q1_stats = get_message_stats_data('TestQueue1')['message_stats']
        q2_stats = get_message_stats_data('TestQueue2')['message_stats']

        self.collectd_plugin.dispatch_values.assert_any_call(
            q1_stats['publish_in'], 'rabbitmq_test_vhost', 'queues',
            'TestQueue1', 'publish_in'
        )

        self.collectd_plugin.dispatch_values.assert_any_call(
            q1_stats['publish_in_details']['rate'], 'rabbitmq_test_vhost',
            'queues', 'TestQueue1', 'publish_in_details', 'rate'
        )

        self.collectd_plugin.dispatch_values.assert_any_call(
            q1_stats['publish_out'], 'rabbitmq_test_vhost', 'queues',
            'TestQueue1', 'publish_out'
        )

        self.collectd_plugin.dispatch_values.assert_any_call(
            q1_stats['publish_out_details']['rate'], 'rabbitmq_test_vhost',
            'queues', 'TestQueue1', 'publish_out_details', 'rate'
        )

        self.collectd_plugin.dispatch_values.assert_any_call(
            q2_stats['publish_in'], 'rabbitmq_test_vhost', 'queues',
            'TestQueue2', 'publish_in'
        )

        self.collectd_plugin.dispatch_values.assert_any_call(
            q2_stats['publish_in_details']['rate'], 'rabbitmq_test_vhost',
            'queues', 'TestQueue2', 'publish_in_details', 'rate'
        )

        self.collectd_plugin.dispatch_values.assert_any_call(
            q2_stats['publish_out'], 'rabbitmq_test_vhost', 'queues',
            'TestQueue2', 'publish_out'
        )

        self.collectd_plugin.dispatch_values.assert_any_call(
            q2_stats['publish_out_details']['rate'], 'rabbitmq_test_vhost',
            'queues', 'TestQueue2', 'publish_out_details', 'rate'
        )


class TestCollectdPluginVhost(BaseTestCollectdPlugin):
    """
    Test the vhosts are generated properly.
    """

    def test_generate_vhost_empty(self):
        """
        Assert empty vhost is set properly.
        """
        vhost = self.collectd_plugin.generate_vhost_name(None)
        self.assertEquals(vhost, "rabbitmq_default")

    def test_generate_vhost_default(self):
        """
        Assert default vhost is set properly.
        """
        vhost = self.collectd_plugin.generate_vhost_name("/")
        self.assertEquals(vhost, "rabbitmq_default")

    def test_generate_vhost_start_slash(self):
        """
        Assert vhost that starts with a '/' is set properly.
        """
        vhost = self.collectd_plugin.generate_vhost_name("/vhost")
        self.assertEquals(vhost, "rabbitmq_slash_vhost")

    def test_generate_vhost_end_slash(self):
        """
        Assert vhost that ends with a '/' is set properly.
        """
        vhost = self.collectd_plugin.generate_vhost_name("vhost/")
        self.assertEquals(vhost, "rabbitmq_vhost_slash")

    def test_generate_vhost(self):
        """
        Assert vhost that contains a slash is set properly.
        """
        vhost = self.collectd_plugin.generate_vhost_name("vho/st")
        self.assertEquals(vhost, "rabbitmq_vho_slash_st")


class TestCollectdPluginNodes(BaseTestCollectdPlugin):
    """
    Test that the read methood dispatches the proper data.
    """

    @patch('collectd_rabbitmq.rabbit.urllib2.urlopen')
    def test_read(self, mock_urlopen):
        """
        Assert node stats are dispatched.
        Args:
        :param mock_urlopen: a patched :mod:`rabbit.urllib2.urlopen' object
        """
        mock_urlopen.side_effect = create_mock_node_url_repsonse

        dispatch_values = MagicMock()
        self.collectd_plugin.dispatch_values = dispatch_values
        self.collectd_plugin.dispatch_nodes()
        self.assertTrue(dispatch_values.called)


class TestCollectdPluginRead(BaseTestCollectdPlugin):
    """
    Test that the read method dispatches the proper data.
    """
    @patch.object(collectd_plugin.rabbit.RabbitMQStats, 'get_vhosts')
    def test_read(self, mock_vhosts):
        """
        Assert all types of stats are dispatched.
        Args:
        :param mock_vhosts: a patched method from a :mod:`RabbitMQStats`
        """
        mock_vhosts.return_value = [dict(name='test_vhost')]

        dispatch_nodes = MagicMock()
        dispatch_queues = MagicMock()
        dispatch_exchanges = MagicMock()
        self.collectd_plugin.dispatch_nodes = dispatch_nodes
        self.collectd_plugin.dispatch_queues = dispatch_queues
        self.collectd_plugin.dispatch_exchanges = dispatch_exchanges

        self.collectd_plugin.read()

        self.assertTrue(dispatch_nodes.called)
        self.assertTrue(dispatch_queues.called)
        self.assertTrue(dispatch_exchanges.called)

    def test_read_no_vhosts(self):
        """
        Assert only node stats are dispatched if not vhosts.
        """

        dispatch_nodes = MagicMock()
        dispatch_queues = MagicMock()
        dispatch_exchanges = MagicMock()
        self.collectd_plugin.dispatch_nodes = dispatch_nodes
        self.collectd_plugin.dispatch_queues = dispatch_queues
        self.collectd_plugin.dispatch_exchanges = dispatch_exchanges

        self.collectd_plugin.read()

        self.assertTrue(dispatch_nodes.called)
        self.assertFalse(dispatch_queues.called)
        self.assertFalse(dispatch_exchanges.called)


class TestCollectdPluginDispatch(BaseTestCollectdPlugin):
    """
    Test the underlying dispatch method.
    """

    @patch('collectd.Values')
    def test_dispatch(self, mock_collectd_values):
        """
        Assert all types of stats are dispatched.
        Args:
        :param mock_collectd_values: a test object
        """
        mock_values = collectd.Values()
        mock_values.dispatch = MagicMock()
        mock_collectd_values.return_value = mock_values
        self.collectd_plugin.dispatch_values((1, 2, 3), 'vhost', 'plugin',
                                             'plugin_instance', 'meteric_type')
        self.assertEqual(mock_values.host, "vhost")
        self.assertTrue(mock_values.dispatch.called)

    @patch('collectd.Values')
    def test_dispatch_non_list(self, mock_collectd_values):
        """
        Assert that a non list value is dispatched.
        Args:
        :param mock_collectd_values: a test object
        """
        mock_values = collectd.Values()
        mock_values.dispatch = MagicMock()
        mock_collectd_values.return_value = mock_values
        self.collectd_plugin.dispatch_values('test_value', 'vhost', 'plugin',
                                             'plugin_instance', 'meteric_type')
        self.assertEqual(mock_values.host, "vhost")
        self.assertTrue(mock_values.dispatch.called)

    @patch('collectd.Values')
    def test_dispatch_meta(self, mock_collectd_values):
        """
        Assert meta is set for rabbitmq versions < 5.5.
        Args:
        :param mock_collectd_values: a test object
        """
        mock_values = collectd.Values()
        mock_collectd_values.return_value = mock_values
        self.collectd_plugin.dispatch_values((1, 2, 3), '/', 'plugin',
                                             'plugin_instance', 'meteric_type')
        self.assertEqual(mock_values.meta, {'0': True})

    @patch('collectd.Values')
    def test_dispatch_type_instance(self, mock_collectd_values):
        """
        Assert type_instance get set and dispatched.
        Args:
        :param mock_collectd_values: a test object
        """
        mock_values = collectd.Values()
        mock_collectd_values.return_value = mock_values
        self.collectd_plugin.dispatch_values((1, 2, 3), '/', 'plugin',
                                             'plugin_instance', 'meteric_type',
                                             'type_instance')
        self.assertEqual(mock_values.type_instance, "type_instance")


class TestCollectdPluginDispatchMessageStats(BaseTestCollectdPlugin):
    """
    Test the helper function to dispatch message stats.
    """

    def test_dispatch_no_data(self):
        """
        Assert that empty data is not dispatched.
        """
        self.collectd_plugin.dispatch_values = Mock()
        self.collectd_plugin.dispatch_message_stats(None, 'test_vhost',
                                                    'test_plugin',
                                                    'type_plugin_instance')
        self.assertFalse(self.collectd_plugin.dispatch_values.called)

    def test_dispatch_no_message_stats(self):
        """
        Assert that data without message_stats are not dispatched.
        """
        self.collectd_plugin.dispatch_values = Mock()
        self.collectd_plugin.dispatch_message_stats(dict(test=Mock),
                                                    'test_vhost',
                                                    'test_plugin',
                                                    'type_plugin_instance')
        self.assertFalse(self.collectd_plugin.dispatch_values.called)

if __name__ == '__main__':

    logging.basicConfig(stream=sys.stderr)
    logging.getLogger().setLevel(logging.DEBUG)
    unittest.main()
