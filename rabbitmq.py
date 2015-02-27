"""
python plugin for collectd to obtain rabbitmq stats
"""
import collectd
import urllib2
import urllib
import json
import re

RABBIT_API_URL = "http://{host}:{port}/api/"

QUEUE_STATS = {
   'consumers': { 'hasMsgStats' : False },
   'memory': {'hasMsgStats': False },
   'messages': { 'hasMsgStats': True },
   'messages_ready': { 'hasMsgStats': True },
   'messages_unacknowledged': { 'hasMsgStats': True }
}

MESSAGE_STATS = 'rate'

QUEUE_MESSAGE_STATS = {
   'ack': { 'hasMsgStats' : True },
   'deliver': {'hasMsgStats': True },
   'deliver_get': { 'hasMsgStats': True },
   'redeliver': { 'hasMsgStats': True }
}

EXCHANGE_MESSAGE_STATS = {
   'publish_in': { 'hasMsgStats' : True },
   'publish_out': {'hasMsgStats': True }
}

NODE_STATS = ['disk_free', 'disk_free_limit', 'fd_total',
              'fd_used', 'mem_limit', 'mem_used',
              'proc_total', 'proc_used', 'processors', 'run_queue',
              'sockets_total', 'sockets_used']

PLUGIN_CONFIG = {
    'username': 'guest',
    'password': 'guest',
    'host': 'localhost',
    'port': 15672,
    'realm': 'RabbitMQ Management'
}


def configure(config_values):
    '''
    Load information from configuration file
    '''

    global PLUGIN_CONFIG
    collectd.info('Configuring RabbitMQ Plugin')
    for config_value in config_values.children:
        collectd.info("%s = %s" % (config_value.key,
                                   len(config_value.values) > 0))
        if len(config_value.values) > 0:
            if config_value.key == 'Username':
                PLUGIN_CONFIG['username'] = config_value.values[0]
            elif config_value.key == 'Password':
                PLUGIN_CONFIG['password'] = config_value.values[0]
            elif config_value.key == 'Host':
                PLUGIN_CONFIG['host'] = config_value.values[0]
            elif config_value.key == 'Port':
                PLUGIN_CONFIG['port'] = config_value.values[0]
            elif config_value.key == 'Realm':
                PLUGIN_CONFIG['realm'] = config_value.values[0]
            elif config_value.key == 'Ignore':
                type_rmq = config_value.values[0]
                PLUGIN_CONFIG['ignore'] = {type_rmq: []}
                for regex in config_value.children:
                    PLUGIN_CONFIG['ignore'][type_rmq].append(
                        re.compile(regex.values[0]))


def init():
    '''
    Initalize connection to rabbitmq
    '''
    collectd.info('Initalizing RabbitMQ Plugin')


def get_info(url):
    '''
    return json object from url
    '''

    try:
        info = urllib2.urlopen(url)
    except urllib2.HTTPError as http_error:
        collectd.error("Error: %s" % (http_error))
        return None
    except urllib2.URLError as url_error:
        collectd.error("Error: %s" % (url_error))
        return None
    return json.load(info)


def dispatch_values(values, host, plugin, plugin_instance, metric_type,
                    type_instance=None):
    '''
    dispatch metrics to collectd
    Args:
      values (tuple): the values to dispatch
      host: (str): the name of the vhost
      plugin (str): the name of the plugin. Should be queue/exchange
      plugin_instance (str): the queue/exchange name
      metric_type: (str): the name of metric
      type_instance: Optional
    '''

    collectd.debug("Dispatching %s %s %s %s %s\n\t%s " % (host, plugin,
                   plugin_instance, metric_type, type_instance, values))

    metric = collectd.Values()
    if host:
        metric.host = host
    metric.plugin = plugin
    if plugin_instance:
        metric.plugin_instance = plugin_instance
    metric.type = metric_type
    if type_instance:
        metric.type_instance = type_instance
    metric.values = values
    metric.dispatch()


def dispatch_message_stats(data, vhost, plugin, plugin_instance, metrics):
    """
    Sends message stats to collectd.
    """
    if not data:
        collectd.debug("No data for %s in vhost %s" % (plugin, vhost))
        return

    for key, value in metrics.iteritems():
        dispatch_values((data.get(key, 0),), vhost, plugin,
                        plugin_instance, key)
        if value['hasMsgStats']:
            details = data.get("%s_details" % key, None)
            if details is None:
                continue
            else:
                dispatch_values((details.get(MESSAGE_STATS, 0),), vhost, plugin,
                                plugin_instance, '%s_rate' % key)


