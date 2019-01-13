
import cPickle
from glob import glob
import gzip
import hashlib
from hashlib import md5
import json
import os
import re
import shutil

import numpy as np


#from nipype.utils import logging, config
#fmlogger = logging.getLogger("filemanip")


def update_minchd_json(filename, data_in, var, attr):
    if os.path.isfile(filename) == True:
        fp = file(filename, 'r')
        data=json.load(fp)
        fp.close()
    else:
        data={}

    if data.get(var,'None') == 'None':
    	data[var]={attr:data_in}
    else :
    	if data.get(var).get(attr,'None') == 'None':
	    data[var][attr]=data_in
    	else :
	    data[var][attr]=[data[var][attr],data_in]
    
    fp = file(filename, 'w')
    json.dump(data, fp, sort_keys=True, indent=4)
    fp.close()
