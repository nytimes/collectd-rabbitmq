"""
python plugin for collectd to obtain rabbitmq stats
"""
import collectd
import urllib2
import urllib
import json
import re

RABBIT_API_URL = "http://{host}:{port}/api/"
QUEUE_MESSAGE_RATE_STATS = ['deliver_get', 'get', 'publish', 'redeliver']
QUEUE_RATE_STATS = ['messages', 'messages_ready', 'messages_unacknowledged']
QUEUE_STATS = ['memory', 'consumers']

EXCHANGE_MESSAGE_RATE_STATS=['confirm', 'publish_in','publish_out',\
                             'return_unroutable']

NODE_STATS = ['disk_free', 'disk_free_limit', 'fd_total',\
              'fd_used', 'mem_limit', 'mem_used', \
              'proc_total', 'proc_used', 'processors', 'run_queue',\
              'sockets_total', 'sockets_used'
             ] 

PLUGIN_CONFIG = {
    'username': 'guest',
    'passowrd': 'guest',
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

def dispatch_values(values, plugin_instance, metric_type, metric_name):
    '''
    dispatch metrics to collectd
    '''

    collectd.debug("Dispatching vhost %s %s %s " % (plugin_instance,
        metric_type, metric_name))

    metric = collectd.Values()
    metric.plugin = "rabbitmq"
    metric.plugin_instance = plugin_instance
    metric.type = metric_type
    metric.type_instance = metric_name
    metric.values = values
    metric.dispatch()

def get_details_rate(key, values):
    '''
    returns the value of the details section or 0
    '''

    rate = 0
    details = values.get("%s_details" % key, None)
    if details:
        rate = details.get('rate', 0)

    return rate

def dispatch_queue_metrics(queue, vhost):
    '''
    Dispatches queue metrics for queue in vhost
    '''
    values = list()
    vhost_name = vhost['name'].replace('/', 'default')

    for name in QUEUE_STATS:
        values.append(queue.get(name, 0))

    message_stats = queue.get('message_stats', None)
    if message_stats: 
        for name in QUEUE_MESSAGE_RATE_STATS:
            values.append(message_stats.get(name, 0))
            values.append(get_details_rate(name, message_stats))
    else:
        # if we don't have message stats cause, we just add a bunch
        # default data. In this case it is twice the size of the 
        # message rate stats

        values = values + [0] * 2 * len (QUEUE_MESSAGE_RATE_STATS)
       
    for name in QUEUE_RATE_STATS:
        values.append(queue.get(name, 0))
        values.append(get_details_rate(name, queue))      

    dispatch_values(values, vhost_name, 'queue', queue['name'])
    
def dispatch_exchange_metrics(exchange, vhost):
    '''
    Dispatches exchange metrics for exchange in vhost
    '''
    values = list()
    vhost_name = vhost['name'].replace('/', 'default')
    collectd.info("Exchange %s" % exchange)
    message_stats = exchange.get('message_stats', None)
    if message_stats: 
        for name in EXCHANGE_MESSAGE_RATE_STATS:
            values.append(message_stats.get(name, 0))
            values.append(get_details_rate(name, message_stats))
    else:
        # if we don't have message stats cause, we just add a bunch
        # default data. In this case it is twice the size of the 
        # message rate stats

        values = values + [0] * 2 * len (EXCHANGE_MESSAGE_RATE_STATS)
     

    dispatch_values(values, vhost_name, 'exchange', exchange['name'])    

def dispatch_node_metrics(node):
    '''
    Dispatches node metrics
    '''
    values = list()

    for name in NODE_STATS:
        values.append(node.get(name, 0)) or 0
            
    dispatch_values(values, 'rabbitmq', 'node', node['name'])    


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

    collectd.info("Reading data with input = %s" % (input_data))
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
        #TODO

    #Then get all vhost

    for vhost in get_info("%s/vhosts"%(base_url)):

        vhost_name = urllib.quote(vhost['name'],'')
        collectd.debug("Found vhost %s" % vhost['name'])
        
        
        for queue in get_info("%s/queues/%s" % (base_url, vhost_name)):
            queue_name = urllib.quote(queue['name'],'')
            collectd.info("Found queue %s" % queue['name'])
            if not want_to_ignore("queue", queue_name):
                queue_data = get_info("%s/queues/%s/%s" % (base_url,
                                                           vhost_name, queue_name))
                if queue_data is not None:
                    dispatch_queue_metrics(queue_data, vhost)
                else:
                    collectd.warning("Cannot get data back from %s/%s queue" % (vhost_name, queue_name))

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

