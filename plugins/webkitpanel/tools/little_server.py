#! /usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2011  <ansuzpeorth@gmail.com>
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

from BaseHTTPServer import HTTPServer
from CGIHTTPServer import CGIHTTPRequestHandler
import cgi
import os
import sys
import subprocess

port         = sys.argv[1]
flag_local   = eval(sys.argv[2])
request_path = sys.argv[3]

os.chdir(request_path)

DEBUG = False

def debug(text):
    if DEBUG: print text

class HTTPHandler (CGIHTTPRequestHandler):
    server_version = "AnsuzServeurHTTP/0.1"
    cgi_directories = ['/cgi-bin', '/htbin','/python','/perl']
    
    def do_GET(self):
        debug('__do_GET__\n%s'% self.headers)
        if self.request_filter(): return
        if self.path.find('.php') != -1:
            if self.path.find('?') != -1:
                self.path, self.requete = self.path.split('?', 1)
            else:
                self.requete = ''
            self.php_request()
        else:
            CGIHTTPRequestHandler.do_GET(self)

    def do_POST(self):
        debug('__do_POST__\n%s'% self.headers)
        if self.request_filter(): return
        if self.path.find('.php') != -1:
            self.requete = self.rfile.read(int(self.headers['Content-Length']))
            self.php_request()
        else:
            CGIHTTPRequestHandler.do_POST(self)
    
    def php_request(self):
        self.args = dict(cgi.parse_qsl(self.requete))
        real_path = request_path + self.path
        l   = ['%s=%s' % (key, value) for key, value in self.args.iteritems()]
        arg = ["php-cgi", real_path] + l
        output = subprocess.Popen(arg, stdout=subprocess.PIPE).communicate()[0]
        self.send_response(200, 'OK')
        #self.send_header('Content-type', 'text/html')
        #self.end_headers()
        self.wfile.write(output)
    
    def request_filter(self):
        if not flag_local: return False
        ip = self.client_address[0]
        if not ip.startswith('127.0.0.1'):
            self.send_response(403, 'Forbidden')
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write('Acces Denied, ip logged: %s' % ip)
            return True
        return False
        
debug('__Serveur Starting__: %s %s'% (port, request_path))
httpd = HTTPServer(('', int(port)), HTTPHandler)
httpd.serve_forever()

