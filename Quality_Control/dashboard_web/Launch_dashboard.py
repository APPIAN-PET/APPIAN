#!/usr/bin/env python

import os
import sys
import argparse
import SimpleHTTPServer
import SocketServer



Handler = SimpleHTTPServer.SimpleHTTPRequestHandler
SocketServer.TCPServer.allow_reuse_address=True
httpd = SocketServer.TCPServer(("", PORT), Handler)



print "APPAIN output directory", opts.outDir
print "serving at port", opts.PORT
httpd.serve_forever()




if __name__ == "__main__":
    usage = "usage: "
    parser = OptionParser(usage=usage,version=version)
    group= OptionGroup(parser,"File options (mandatory)")
    group.add_option("-o","--output_appain","--output_appain",dest="outDir",  help="Absolute path for APPAIN directory where output data will were saved in")
    group.add_option("-p","--port","--port",dest="PORT",type='string', help="Port number")

    (opts, args) = parser.parse_args()
