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
        fake_config = MagicMock()
        collectd_plugin.INSTANCES = [fake_config]
        fake_config.read = MagicMock()
        collectd_plugin.read()
        self.assertIsNotNone(collectd_plugin.CONFIGS)
        self.assertTrue(fake_config.read.called)
        collectd_plugin.INSTANCES = []

    @patch.object(collectd_plugin.CollectdPlugin, 'read')
    def test_read_no_plugin(self, mock_read):
        """
        Asserts that read does not run when plugin is not loaded

        Args:
        :param mock_read a patched method from a :mod:`CollectdPlugin`.
        """
        collectd_plugin.read()
        self.assertFalse(mock_read.called)

    def test_init(self):
        """
        Asserts that init creates new instances of the CollectdPlugin for each
        config.
        """

        fake_config = MagicMock()
        collectd_plugin.CONFIGS = [fake_config]
        collectd_plugin.INSTANCES = []
        collectd_plugin.init()
        self.assertIsNotNone(collectd_plugin.INSTANCES)
        collectd_plugin.INSTANCES = []
        collectd_plugin.CONFIGS = []


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
        schema = collectd.Config('Scheme', ('http',))
        vhost_prefix = collectd.Config('VHostPrefix', ('',))
        validate_certs = collectd.Config('ValidateCerts', ('false',))

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
        config_data = [username,
                       password,
                       host,
                       port,
                       realm,
                       schema,
                       ignore_queue,
                       ignore_exchange,
                       vhost_prefix,
                       validate_certs
                       ]
        self.test_config = collectd.Config(
            'Module', ('rabbitmq',), config_data)

        collectd_plugin.configure(self.test_config)
        self.collectd_plugin = collectd_plugin.CollectdPlugin(
            collectd_plugin.CONFIGS[0])


class TestCollectdPluginConfig(BaseTestCollectdPlugin):
    """
    Test the configuration.
    """

    def test_config(self):
        """
        Asserts that configuration is populated properly.
        """
        self.assertIsNotNone(collectd_plugin.CONFIGS)
        self.assertIsNotNone(collectd_plugin.CONFIGS[0].connection)
        self.assertIsNotNone(collectd_plugin.CONFIGS[0].data_to_ignore)
        self.assertEqual(len(collectd_plugin.CONFIGS[0].data_to_ignore), 2)


