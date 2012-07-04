#!/usr/bin/env python
"""
GDS Burp Suite API

* Burp and Burp Suite are trademarks of PortSwigger Ltd.
Copyright 2008 PortSwigger Ltd. All rights reserved.
See http://portswigger.net for license terms.

Copyright (c) 2009-2010 Marcin Wielgoszewski <marcinw@gdssecurity.com>
Gotham Digital Science

This file is part of GDS Burp API.

GDS Burp API is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

GDS Burp API is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with GDS Burp API.  If not, see <http://www.gnu.org/licenses/>
"""
from urlparse import urljoin, urlparse
from utils import parse_headers, parse_parameters
import copy
import logging

LOGGER = logging.getLogger(__name__)


class Burp(object):
    """
    This is our main Burp class that contains a single request and an
    optional response.  This data was gathered from parsing our Burp
    log file, which may have been generated by any of the Burp Suite tools.
    """
    def __init__(self, data=None, index=0):
        """
        Create a new Burp request/response object from a parsed Burp log
        file.
        """
        self.index = index
        self.host = None
        self.ip_address = None
        self.time = None
        self.request = {}
        self.response = {}
        self.url = None
        self.parameters = {}
        self.replayed = []

        if hasattr(data, 'items'):
            self.__process(data)

        LOGGER.debug("Burp object created: %d" % self.index)

    def __process(self, data):
        """
        Process data to fill properties of Burp object.
        """
        self.host = data.get('host', None)
        self.ip_address = data.get('ip_address', None)
        self.time = data.get('time', None)

        self.request.update({
             'method': data['request'].get('method'),
             'path': data['request'].get('path'),
             'version': data['request'].get('version'),
             'headers': parse_headers(data['request'].get('headers')),
             'body': data['request'].get('body', ""),
            })

        self.response.update({
             'version': data['response'].get('version'),
             'status': int(data['response'].get('status', 0)),
             'reason': data['response'].get('reason'),
             'headers': parse_headers(data['response'].get('headers')),
             'body': data['response'].get('body', ""),
            })

        self.url = urlparse(urljoin(self.host, self.request.get('path')))
        self.parameters = parse_parameters(self)

        # During parsing, we may parse an extra CRLF or two.  So to account
        # for that, we'll just grab the actual content-length from the
        # HTTP header and slice the request/response body appropriately.
        if self.get_response_header('Content-Length'):
            content_length = int(self.get_response_header('Content-Length'))
            if len(self) != content_length:
                #LOGGER.debug("Response content-length differs by %d" % (len(self) - content_length))
                self.response['body'] = self.response['body'][:content_length]

        if self.get_request_header('Content-Length'):
            content_length = int(self.get_request_header('Content-Length'))
            if len(self.get_request_body()) != content_length and 'amf' not in \
                self.get_request_header('Content-Type'):
                #LOGGER.debug("Request content-length differs by %d" % (len(self.get_request_body()) - content_length))
                self.request['body'] = self.request['body'][:content_length]

    def __len__(self):
        """
        @return: Content-Length of response body.
        @rtype: int
        """
        return len(self.get_response_body())

    def __repr__(self):
        return "<Burp %d>" % self.index

    def get_request_body(self):
        """
        Return request body.

        @rtype: string
        """
        return self.request['body']

    def get_request_method(self):
        """
        Return request method.

        @rtype: string
        """
        return self.request['method']

    def get_request_version(self):
        """
        Return request version.

        @rtype: string
        """
        return self.request['version']

    def get_request_header(self, name):
        """
        Return request header.

        @param name: Name of the request header.
        @return: If header exists returns its value, else an empty string.
        @rtype: string
        """
        return self.request['headers'].get(name.title(), '')

    def get_request_headers(self):
        """
        Return request headers.

        @rtype: dict
        """
        return self.request['headers']

    def get_request_path(self):
        """
        Return request path.

        @rtype: string
        """
        return self.request['path']

    def get_response_version(self):
        """
        Return response version.

        @rtype: string
        """
        return self.response['version']

    def get_response_status(self):
        """
        Return response status.

        @rtype: string
        """
        return self.response['status']

    def get_response_reason(self):
        """
        Return response reason.

        @rtype: string
        """
        return self.response['reason']

    def get_response_header(self, name):
        """
        Return response header.

        @param name: Name of the response header.
        @return: If header exists return its value, else an empty string.
        @rtype: string
        """
        return self.response['headers'].get(name.title(), None)

    def get_response_headers(self):
        """
        Return response headers.

        @rtype: dict
        """
        return self.response['headers']

    def get_response_body(self):
        """
        Return response body.

        @rtype: string"""
        return self.response['body']


class Scanner(object):
    def __init__(self):
        # Reference implementation using httplib2
        #
        #self.conn = httplib2.Http()
        pass

    def replay(self, request, url=None, method=None, body=None, headers=None):
        """
        Replay a Burp object, appending the result as a Burp object to the
        original replayed list.

        @param request: A gds.pub.burp.Burp object.
        @param url: URL to override request's original url.
        @param method: Method to override request's original request method.
        @param body: Body to override request's original request body.
        @param headers: Headers to override request's original request body.
        """
        if url is None:
            url = request.url.geturl()
        if method is None:
            method = request.get_request_method()
        if body is None:
            body = request.get_request_body()
        if headers is None:
            headers = copy.deepcopy(request.get_request_headers())

        if method == "POST" and body:
            headers.update({"Content-Length": str(len(body))})

        # Reference implementation using httplib2
        #
        #response, body = self.conn.request(request.url.geturl(),
        #                                   request.get_request_method(),
        #                                   request.get_request_body(),
        #                                   request.get_request_headers())
        #
        #burpobj = Burp({'request': {'body': body,
        #                            'method': method,
        #                            'path': path,
        #                            'version': 'HTTP/1.1'},
        #                'response': {'status': response.status,
        #                             'reason': response.reason,
        #                             'version': "HTTP/%.1f" % (float(response.version)/10)},
        #                'index': 0})
        #
        #burpobj.request['headers'] = headers
        #burpobj.response['headers'] = response
        #burpobj.response['body'] = body
        #burpobj.url = urlparse(url)
        #request.replayed.append(burpobj)
