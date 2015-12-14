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

""" Simple test modules rabbit test module """

import json
import urlparse


def get_message_stats_data(name):
    """
    Returns fake message stats data.
    """
    return dict(name=name, vhost="test_vhost",
                message_stats=dict(
                    publish_in=10,
                    publish_in_details=dict(rate=20.0),
                    publish_out=10,
                    publish_out_details=dict(rate=110.0)
                ))


def create_mock_url_repsonse(url):
    """
    Returns mocked stats data based on URL.
    """
    name = urlparse.urlparse(url).path.split('/')[-1:][0]
    data = get_message_stats_data(name)
    return MockURLResponse(json.dumps(data))


def get_node_stats_data():
    """
    Returns fake node stats data.
    """
    return [{
        "disk_free": 20234559488,
        "disk_free_details": {
            "rate": -27852.799999999999
        },
        "disk_free_limit": 50000000,

        "fd_total": 150000,
        "fd_used": 113,
        "fd_used_details": {
            "rate": 0.20000000000000001
        },
        "mem_limit": 2030287257,
        "mem_used": 108663688,
        "mem_used_details": {
            "rate": -28052.799999999999
        },
        "name": "rabbit@fabrik",
        "net_ticktime": 60,
        "os_pid": "29958",
        "partitions": [],
        "proc_total": 1048576,
        "proc_used": 1626,
        "proc_used_details": {
            "rate": -6.2000000000000002
        },
        "processors": 2,
        "rates_mode": "basic",
        "run_queue": 0,
        "sockets_total": 134908,
        "sockets_used": 94,
        "sockets_used_details": {
            "rate": -0.20000000000000001
        },
        "type": "disc",
        "uptime": 65806573
    }]


def create_mock_node_url_repsonse(url=None):
    """
    Returns mocked node stats data based on URL.
    """
    data = get_node_stats_data()
    return MockURLResponse(json.dumps(data))


class MockURLResponse(object):
    """
    A class to mock URL lib response
    based on https://gist.github.com/puffin/966992
    """

    def __init__(self, resp_data, code=200, msg='OK'):
        self.resp_data = resp_data
        self.code = code
        self.msg = msg
        self.headers = {'content-type': 'text/plain; charset=utf-8'}

    def read(self):
        """
        Implements read function by returning base data.
        """
        return self.resp_data

    def getcode(self):
        """
        Returns HTTP code.
        """
        return self.code
