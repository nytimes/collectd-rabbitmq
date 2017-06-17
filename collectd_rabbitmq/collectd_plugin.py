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
import urllib

from collectd_rabbitmq import rabbit
from collectd_rabbitmq import utils

CONFIGS = []
INSTANCES = []
plugin_name = 'rabbitmq'

def configure(config_values):
    """
    Converts a collectd configuration into rabbitmq configuration.
    """

    collectd.debug('Configuring RabbitMQ Plugin')
    data_to_ignore = dict()
    scheme = 'http'
    vhost_prefix = None

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
            elif config_value.key == 'VHostPrefix':
                vhost_prefix = config_value.values[0]
            elif config_value.key == 'Ignore':
                type_rmq = config_value.values[0]
                data_to_ignore[type_rmq] = list()
                for regex in config_value.children:
                    data_to_ignore[type_rmq].append(regex.values[0])

    global CONFIGS  # pylint: disable=W0603

    auth = utils.Auth(username, password, realm)
    conn = utils.ConnectionInfo(host, port, scheme)
    config = utils.Config(auth, conn, data_to_ignore, vhost_prefix)
    CONFIGS.append(config)


def init():
    """
    Creates the logs stash plugin object.
    """
    for config in CONFIGS:
        INSTANCES.append(CollectdPlugin(config))


def read():
    """
    Reads and dispatches data.
    """
    collectd.debug("Reading data from rabbit and dispatching")
    if not INSTANCES:
        collectd.warning('Plugin not ready')
        return
    for instance in INSTANCES:
        instance.read()


