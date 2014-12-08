"""
python plugin for collectd to obtain rabbitmq stats
"""
import collectd
import urllib2
import urllib
import json
import re

RABBIT_API_URL = "http://{host}:{port}/api/"

QUEUE_MESSAGE_STATS = ['messages', 'messages_ready', 'messages_unacknowledged']
QUEUE_STATS = ['memory', 'messages', 'consumers']

MESSAGE_STATS = ['ack', 'publish', 'publish_in', 'publish_out', 'confirm', 'deliver', 'deliver_noack', 'get', 'get_noack', 'deliver_get', 'redeliver', 'return']
MESSAGE_DETAIL = ['avg', 'avg_rate', 'rate', 'sample']
NODE_STATS = ['disk_free', 'disk_free_limit', 'fd_total',\
              'fd_used', 'mem_limit', 'mem_used', \
              'proc_total', 'proc_used', 'processors', 'run_queue',\
              'sockets_total', 'sockets_used'
             ]

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
        collectd.info("%s = %s" %( config_value.key,
                                   len(config_value.values) > 0))
        if config_value.key == 'Username' and len (config_value.values) > 0:
            PLUGIN_CONFIG['username'] = config_value.values[0]
        elif config_value.key == 'Password' and len (config_value.values) > 0:
            PLUGIN_CONFIG['password'] = config_value.values[0]
        elif config_value.key == 'Host' and len (config_value.values) > 0:
            PLUGIN_CONFIG['host'] = config_value.values[0]
        elif config_value.key == 'Port' and len (config_value.values) > 0:
            PLUGIN_CONFIG['port'] = config_value.values[0]
        elif config_value.key == 'Realm' and len (config_value.values) > 0:
            PLUGIN_CONFIG['realm'] = config_value.values[0]
        elif config_value.key == 'Ignore' and len (config_value.values) > 0:
            type_rmq = config_value.values[0]
            PLUGIN_CONFIG['ignore'] = {type_rmq: []}
            for regex in config_value.children:
                PLUGIN_CONFIG['ignore'][type_rmq].append(re.compile(regex.values[0]))

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

def dispatch_message_stats(data, vhost, plugin, plugin_instance):
    if not data:
        collectd.debug("No data for %s in vhost %s" % (plugin, vhost))
        return

    for name in MESSAGE_STATS:
    	dispatch_values((data.get(name,0),), vhost, plugin, plugin_instance, name)

def dispatch_queue_metrics(queue, vhost):
    '''
    Dispatches queue metrics for queue in vhost
    '''

    vhost_name = 'rabbitmq_%s' % (vhost['name'].replace('/', 'default'))
    for name in QUEUE_STATS:
        values= (queue.get(name, 0),)
        dispatch_values(values, vhost_name, 'queues', queue['name'], 'rabbitmq_%s' % name)

    for name in QUEUE_MESSAGE_STATS:
        values= (queue.get(name, 0),)
        dispatch_values(values, vhost_name, 'queues', queue['name'], 'rabbitmq_%s' % name)

	details = queue.get("%s_details" % name, None)
	values = list()
	for detail in MESSAGE_DETAIL:
		values.append (details.get(detail,0))
	dispatch_values(values, vhost_name, 'queues', queue['name'], 'rabbitmq_details', name)

    dispatch_message_stats(queue.get('message_stats',None), vhost_name, 'queues', queue['name'])

def dispatch_exchange_metrics(exchange, vhost):
    '''
    Dispatches exchange metrics for exchange in vhost
    '''
    vhost_name = 'rabbitmq_%s' % vhost['name'].replace('/', 'default')
    dispatch_message_stats(exchange.get('message_stats',None), vhost_name, 'exchanges', exchange['name'])

def dispatch_node_metrics(node):
    '''
    Dispatches node metrics
    '''

    for name in NODE_STATS:
    	dispatch_values((node.get(name,0),), node['name'].split('@')[1], 'rabbitmq', None, name )


def want_to_ignore(type_rmq, name):
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
    base_url = RABBIT_API_URL.format(host = PLUGIN_CONFIG['host'],
                port = PLUGIN_CONFIG['port'])

    auth_handler = urllib2.HTTPBasicAuthHandler()
    auth_handler.add_password(realm = PLUGIN_CONFIG['realm'],
                uri = base_url,
                user = PLUGIN_CONFIG['username'],
                passwd = PLUGIN_CONFIG['password'])
    opener = urllib2.build_opener(auth_handler)
    urllib2.install_opener(opener)

    #First get all the nodes
    for node in get_info("%s/nodes"%(base_url)):
        dispatch_node_metrics(node)

    #Then get all vhost

    for vhost in get_info("%s/vhosts" % (base_url)):

        vhost_name = urllib.quote(vhost['name'],'')
        collectd.debug("Found vhost %s" % vhost['name'])

        for queue in get_info("%s/queues/%s" % (base_url, vhost_name)):
            queue_name = urllib.quote(queue['name'],'')
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
            exchange_name = urllib.quote(exchange['name'],'')
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
