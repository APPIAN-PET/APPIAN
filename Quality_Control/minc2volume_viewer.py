#!/usr/bin/env python
#
# BrainBrowser: Web-based Neurological Visualization Tools
# (https://brainbrowser.cbrain.mcgill.ca)
#
# Copyright (C) 2011 McGill University
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Author: Jon Pipitone <jon@pipitone.ca>
# Author: Robert D. Vincent <robert.d.vincent@mcgill.ca>
#         (Made it work with Python 2.7, supported multiple voxel types)

from __future__ import print_function
import sys
import shutil
import os.path
import argparse
import subprocess
import json
import nibabel as nib
import numpy as np
from Extra.utils import check_gz, splitext

required_minc_cmdline_tools = ['mincinfo', 'minctoraw']

def console_error(message, exit_code):
    print(message, file=sys.stderr)
    sys.exit(exit_code)

def console_log(message):
    print(message)

def which(pgm):
    path=os.getenv('PATH')
    for p in path.split(os.path.pathsep):
        p=os.path.join(p, pgm)
        if os.path.exists(p) and os.access(p, os.X_OK):
            return p

def check_minc_tools_installed():
    for tool in required_minc_cmdline_tools:
        if not which(tool):
            console_error(
              "minc2volume-viewer.py requires that the MINC tools be installed.\n"
              "Visit http://www.bic.mni.mcgill.ca/ServicesSoftware/MINC for info.", 1)

def cmd(command):
    return subprocess.check_output(command.split(), universal_newlines=True).strip()

def get_space(mincfile, space):
    header = {
        "start" : float(cmd("mincinfo -attval {}:start {}".format(space,mincfile))),
        "space_length" : float(cmd("mincinfo -dimlength {} {}".format(space,mincfile))),
        "step" : float(cmd("mincinfo -attval {}:step {}".format(space,mincfile))),
    }

    if not space == "time":
        cosines = cmd("mincinfo -attval {}:direction_cosines {}".format(space,mincfile))
        cosines = cosines.strip().split()
        if len(cosines) > 1:
            header["direction_cosines"] = list(map(float, cosines))

    return header

def make_header(mincfile, datatype, headerfile):
    header = {}


    # find dimension order
    #order = cmd("mincinfo -attval image:dimorder {}".format(mincfile))
    #order = order.split(",")

    #if len(order) < 3 or len(order) > 4:
    #    order = cmd("mincinfo -dimnames {}".format(mincfile))
    #    order = order.split(" ")

    
    img = nib.load(mincfile)
    shape = img.get_shape()
    affine = img.get_affine()
    dims=len(shape)
    
    order = ['xspace','yspace','zspace']
    
    datatype=type(img.get_data().dtype.type(0).item())
    if datatype == int :
        header["datatype"] = 'int' 
    else :
        header["datatype"] = 'float' 


    if dims > 3 :
        ti=np.argmin(shape)
        order.insert(ti, 'time')
    
        header["time"] = {'start':0,'step':1,'space_length':shape[ti]} #get_space(mincfile,"xspace")

    # find space
    header["xspace"] = {'start':affine[0][3],'step':affine[0][0],'space_length':shape[0]} #get_space(mincfile,"xspace")
    header["yspace"] = {'start':affine[1][3],'step':affine[1][1],'space_length':shape[1]} #get_space(mincfile,"yspace")
    header["zspace"] = {'start':affine[2][3],'step':affine[2][2],'space_length':shape[2]} #get_space(mincfile,"zspace")

    # write out the header
    print(headerfile)
    print(header)
    open(headerfile,"w").write(json.dumps(header))

def make_raw(mincfile, datatype, rawfile):
    print(mincfile)
    print(rawfile)
    img = nib.load(mincfile).get_data()
    img.astype('int16').tofile(rawfile)
    
    return 0
    #raw = open(rawfile, "wb")
    #args = ["-normalize", mincfile]
    #opts = {
    #    "int8":   ["-byte",  "-signed"],
    #    "uint8":  ["-byte",  "-unsigned"],
    #    "int16":  ["-short", "-signed"],
    #    "uint16": ["-short", "-unsigned"],
    #    "int32":  ["-int",   "-signed"],
    #    "uint32": ["-int",   "-unsigned"],
    #    "int32":  ["-int",   "-signed"],
    #    "uint32": ["-int",   "-unsigned"],
    #    "float32":["-float"],
    #    "float64":["-double"],
    #}[datatype]
    #for opt in opts:
    #    args.insert(0, opt)
    #args.insert(0, "minctoraw")
    #raw.write(
    #    subprocess.check_output(args))

def main(filename, datatype):
    if not os.path.isfile(filename):
        console_error("File {} does not exist.".format(filename), 1)

    check_minc_tools_installed()

    basename = splitext(os.path.basename(filename))
    dirname = os.path.dirname(filename)
    headername = "{}/{}.header".format(dirname, basename)
    rawname = "{}/{}.raw".format(dirname, basename)

    console_log("Processing file: {}".format(filename))

    console_log("Creating header file: {}".format(headername))
    make_header(filename, datatype, headername)

    console_log("Creating raw data file: {}".format(rawname))
    make_raw(filename, datatype, rawname)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("filename", help="the minc file to convert")
    parser.add_argument("-T", dest="datatype",
                        choices=["int8", "int16", "int32",
                                 "uint8", "uint16", "uint32",
                                 "float32", "float64"],
                        action="store", default="uint8",
                        help="set the voxel data type of the output")
    args = parser.parse_args()
    main(args.filename, args.datatype)
