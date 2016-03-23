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

""" Module that contains utility classes and functions """

import re
from urlparse import urlparse


class Auth(object):
    """
    Stores Auth data.
    """

    def __init__(self, username='guest', password='guest', realm=None):
        self.username = username
        self.password = password
        self.realm = realm or "RabbitMQ Management"


class ConnectionInfo(object):
    """
    Stores connection information.
    """

    def __init__(self, host='localhost', port=15672, scheme='http'):
        self.host = host
        self.port = port
        self.scheme = scheme

    @property
    def url(self):
        """
        Returns a url made from scheme, host and port.
        """
        return "{0}://{1}:{2}".format(self.scheme, self.host, self.port)

    @url.setter
    def url(self, value):
        """
        Sets scheme, host, and port from URL.
        """
        parsed_url = urlparse(value)
        self.host = parsed_url.hostname
        self.port = parsed_url.port
        self.scheme = parsed_url.scheme


class Config(object):
    """
    Class that contains configuration data.
    """

    def __init__(self, auth, connection, data_to_ignore=None):
        self.auth = auth
        self.connection = connection
        self.data_to_ignore = dict()

        if data_to_ignore:
            for key, values in data_to_ignore.items():
                self.data_to_ignore[key] = list()
                for value in values:
                    self.data_to_ignore[key].append(re.compile(value))

    def is_ignored(self, stat_type, name):
        """
        Return true if name of type qtype should be ignored.
        """
        if stat_type in self.data_to_ignore:
            for regex in self.data_to_ignore[stat_type]:
                match = regex.match(name)
                if match:
                    return True
        return False


def filter_dictionary(dictionary, keys):
    """
    Returns a dictionary with only keys.
    """
    if not keys:
        return dict()

    if not dictionary:
        return dict()

    return dict((key, dictionary[key]) for key in keys if key in dictionary)


def is_sequence(arg):
    """
    Returns true if arg behaves like a sequence,
    unless it also implements strip, such as strings.
    """

    return (not hasattr(arg, "strip") and
            hasattr(arg, "__getitem__") or
            hasattr(arg, "__iter__"))