def dispatch_queue_metrics(queue, vhost):
    '''
    Dispatches queue metrics for queue in vhost
    '''

    vhost_name = 'rabbitmq_%s' % (vhost['name'].replace('/', 'default'))
    for key, value in QUEUE_STATS.iteritems():
        dispatch_values((queue.get(key, 0),), vhost_name, 'queues', queue['name'],
                        'rabbitmq_%s' % key)
        if value['hasMsgStats']:
            details = queue.get("%s_details" % key, None)
            if details is None:
                continue
            else:
                dispatch_values((details.get(MESSAGE_STATS, 0),), vhost_name, 'queues', queue['name'],
                               'rabbitmq_%s_rate' % key)

    dispatch_message_stats(queue.get('message_stats', None), vhost_name,
                           'queues', queue['name'], QUEUE_MESSAGE_STATS)


def dispatch_exchange_metrics(exchange, vhost):
    '''
    Dispatches exchange metrics for exchange in vhost
    '''
    vhost_name = 'rabbitmq_%s' % vhost['name'].replace('/', 'default')
    dispatch_message_stats(exchange.get('message_stats', None), vhost_name,
                           'exchanges', exchange['name'], EXCHANGE_MESSAGE_STATS)


def dispatch_node_metrics(node):
    '''
    Dispatches node metrics
    '''

    for name in NODE_STATS:
        dispatch_values((node.get(name, 0),), node['name'].split('@')[1],
                        'rabbitmq', None, name)


def want_to_ignore(type_rmq, name):
    """
    Applies ignore regex to the queue.
    """
    if 'ignore' in PLUGIN_CONFIG:
        if type_rmq in PLUGIN_CONFIG['ignore']:
            for regex in PLUGIN_CONFIG['ignore'][type_rmq]:
                match = regex.match(name)
                if match:
                    return True
    return False


def read(input_data=None):
    '''
    reads all metrics from rabbitmq
    '''

    collectd.debug("Reading data with input = %s" % (input_data))
    base_url = RABBIT_API_URL.format(host=PLUGIN_CONFIG['host'],
                                     port=PLUGIN_CONFIG['port'])

    auth_handler = urllib2.HTTPBasicAuthHandler()
    auth_handler.add_password(realm=PLUGIN_CONFIG['realm'],
                              uri=base_url,
                              user=PLUGIN_CONFIG['username'],
                              passwd=PLUGIN_CONFIG['password'])
    opener = urllib2.build_opener(auth_handler)
    urllib2.install_opener(opener)

    #First get all the nodes
    for node in get_info("%s/nodes" % (base_url)):
        dispatch_node_metrics(node)

    #Then get all vhost

    for vhost in get_info("%s/vhosts" % (base_url)):

        vhost_name = urllib.quote(vhost['name'], '')
        collectd.debug("Found vhost %s" % vhost['name'])

        for queue in get_info("%s/queues/%s" % (base_url, vhost_name)):
            queue_name = urllib.quote(queue['name'], '')
            collectd.debug("Found queue %s" % queue['name'])
            if not want_to_ignore("queue", queue_name):
                queue_data = get_info("%s/queues/%s/%s" % (base_url,
                                                           vhost_name,
                                                           queue_name))
                if queue_data is not None:
                    dispatch_queue_metrics(queue_data, vhost)
                else:
                    collectd.warning("Cannot get data back from %s/%s queue" %
                                    (vhost_name, queue_name))

        for exchange in get_info("%s/exchanges/%s" % (base_url,
                                 vhost_name)):
            exchange_name = urllib.quote(exchange['name'], '')
            if exchange_name:
                collectd.debug("Found exchange %s" % exchange['name'])
                exchange_data = get_info("%s/exchanges/%s/%s" % (
                                         base_url, vhost_name, exchange_name))
                dispatch_exchange_metrics(exchange_data, vhost)


def shutdown():
    '''
    Shutdown connection to rabbitmq
    '''

    collectd.info('RabbitMQ plugin shutting down')

# Register callbacks
collectd.register_config(configure)
collectd.register_init(init)
collectd.register_read(read)
#collectd.register_write(write)
collectd.register_shutdown(shutdown)
