#!/usr/bin/env python
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


from random import random
from time import sleep

from datetime import datetime

import pika


def main():

    credentials = pika.PlainCredentials('collectd', 'collectd')
    parameters = pika.ConnectionParameters('localhost',
                                           5672,
                                           'collectd',
                                           credentials)
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()
    counter = 0
    while (counter < 10000):
        message = 'Message {} created at {}'.format(datetime.now, counter)

        channel.basic_publish(exchange='test_topic_exchange',
                              routing_key='test',
                              body=message)
        counter = counter + 1
        sleep(random())

    connection.close()

if __name__ == "__main__":
    import sys
    sys.exit(main())
