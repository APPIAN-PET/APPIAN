import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pyminc.volumes.factory import *
import sys
import os
import numpy as np
from scipy.ndimage.measurements import center_of_mass
if __name__ == "__main__":
    if os.path.exists(sys.argv[1]) :
        vol=volumeFromFile(sys.argv[1])
        if len(vol.data.shape) > 3 :
            ar = np.sum(vol.data, axis=0)
        else : 
            ar = np.array(vol.data)
        plt.title(os.path.basename(sys.argv[1]))
        com=np.round(center_of_mass(np.array(ar))).astype(int)
        plt.subplot(1,3,1)
        plt.imshow(ar[:,:,com[2]], origin='lower')
        plt.axis('off')
        plt.subplot(1,3,2)
        plt.imshow(ar[:,com[1],:], origin='lower')
        plt.axis('off')
        plt.subplot(1,3,3)
        plt.imshow(ar[com[0],:,:], origin='lower')
        plt.axis('off')
        plt.colorbar()
        plt.savefig(sys.argv[2], dpi=300) #, bbox_inches='tight')
        print("Creating image:", sys.argv[2])
        exit(0)
    print("Error: could not find file ", sys.argv[1])
    exit(1)
