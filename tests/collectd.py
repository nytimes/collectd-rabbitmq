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

"""
Mock collected object for testing
Based on:
https://github.com/rampage644/blueflood-python/blob/master/test/collectd.py
"""
import logging

# pylint: disable=R0913
# pylint: disable=R0902
# pylint: disable=R0903
# pylint: disable=W0613


class Config(object):
    """
    Fake config oebject.
    """

    def __init__(self, key, values, children=None):
        # also Config instance
        self.parent = None
        # key string
        self.key = key
        # tuple of Config instances, mostly empty
        self.children = children or list()
        for child in self.children:
            child.parent = self
        # tuple of strings, mostly one value
        self.values = values

    def __repr__(self):
        if self.parent:
            prefix = '\n\t'
        else:
            prefix = ''

        return "{0}Key: {1}, Value: {2}, Parent: {3}, Children: {4}".format(
            prefix, self.key, self.values, hex(id(self.parent)), self.children)


class Values(object):
    """
    Fake value object build for testing.
    Attempts to implement:
        https://collectd.org/documentation/manpages/collectd-python.5.shtml
    """

    def __init__(self, host='', plugin='', plugin_instance='', value_type='',
                 type_instance='', time=0, values=None, interval=0):
        self.host = host
        self.plugin = plugin
        self.plugin_instance = plugin_instance
        self.time = time
        self.value_type = value_type
        self.type_instance = type_instance
        self.values = values or tuple()
        self.interval = interval
        self.meta = None

    def dispatch(self, value_type=None, values=None, plugin_instance=None,
                 type_instance=None, plugin=None, host=None, time=None,
                 interval=None):
        """
        Fake dispatch method, does nothing.
        """
        pass

    def write(self, destination=None, value_type=None, values=None,
              plugin_instance=None, type_instance=None, plugin=None, host=None,
              time=None, interval=None):
        """
        Fake dispatch method, does nothing.
        """
        pass


def register_write(func, data):
    """
    Fake write function.
    """
    pass


def register_config(func):
    """
    Fake config function.
    """
    pass


def register_init(func):
    """
    Fake init function.
    """
    pass


def register_read(func):
    """
    Fake read function.
    """
    pass


def register_shutdown(func):
    """
    Fake shutdown function.
    """
    pass


def info(msg):
    """
    Logs as info level.
    """
    logging.info(msg)


def warning(msg):
    """
    Logs as warning level.
    """
    logging.warning(msg)


def error(msg):
    """
    Logs as error level.
    """
    logging.error(msg)


def debug(msg):
    """
    Logs as error level.
    """
    logging.debug(msg)