class TestCollectdPluginExchanges(BaseTestCollectdPlugin):
    """
    Test the exchange stats are dispatched properly.
    """

    @patch.object(collectd_plugin.rabbit.RabbitMQStats, 'get_vhosts')
    @patch('collectd_rabbitmq.rabbit.urllib.request.urlopen')
    def test_dispatch_exchanges(self, mock_urlopen, mock_vhosts):
        """
        Assert exchanges are dispatched with the correct data.
        Args:
        :param mock_urlopen: a patched :mod:`rabbit.urllib.request.urlopen`
            object
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

    @patch.object(collectd_plugin.rabbit.RabbitMQStats, 'get_vhosts')
    @patch('collectd_rabbitmq.rabbit.urllib.request.urlopen')
    def test_dispatch_exchanges_empty_value(self, mock_urlopen, mock_vhosts):
        """
        Assert an non-existant value is not dispatched.
        Args:
        :param mock_urlopen: a patched :mod:`rabbit.urllib.request.urlopen`
            object
        :param mock_vhosts: a patched method from a :mod:`CollectdPlugin`
        """
        self.collectd_plugin.rabbit.get_exchanges = Mock()
        self.collectd_plugin.rabbit.get_exchanges.return_value = [
            dict(name='TestExchange'),
        ]

        mock_urlopen.side_effect = create_mock_url_repsonse
        mock_vhosts.return_value = [dict(name='test_vhost')]

        self.collectd_plugin.dispatch_values = MagicMock()
        self.collectd_plugin.dispatch_exchanges('test_vhost')

        reported_metrics = [
            call[0][4] for call in
            self.collectd_plugin.dispatch_values.call_args_list
        ]
        self.assertEqual(
            set(reported_metrics),
            set(get_message_stats_data('TestExchange')['message_stats'].keys())
        )


class TestCollectdPluginQueues(BaseTestCollectdPlugin):
    """
    Test the queue stats are dispatched properly.
    """
    @patch.object(collectd_plugin.rabbit.RabbitMQStats, 'get_vhosts')
    @patch('collectd_rabbitmq.rabbit.urllib.request.urlopen')
    def test_dispatch_queues(self, mock_urlopen, mock_vhosts):
        """
        Assert queues are dispatched with the correct data.
        Args:
        :param mock_urlopen: a patched :mod:`rabbit.urllib.request.urlopen`
            object
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

    @patch.object(collectd_plugin.rabbit.RabbitMQStats, 'get_vhosts')
    @patch('collectd_rabbitmq.rabbit.urllib.request.urlopen')
    def test_dispatch_queue_stats(self, mock_urlopen, mock_vhosts):
        """
        Assert queues are dispatched with preoper data.
        Args:
        :param mock_urlopen: a patched :mod:`rabbit.urllib.request.urlopen`
            object
        :param mock_vhosts: a patched method from a :mod:`CollectdPlugin`
        """
        mock_dispatch = MagicMock()
        mock_queue_stats = dict(messages=10)
        self.collectd_plugin.dispatch_values = mock_dispatch
        self.collectd_plugin.dispatch_queue_stats(
            mock_queue_stats, 'test_vhost', None, None)

        self.assertTrue(mock_dispatch.called)

    @patch.object(collectd_plugin.rabbit.RabbitMQStats, 'get_vhosts')
    @patch('collectd_rabbitmq.rabbit.urllib.request.urlopen')
    def test_dispatch_queue_stats_consumer_utilisation(
            self, mock_urlopen, mock_vhosts):
        """
        Assert queues are dispatched with preoper data.
        Args:
        :param mock_urlopen: a patched :mod:`rabbit.urllib.request.urlopen`
            object
        :param mock_vhosts: a patched method from a :mod:`CollectdPlugin`
        """
        mock_dispatch = MagicMock()
        mock_queue_stats = dict(consumer_utilisation=None)
        self.collectd_plugin.dispatch_values = mock_dispatch
        self.collectd_plugin.dispatch_queue_stats(
            mock_queue_stats, 'test_vhost', None, None)

        self.assertTrue(mock_dispatch.called)

    @patch.object(collectd_plugin.rabbit.RabbitMQStats, 'get_vhosts')
    @patch('collectd_rabbitmq.rabbit.urllib.request.urlopen')
    def test_dispatch_empty_queue_stats(self, mock_urlopen, mock_vhosts):
        """
        Assert queues are not dispatched with no data.
        Args:
        :param mock_urlopen: a patched :mod:`rabbit.urllib.request.urlopen`
            object
        :param mock_vhosts: a patched method from a :mod:`CollectdPlugin`
        """
        mock_dispatch = MagicMock()
        self.collectd_plugin.dispatch_values = mock_dispatch

        self.collectd_plugin.dispatch_queue_stats(
            None, 'test_vhost', None, None)

        self.assertFalse(mock_dispatch.called)

    @patch.object(collectd_plugin.rabbit.RabbitMQStats, 'get_vhosts')
    @patch('collectd_rabbitmq.rabbit.urllib.request.urlopen')
    def test_dispatch_queues_empty_values(self, mock_urlopen, mock_vhosts):
        """
        Assert empty values are not dispatched.
        Args:
        :param mock_urlopen: a patched :mod:`rabbit.urllib.request.urlopen`
            object
        :param mock_vhosts: a patched method from a :mod:`CollectdPlugin`
        """
        self.collectd_plugin.rabbit.get_queues = Mock()
        self.collectd_plugin.rabbit.get_queues.return_value = [
            dict(name='TestQueue'),
        ]

        mock_urlopen.side_effect = create_mock_url_repsonse
        mock_vhosts.return_value = [dict(name='test_vhost')]

        self.collectd_plugin.dispatch_values = MagicMock()
        self.collectd_plugin.dispatch_queues('test_vhost')

        reported_metrics = [
            call[0][4] for call in
            self.collectd_plugin.dispatch_values.call_args_list
        ]
        self.assertEqual(
            set(reported_metrics),
            set(get_message_stats_data('TestQueue')['message_stats'].keys())
        )


