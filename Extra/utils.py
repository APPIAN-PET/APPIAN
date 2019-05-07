import os 
import re
import gzip
import shutil
import gzip

import subprocess
def cmd(command):
    try:
        output = subprocess.check_output(command,stderr=subprocess.STDOUT, shell=True, universal_newlines=True)
    except subprocess.CalledProcessError as exc:
        print("Status : FAIL", exc.returncode, exc.output)
        exit(1)
    else:
        print("Output: \n{}\n".format(output))


def splitext(s):
    try :
        ssplit = os.path.basename(s).split('.')
        ext='.'+'.'.join(ssplit[1:])
        basepath= re.sub(ext,'',s)
        return [basepath, ext]
    except TypeError :  
        return s


def gz(ii, oo):
    with open(ii, 'rb') as in_file:
        with gzip.open(oo, 'wb') as out_file:
            shutil.copyfileobj(in_file, out_file)

def gunzip(ii, oo):
    with gzip.open(ii, 'rb') as in_file:
        with open(oo, 'wb') as out_file:
            shutil.copyfileobj(in_file, out_file)

def check_gz(in_file_fn) :
    img, ext = splitext(in_file_fn)
    if '.gz' in ext :
        out_file_fn='/tmp/'+os.path.basename(img)+'.nii'
        sif = img + '.sif'
        if os.path.exists(sif) : 
            shutil.copy(sif, '/tmp/'+os.path.basename(img)+'.sif'  )
        gunzip(in_file_fn, out_file_fn) 
        return out_file_fn
    else :
        return in_file_fn
