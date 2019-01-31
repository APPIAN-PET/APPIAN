#!/usr/bin/env python
import os
import sys
import SimpleHTTPServer
import SocketServer
from optparse import OptionParser
from optparse import OptionGroup
from glob import glob
import thread
import webbrowser

def get_free_port():
    import socket
    sock = socket.socket()
    sock.bind(('', 0))
    return sock.getsockname()[1]

def create_server(port, *args):
    Handler = SimpleHTTPServer.SimpleHTTPRequestHandler
    SocketServer.TCPServer.allow_reuse_address=True
    httpd = SocketServer.TCPServer(("", port), Handler)

    print( "\n\nAPPIAN Dashboard: http://localhost:"+str(port))   
    httpd.serve_forever()


def LaunchDashboard(outDir):

    if not os.path.exists(outDir) :
        print("Error: could not find APPIAN output directory", outDir)
        exit(1)
    
    print( "APPAIN output directory :"+ outDir)
    indexDir = outDir+os.sep+"preproc"+os.sep+"dashboard"

    if not os.path.exists(indexDir) :
        print("Error: could not find dashboard directory in APPIAN output: ",indexDir)
        print("Did you run APPIAN with the <--dashboard> option?")
        exit(1)
    os.chdir(indexDir) 
    
    port=get_free_port()
    thread.start_new_thread(create_server, (port , 1))
    
    webbrowser.open("http://localhost:"+str(port),new=2)

    raw_input("Press any key to exit. Can relaunch dashboard with APPIAN/LaunchDashboard.py")  #needs to be changed to <input> for python3

if __name__ == "__main__":
    usage = "usage: "
    parser = OptionParser(usage=usage)
    group= OptionGroup(parser,"File options (mandatory)")
    group.add_option("-o","--output_appain","--output_appain",dest="outDir",  help="Absolute path for APPAIN directory where output data will were saved in")

    (opts, args) = parser.parse_args()
    LaunchDashboard(opts.outDir)