class CollectdPlugin(object):
    """
    Controls interaction between rabbitmq stats and collectd.
    """
    message_stats = ['ack', 'publish', 'publish_in', 'publish_out', 'confirm',
                     'deliver', 'deliver_noack', 'get', 'get_noack',
                     'deliver_get', 'redeliver', 'return']
    message_details = ['avg', 'avg_rate', 'rate', 'sample']
    queue_stats = ['consumers', 'messages', 'messages_ready',
                   'messages_unacknowledged']
    node_stats = ['disk_free', 'disk_free_limit', 'fd_total',
                  'fd_used', 'mem_limit', 'mem_used',
                  'proc_total', 'proc_used', 'processors', 'run_queue',
                  'sockets_total', 'sockets_used']
    overview_stats = {'object_totals': ['consumers', 'queues', 'exchanges',
                                        'connections', 'channels'],
                      'message_stats': ['publish', 'ack', 'deliver_get',
                                        'confirm', 'redeliver', 'deliver',
                                        'deliver_no_ack'],
                      'queue_totals': ['messages', 'messages_ready',
                                       'messages_unacknowledged']}
    overview_details = ['rate']

    def __init__(self, config):
        self.config = config
        self.rabbit = rabbit.RabbitMQStats(self.config)

    def read(self):
        """
        Dispatches values to collectd.
        """
        self.dispatch_nodes()
        self.dispatch_overview()
        for vhost_name in self.rabbit.vhost_names:
            self.dispatch_exchanges(vhost_name)
            self.dispatch_queues(vhost_name)

    def generate_vhost_name(self, name):
        """
        Generate a "normalized" vhost name without / (or escaped /).
        """
        if name:
            name = urllib.unquote(name)

        if not name or name == '/':
            name = 'default'
        else:
            name = re.sub(r'^/', 'slash_', name)
            name = re.sub(r'/$', '_slash', name)
            name = re.sub(r'/', '_slash_', name)

        vhost_prefix = ''
        if self.config.vhost_prefix:
            vhost_prefix = '%s_' % self.config.vhost_prefix
        return '%s%s' % (vhost_prefix, name)

    def dispatch_message_stats(self, data, vhost, message_source, message_source_name):
        """
        Sends message stats to collectd.
        """
        if not data:
            collectd.debug("No data for %s in vhost %s" % (message_source, vhost))
            return

        vhost = self.generate_vhost_name(vhost)

        for name in self.message_stats:
            if 'message_stats' not in data:
                return
            collectd.debug("Dispatching stat %s for %s in %s" % (name, message_source_name, vhost))

            value = data['message_stats'].get(name, 0)
            self.dispatch_values(values=value,
                                 metric_type=name,
                                 plugin_instance='vhost-' + vhost + '-' + message_source + '-' + message_source_name)

            details = data['message_stats'].get("%s_details" % name, None)
            if not details:
                continue
            for detail in self.message_details:
                self.dispatch_values(values=details.get(detail, 0),
                                     metric_type=name,
                                     plugin_instance='vhost-' + vhost + '-' + message_source + '-' + message_source_name + "-details")

    def dispatch_nodes(self):
        """
        Dispatches nodes stats.
        """
        name = self.generate_vhost_name('')
        node_names = []
        stats = self.rabbit.get_nodes()
        collectd.debug("Node stats for {} {}".format(name, stats))
        for node in stats:
            node_name = node['name'].split('@')[1]
            if node_name in node_names:
                # If we ahve already seen this node_name we
                node_name = '%s%s' % (node_name, len(node_names))
            node_names.append(node_name)
            collectd.debug("Getting stats for %s node" % node_names)
            for stat_name in self.node_stats:
                value = node.get(stat_name, 0)
                self.dispatch_values(values=value,
                                     metric_type=stat_name,
                                     plugin_instance='vhost-' + name + '-node-' + node_name)

                details = node.get("%s_details" % stat_name, None)
                if not details:
                    continue
                for detail in self.message_details:
                    value = details.get(detail, 0)
                    self.dispatch_values(values=value,
                                         metric_type="%s_details" % stat_name,
                                         plugin_instance='vhost-' + name + '-node-' + node_name + '-details',
                                         type_instance=detail)

    def dispatch_overview(self):
        """
        Dispatches cluster overview stats.
        """
        stats = self.rabbit.get_overview_stats()
        if stats is None:
            return None

        cluster_name = stats.get('cluster_name', 'rabbitmq')
        prefixed_cluster_name = "cluster_%s" % cluster_name
        prefixed_cluster_name = re.sub(r'@', '_at_', prefixed_cluster_name)

        for subtree_name, keys in self.overview_stats.items():
            subtree = stats.get(subtree_name, {})
            for stat_name in keys:
                type_name = stat_name
                type_name = type_name.replace('no_ack', 'noack')
                stats_re = re.compile(r"""
                    ^(connections|messages|consumers|queues|exchanges|channels)
                    """, re.X)
                if re.match(stats_re, stat_name) is not None:
                    type_name = "rabbitmq_%s" % stat_name

                value = subtree.get(stat_name, 0)
                self.dispatch_values(values=value,
                                     plugin_instance='overview-' + prefixed_cluster_name,
                                     metric_type=type_name)

                details = subtree.get("%s_details" % stat_name, None)
                if not details:
                    continue
                detail_values = []
                for detail in self.message_details:
                    detail_values.append(details.get(detail, 0))

                collectd.debug("Dispatching overview stat {} for {}".format(stat_name, prefixed_cluster_name))

                self.dispatch_values(values=detail_values,
                                     metric_type='rabbitmq_details',
                                     plugin_instance='overview-' + prefixed_cluster_name + '-details',
                                     type_instance=type_name)

    def dispatch_queue_stats(self, data, vhost, message_source, message_source_name):
        """
        Sends queue stats to collectd.
        """
        if not data:
            collectd.debug("No data for %s in vhost %s" % (message_source, vhost))
            return

        vhost = self.generate_vhost_name(vhost)
        for name in self.queue_stats:
            if name not in data:
                collectd.debug("Stat ({}) not found in data.".format(name))
                continue
            collectd.debug("Dispatching stat %s for %s in %s" % (name, message_source_name, vhost))

            value = data.get(name, 0)
            self.dispatch_values(values=value,
                                 plugin_instance='vhost-' + vhost + '-' + message_source + '-' + message_source_name,
                                 metric_type=name)

    def dispatch_exchanges(self, vhost_name):
        """
        Dispatches exchange data for vhost_name.
        """
        collectd.debug("Dispatching exchange data for {0}".format(vhost_name))
        stats = self.rabbit.get_exchange_stats(vhost_name=vhost_name)
        for exchange_name, value in stats.iteritems():
            self.dispatch_message_stats(data=value,
                                        vhost=vhost_name,
                                        message_source='exchanges',
                                        message_source_name=exchange_name)

    def dispatch_queues(self, vhost_name):
        """
        Dispatches queue data for vhost_name.
        """
        collectd.debug("Dispatching queue data for {0}".format(vhost_name))
        stats = self.rabbit.get_queue_stats(vhost_name=vhost_name)
        for queue_name, value in stats.iteritems():
            self.dispatch_message_stats(data=value,
                                        vhost=vhost_name,
                                        message_source='queues',
                                        message_source_name=queue_name)
            self.dispatch_queue_stats(data=value,
                                      vhost=vhost_name,
                                      message_source='queues',
                                      message_source_name=queue_name)

    # pylint: disable=R0913
    @staticmethod
    def dispatch_values(values,
                        metric_type,
                        plugin_instance='',
                        type_instance=''):
        """
        Dispatch metrics to collectd.

        :param values (tuple or list): The values to dispatch. It will be
                                       coerced into a list.
        :param metric_type: (str):     The type of the metric.
        :param plugin_instance (str):  Optional, overview, queues, vhost statistics
        :param type_instance (str):    Optional, type of a certain metric.

        """
        collectd.debug("Dispatching metric: values = %s | \
                                            metric_type = %s | \
                                            plugin_instance = %s | \
                                            type_instance = %s" % \
                       (values, metric_type, plugin_instance, type_instance))

        try:
            metric = collectd.Values()
            metric.plugin = plugin_name
            metric.type = metric_type
            metric.plugin_instance = plugin_instance
            metric.type_instance = type_instance
            metric.values = values if utils.is_sequence(values) else [values]
            # Tiny hack to fix bug with write_http plugin in Collectd versions < 5.5.
            # See https://github.com/phobos182/collectd-elasticsearch/issues/15
            metric.meta = {'0': True}
            metric.dispatch()
        except Exception as ex:
            collectd.warning("Failed to dispatch: values = %s | metric_type = %s | plugin_instance = %s | \
type_instance = %s | Exception = %s" % (values, metric_type, plugin_instance, type_instance, ex))

# Register callbacks
collectd.register_config(configure)
collectd.register_init(init)
collectd.register_read(read)