class TestCollectdPluginOverviewStats(BaseTestCollectdPlugin):
    """
    Test the overview stats are dispatched properly.
    """
    @patch.object(collectd_plugin.rabbit.RabbitMQStats, 'get_vhosts')
    @patch('collectd_rabbitmq.rabbit.urllib.request.urlopen')
    def test_overview_stats_no_details(self, mock_urlopen, mock_vhosts):
        """
        Assert overview stats are dispatched with even if there are no details.
        This work by manking sure that only the default data is dispatched.

        Args:
        :param mock_urlopen: a patched :mod:`rabbit.urllib.request.urlopen`
            object
        :param mock_vhosts: a patched method from a :mod:`CollectdPlugin`
        """
        mock_get = Mock()
        self.collectd_plugin.rabbit.get_overview_stats = mock_get
        mock_stats = dict(cluster_name="test_cluster")
        mock_get.return_value = mock_stats

        mock_dispatch = MagicMock()
        self.collectd_plugin.dispatch_values = mock_dispatch
        self.collectd_plugin.dispatch_overview()

        # Calculate the proper nubmer of dispatches without dispatching details
        dispatches = sum(len(v) for v in self.collectd_plugin.overview_stats)

        self.assertTrue(mock_dispatch.call_count < dispatches)

    @patch.object(collectd_plugin.rabbit.RabbitMQStats, 'get_vhosts')
    @patch('collectd_rabbitmq.rabbit.urllib.request.urlopen')
    def test_overview_stats_no_cluster_name_no_details(self,
                                                       mock_urlopen,
                                                       mock_vhosts):
        """
        Assert overview stats without cluster name are dispatched with even
        if there are no details. This work by manking sure that only the
        default data is dispatched.

        Args:
        :param mock_urlopen: a patched :mod:`rabbit.urllib.request.urlopen`
            object
        :param mock_vhosts: a patched method from a :mod:`CollectdPlugin`
        """
        mock_get = Mock()
        self.collectd_plugin.rabbit.get_overview_stats = mock_get
        mock_stats = dict()
        mock_get.return_value = mock_stats

        mock_dispatch = MagicMock()
        self.collectd_plugin.dispatch_values = mock_dispatch
        self.collectd_plugin.dispatch_overview()

        # Calculate the proper nubmer of dispatches without dispatching details
        dispatches = sum(len(v) for v in self.collectd_plugin.overview_stats)

        self.assertTrue(mock_dispatch.call_count < dispatches)

    @patch.object(collectd_plugin.rabbit.RabbitMQStats, 'get_vhosts')
    @patch('collectd_rabbitmq.rabbit.urllib.request.urlopen')
    def test_overview_stats_details(self, mock_urlopen, mock_vhosts):
        """
        Assert overview stats are dispatched with even if there are no details.
        This work by manking sure that only the default data is dispatched.

        Args:
        :param mock_urlopen: a patched :mod:`rabbit.urllib.request.urlopen`
            object
        :param mock_vhosts: a patched method from a :mod:`CollectdPlugin`
        """
        mock_get = Mock()
        self.collectd_plugin.rabbit.get_overview_stats = mock_get
        mock_stats = dict(cluster_name="test_cluster",
                          object_totals=dict(consumers_details=dict(rate=10)))
        mock_get.return_value = mock_stats

        mock_dispatch = MagicMock()
        self.collectd_plugin.dispatch_values = mock_dispatch
        self.collectd_plugin.dispatch_overview()

        # Calculate the proper nubmer of default dispatches
        dispatches = sum(len(v) for v in self.collectd_plugin.overview_stats)
        # Add 1 for our detailed dispatch
        dispatches = dispatches + 1
        self.assertTrue(mock_dispatch.call_count < dispatches)

    @patch.object(collectd_plugin.rabbit.RabbitMQStats, 'get_vhosts')
    @patch('collectd_rabbitmq.rabbit.urllib.request.urlopen')
    def test_overview_stats_details_no_cluster_name(self,
                                                    mock_urlopen,
                                                    mock_vhosts):
        """
        Assert overview stats without cluster_name are dispatched.
        This work by manking sure that only the default data is dispatched.

        Args:
        :param mock_urlopen: a patched :mod:`rabbit.urllib.request.urlopen`
            object
        :param mock_vhosts: a patched method from a :mod:`CollectdPlugin`
        """
        mock_get = Mock()
        self.collectd_plugin.rabbit.get_overview_stats = mock_get
        mock_stats = dict(object_totals=dict(consumers_details=dict(rate=10)))
        mock_get.return_value = mock_stats

        mock_dispatch = MagicMock()
        self.collectd_plugin.dispatch_values = mock_dispatch
        self.collectd_plugin.dispatch_overview()

        # Calculate the proper nubmer of default dispatches
        dispatches = sum(len(v) for v in self.collectd_plugin.overview_stats)
        # Add 1 for our detailed dispatch
        dispatches = dispatches + 1
        self.assertTrue(mock_dispatch.call_count < dispatches)

    @patch.object(collectd_plugin.rabbit.RabbitMQStats, 'get_vhosts')
    @patch('collectd_rabbitmq.rabbit.urllib.request.urlopen')
    def test_overview_no_stats(self, mock_urlopen, mock_vhosts):
        """
        Assert that no values are dispatched if no stats are found
        Args:
        :param mock_urlopen: a patched :mod:`rabbit.urllib.request.urlopen`
            object
        :param mock_vhosts: a patched method from a :mod:`CollectdPlugin`
        """
        self.collectd_plugin.rabbit.get_overview_stats = Mock()
        self.collectd_plugin.rabbit.get_overview_stats.return_value = None
        mock_dispatch = MagicMock()
        self.collectd_plugin.dispatch_values = mock_dispatch
        self.collectd_plugin.dispatch_overview()
        self.assertFalse(mock_dispatch.called)


