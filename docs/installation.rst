============
Installation
============

At the command line::

    $ easy_install collectd-rabbitmq

Or, if you have virtualenvwrapper installed::

    $ mkvirtualenv collectd-rabbitmq
    $ pip install collectd-rabbitmq

This plugins requires that the Collectd type database be updated. Each of these statistics have their own custom enter in collectd's type database. To add these types defined in :download:`this example <../config/types.db.custom>` run the following command::

    $ cat config/types.db.custom >> /usr/share/collectd/types.db
