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

"""
This module controls the interactions with collectd
"""

import collectd
import re

from collectd_rabbitmq import rabbit
from collectd_rabbitmq import utils


CONFIG = None
AUTH = None
CONN = None
PLUGIN = None


def configure(config_values):
    """
    Converts a collectd configuration into rabbitmq configuration.
    """

    collectd.debug('Configuring RabbitMQ Plugin')
    data_to_ignore = dict()

    scheme = 'http'
    for config_value in config_values.children:
        collectd.debug("%s = %s" % (config_value.key, config_value.values))
        if len(config_value.values) > 0:
            if config_value.key == 'Username':
                username = config_value.values[0]
            elif config_value.key == 'Password':
                password = config_value.values[0]
            elif config_value.key == 'Host':
                host = config_value.values[0]
            elif config_value.key == 'Port':
                port = config_value.values[0]
            elif config_value.key == 'Realm':
                realm = config_value.values[0]
            elif config_value.key == 'Scheme':
                scheme = config_value.values[0]
            elif config_value.key == 'Ignore':
                type_rmq = config_value.values[0]
                data_to_ignore[type_rmq] = list()
                for regex in config_value.children:
                    data_to_ignore[type_rmq].append(regex.values[0])

    global AUTH  # pylint: disable=W0603
    global CONN  # pylint: disable=W0603
    global CONFIG  # pylint: disable=W0603

    AUTH = utils.Auth(username, password, realm)
    CONN = utils.ConnectionInfo(host, port, scheme)
    CONFIG = utils.Config(AUTH, CONN, data_to_ignore)


def init():
    """
    Creates the logs stash plugin object.
    """
    global PLUGIN  # pylint: disable=W0603
    PLUGIN = CollectdPlugin()


def read():
    """
    Reads and dispatches data.
    """
    collectd.debug("Reading data from rabbit and dispatching")
    if not PLUGIN:
        collectd.warning('Plugin not ready')
        return
    PLUGIN.read()


