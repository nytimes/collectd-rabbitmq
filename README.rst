===============================
collectd-rabbitmq
===============================

.. image:: https://img.shields.io/pypi/v/collectd-rabbitmq.svg
        :target: https://pypi.python.org/pypi/collectd-rabbitmq

.. image:: https://api.travis-ci.org/NYTimes/collectd-rabbitmq.svg
        :target: https://travis-ci.org/NYTimes/collectd-rabbitmq

.. image:: https://readthedocs.org/projects/collectd-rabbitmq/badge/?version=latest
        :target: https://readthedocs.org/projects/collectd-rabbitmq/?badge=latest
        :alt: Documentation Status


"A collected plugin, written in python, to collect statistics from RabbitMQ."

* Free software: Apache license
* Documentation: https://collectd-rabbitmq.readthedocs.org.
* For the older single file version see https://github.com/NYTimes/collectd-rabbitmq/tree/0.1.1

Features
--------

* Support queue, exchange, and node stats,


Configuration
-------------

This plugin supports a small amount of configuration options:

* `Username`: The rabbitmq user. Defaults to `guest`
* `Password`: The rabbitmq user password. Defaults to `guest`
* `Realm`: The http realm for authentication. Defaults to `RabbitMQ Management`
* `Scheme`: The protocol that the rabbitmq management API is running on. Defaults to `http`
* `Host`: The hostname that the rabbitmq server running on. Defaults to `localhost`
* `Port`: The port that the rabbitmq server is listening on. Defaults to `15672`
* `Ignore`: The queue to ignore, matching by Regex.  See example.

See `this example`_ for further details.
    .. _this example: config/collectd.conf

Nodes
-----

For each node the following statistics are gathered:

* disk_free_limit
* fd_total
* fd_used
* mem_limit
* mem_used
* proc_total
* proc_used
* processors
* run_queue
* sockets_total
* sockets_used

Queues
-------

For each queue in each vhost the following statistics are gathered:
_NOTE_: The `/` vhost name is sent as `default`

* message_stats
    * deliver_get
    * deliver_get_details
        * rate
    * get
    * get_details
        * rate
    * publish
    * publish_details
        * rate
    * redeliver
    * redeliver_details
        * rate
* messages
* messages_details
    * rate
* messages_ready
* messages_ready_details
    * rate
* messages_unacknowledged
* messages_unacknowledged_details
  * rate
* memory
* consumers

Exchanges
----------

For each exchange in each vhost the following statistics are gathered:
_NOTE_: The `/` vhost name is sent as `default`

* disk_free
* disk_free_limit
* fd_total
* fd_used
* mem_limit
* mem_used
* proc_total
* proc_used
* processors
* run_queue
* sockets_total
* sockets_used

Credits
---------

This package was created with Cookiecutter_ and the `cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