class TestCollectdPluginVhost(BaseTestCollectdPlugin):
    """
    Test the vhosts are generated properly.
    """

    def test_generate_vhost_empty(self):
        """
        Assert empty vhost is set properly.
        """
        vhost = self.collectd_plugin.generate_vhost_name(None)
        self.assertEqual(vhost, "rabbitmq_default")

    def test_generate_vhost_default(self):
        """
        Assert default vhost is set properly.
        """
        vhost = self.collectd_plugin.generate_vhost_name("/")
        self.assertEqual(vhost, "rabbitmq_default")

    def test_generate_vhost_start_slash(self):
        """
        Assert vhost that starts with a '/' is set properly.
        """
        vhost = self.collectd_plugin.generate_vhost_name("/vhost")
        self.assertEqual(vhost, "rabbitmq_slash_vhost")

    def test_generate_vhost_end_slash(self):
        """
        Assert vhost that ends with a '/' is set properly.
        """
        vhost = self.collectd_plugin.generate_vhost_name("vhost/")
        self.assertEqual(vhost, "rabbitmq_vhost_slash")

    def test_generate_vhost(self):
        """
        Assert vhost that contains a slash is set properly.
        """
        vhost = self.collectd_plugin.generate_vhost_name("vho/st")
        self.assertEqual(vhost, "rabbitmq_vho_slash_st")

    def test_generate_vhost_prefix(self):
        """
        Assert vhost is prefixed with that from the config.
        """
        self.collectd_plugin.config.vhost_prefix = 'test_prefix'
        vhost = self.collectd_plugin.generate_vhost_name("vhost")
        self.assertEqual(vhost, "rabbitmq_test_prefix_vhost")
        self.collectd_plugin.config.vhost_prefix = ''


class TestCollectdPluginNodes(BaseTestCollectdPlugin):
    """
    Test that the read methood dispatches the proper data.
    """

    @patch('collectd_rabbitmq.rabbit.urllib.request.urlopen')
    def test_read(self, mock_urlopen):
        """
        Assert node stats are dispatched.
        Args:
        :param mock_urlopen: a patched :mod:`rabbit.urllib.request.urlopen'
            object
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
        dispatch_overview = MagicMock()
        self.collectd_plugin.dispatch_nodes = dispatch_nodes
        self.collectd_plugin.dispatch_queues = dispatch_queues
        self.collectd_plugin.dispatch_exchanges = dispatch_exchanges
        self.collectd_plugin.dispatch_overview = dispatch_overview

        self.collectd_plugin.read()

        self.assertTrue(dispatch_nodes.called)
        self.assertTrue(dispatch_overview.called)
        self.assertTrue(dispatch_queues.called)
        self.assertTrue(dispatch_exchanges.called)

    def test_read_no_vhosts(self):
        """
        Assert only node stats are dispatched if not vhosts.
        """

        dispatch_nodes = MagicMock()
        dispatch_queues = MagicMock()
        dispatch_exchanges = MagicMock()
        dispatch_overview = MagicMock()
        self.collectd_plugin.dispatch_nodes = dispatch_nodes
        self.collectd_plugin.dispatch_queues = dispatch_queues
        self.collectd_plugin.dispatch_exchanges = dispatch_exchanges
        self.collectd_plugin.dispatch_overview = dispatch_overview

        self.collectd_plugin.read()

        self.assertTrue(dispatch_nodes.called)
        self.assertTrue(dispatch_overview.called)
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
    def test_dispatch_throws_exception(self, mock_collectd_values):
        """
        Assert dispath throws an exception.
        Args:
        :param mock_collectd_values: a test object
        """
        mock_values = collectd.Values()
        mock_values.dispatch = MagicMock()
        mock_collectd_values.side_effect = Exception('Collectd exception')
        self.collectd_plugin.dispatch_values((1, 2, 3), 'vhost', 'plugin',
                                             'plugin_instance', 'meteric_type')
        self.assertFalse(mock_values.dispatch.called)

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
