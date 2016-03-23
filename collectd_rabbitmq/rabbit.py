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
python plugin for collectd to obtain rabbitmq stats
"""

import collectd
import json
import urllib
import urllib2


class RabbitMQStats(object):
    """
        Class to interface with the RabbitMQ API.
    """

    def __init__(self, config):
        self.config = config
        self.api = "{0}/api".format(self.config.connection.url)

    @staticmethod
    def get_names(items):
        """
        Return URL encoded names.
        """
        collectd.debug("Getting names for %s" % items)
        names = list()
        for item in items:
            name = item.get('name', None)
            if name:
                name = urllib.quote(name, '')
                names.append(name)
        return names

    def get_info(self, *args):
        """
        return JSON object from URL.
        """

        url = "{0}/{1}".format(self.api, '/'.join(args))
        collectd.debug("Getting info for %s" % url)

        auth_handler = urllib2.HTTPBasicAuthHandler()
        auth_handler.add_password(realm=self.config.auth.realm,
                                  uri=self.api,
                                  user=self.config.auth.username,
                                  passwd=self.config.auth.password)
        opener = urllib2.build_opener(auth_handler)
        urllib2.install_opener(opener)

        try:
            info = urllib2.urlopen(url)
        except urllib2.HTTPError as http_error:
            collectd.error("HTTP Error: %s" % http_error)
            return None
        except urllib2.URLError as url_error:
            collectd.error("URL Error: %s" % url_error)
            return None
        except ValueError as value_error:
            collectd.error("Value Error: %s" % value_error)
            return None

        try:
            return_value = json.load(info)
        except ValueError as err:
            collectd.error("ValueError parsing JSON from %s: %s" % (url, err))
            return_value = None
        except TypeError as err:
            collectd.error("TypeError parsing JSON from %s: %s" % (url, err))
            return_value = None
        return return_value

    def get_nodes(self):
        """
        Return a list of nodes.
        """
        return self.get_info("nodes") or list()
    nodes = property(get_nodes)

    # Vhosts
    def get_vhosts(self):
        """
        Returns a list of vhosts.
        """
        collectd.debug("Getting a list of vhosts")
        return self.get_info("vhosts") or list()

    def get_vhost_names(self):
        """
        Returns a list of vhost names.
        """
        collectd.debug("Getting vhost names")
        all_vhosts = self.get_vhosts()
        return self.get_names(all_vhosts) or list()
    vhost_names = property(get_vhost_names)

    # Exchanges
    def get_exchanges(self, vhost_name=None):
        """
        Returns raw exchange data.
        """
        collectd.debug("Getting exchanges for %s" % vhost_name)
        return self.get_info("exchanges", vhost_name)

    def get_exchange_names(self, vhost_name=None):
        """
        Returns a list of all exchange names.
        """
        collectd.debug("Getting exchange names for %s" % vhost_name)
        all_exchanges = self.get_exchanges(vhost_name)
        return self.get_names(all_exchanges)

    def get_exchange_stats(self, exchange_name=None, vhost_name=None):
        """
        Returns a dictionary of stats for exchange_name.
        """
        collectd.debug("Getting exchange stats for %s in %s" %
                       (exchange_name, vhost_name))

        return self.get_stats('exchange', exchange_name, vhost_name)

    # Queues
    def get_queues(self, vhost_name=None):
        """
        Returns raw queue data.
        """
        collectd.debug("Getting queues for %s" % vhost_name)
        return self.get_info("queues", vhost_name)

    def get_queue_names(self, vhost_name=None):
        """
        Returns a list of all queue names.
        """
        collectd.debug("Getting queue names for %s" % vhost_name)
        all_queues = self.get_queues(vhost_name)
        return self.get_names(all_queues)

    def get_queue_stats(self, queue_name=None, vhost_name=None):
        """
        Returns a dictionary of stats for queue_name.
        """
        return self.get_stats('queue', queue_name, vhost_name)

    def get_stats(self, stat_type, stat_name, vhost_name):
        """
        Returns a dictionary of stats.
        """
        collectd.debug("Getting stats for %s %s%s in %s" %
                       (stat_name or 'all',
                        stat_type,
                        's' if not stat_name else '',
                        vhost_name))

        if stat_type not in('exchange', 'queue'):
            raise ValueError("Unsupported stat type {0}".format(stat_type))
        stat_name_func = getattr(self, 'get_{0}_names'.format(stat_type))
        if not vhost_name:
            vhosts = self.get_vhost_names()
        else:
            vhosts = [vhost_name]

        stats = dict()
        for vhost in vhosts:
            if not stat_name:
                names = stat_name_func(vhost)
            else:
                names = [stat_name]
            for name in names:
                if not self.config.is_ignored(stat_type, name):
                    stats[name] = self.get_info("{0}s".format(stat_type),
                                                vhost,
                                                name)
        return stats