class CollectdPlugin(object):
    """
    Controls interaction between rabbitmq stats and collectd.
    """
    message_stats = ['ack', 'publish', 'publish_in', 'publish_out', 'confirm',
                     'deliver', 'deliver_noack', 'get', 'get_noack',
                     'deliver_get', 'redeliver', 'return']
    message_details = ['avg', 'avg_rate', 'rate', 'sample']
    queue_stats = ['messages', 'messages_ready', 'messages_unacknowledged']
    node_stats = ['disk_free', 'disk_free_limit', 'fd_total',
                  'fd_used', 'mem_limit', 'mem_used',
                  'proc_total', 'proc_used', 'processors', 'run_queue',
                  'sockets_total', 'sockets_used']

    def __init__(self):
        self.rabbit = rabbit.RabbitMQStats(CONFIG)

    def read(self):
        """
        Dispatches values to collectd.
        """
        self.dispatch_nodes()
        for vhost_name in self.rabbit.vhost_names:
            self.dispatch_exchanges(vhost_name)
            self.dispatch_queues(vhost_name)

    @staticmethod
    def generate_vhost_name(name):
        """
        Generate a "normalized" vhost name without /.
        """
        if not name or name == '/':
            name = 'default'
        else:
            name = re.sub(r'^/', 'slash_', name)
            name = re.sub(r'/$', '_slash', name)
            name = re.sub(r'/', '_slash_', name)
        return 'rabbitmq_%s' % name

    def dispatch_message_stats(self, data, vhost, plugin, plugin_instance):
        """
        Sends message stats to collectd.
        """
        if not data:
            collectd.debug("No data for %s in vhost %s" % (plugin, vhost))
            return

        vhost = self.generate_vhost_name(vhost)

        for name in self.message_stats:
            if 'message_stats' not in data:
                return
            collectd.debug("Dispatching stat %s for %s in %s" %
                           (name, plugin_instance, vhost))

            value = data['message_stats'].get(name, 0)
            self.dispatch_values(value, vhost, plugin, plugin_instance, name)

            details = data['message_stats'].get("%s_details" % name, None)
            if not details:
                continue
            for detail in self.message_details:
                self.dispatch_values(
                    (details.get(detail, 0)), vhost, plugin, plugin_instance,
                    "%s_details" % name, detail)

    def dispatch_nodes(self):
        """
        Dispatches nodes stats.
        """
        stats = self.rabbit.get_nodes()
        for node in stats:
            name = node['name'].split('@')[1]
            collectd.debug("Getting stats for %s node" % name)
            for stat_name in self.node_stats:
                value = node.get(stat_name, 0)
                self.dispatch_values(value, name, 'rabbitmq', None, stat_name)

                details = node.get("%s_details" % stat_name, None)
                if not details:
                    continue
                for detail in self.message_details:
                    value = details.get(detail, 0)
                    self.dispatch_values(value, name, 'rabbitmq', None,
                                         "%s_details" % stat_name, detail)

    def dispatch_queue_stats(self, data, vhost, plugin, plugin_instance):
        """
        Sends queue stats to collectd.
        """
        if not data:
            collectd.debug("No data for %s in vhost %s" % (plugin, vhost))
            return

        vhost = self.generate_vhost_name(vhost)

        for name in self.queue_stats:
            if name not in data:
                return
            collectd.debug("Dispatching stat %s for %s in %s" %
                           (name, plugin_instance, vhost))

            value = data.get(name, 0)
            self.dispatch_values(value, vhost, plugin, plugin_instance, name)

    def dispatch_exchanges(self, vhost_name):
        """
        Dispatches exchange data for vhost_name.
        """
        collectd.debug("Dispatching exchange data for {0}".format(vhost_name))
        stats = self.rabbit.get_exchange_stats(vhost_name=vhost_name)
        for exchange_name, value in stats.iteritems():
            self.dispatch_message_stats(value, vhost_name, 'exchanges',
                                        exchange_name)

    def dispatch_queues(self, vhost_name):
        """
        Dispatches queue data for vhost_name.
        """
        collectd.debug("Dispatching queue data for {0}".format(vhost_name))
        stats = self.rabbit.get_queue_stats(vhost_name=vhost_name)
        for queue_name, value in stats.iteritems():
            self.dispatch_message_stats(value, vhost_name, 'queues',
                                        queue_name)
            self.dispatch_queue_stats(value, vhost_name, 'queues',
                                      queue_name)

    # pylint: disable=R0913
    @staticmethod
    def dispatch_values(values, host, plugin, plugin_instance,
                        metric_type, type_instance=None):
        """
        Dispatch metrics to collectd.

        :param values (tuple or list): The values to dispatch. It will be
                                       coerced into a list.
        :param host: (str): The name of the vhost.
        :param plugin (str): The name of the plugin. Should be
                             queue/exchange.
        :param plugin_instance (str): The queue/exchange name.
        :param metric_type: (str): The name of metric.
        :param type_instance: Optional.

        """
        path = "{0}.{1}.{2}.{3}.{4}".format(host, plugin,
                                            plugin_instance,
                                            metric_type, type_instance)

        collectd.debug("Dispatching %s values: %s" % (path, values))

        metric = collectd.Values()
        metric.host = host

        metric.plugin = plugin

        if plugin_instance:
            metric.plugin_instance = plugin_instance

        metric.type = metric_type

        if type_instance:
            metric.type_instance = type_instance

        if utils.is_sequence(values):
            metric.values = values
        else:
            metric.values = [values]
        # Tiny hack to fix bug with write_http plugin in Collectd
        # versions < 5.5.
        # See https://github.com/phobos182/collectd-elasticsearch/issues/15
        # for details
        metric.meta = {'0': True}
        metric.dispatch()


# Register callbacks
collectd.register_config(configure)
collectd.register_init(init)
collectd.register_read(read)
