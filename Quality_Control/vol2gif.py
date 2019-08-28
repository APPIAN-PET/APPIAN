import nibabel as nib
import numpy as np
import os
import argparse
from skimage import feature
from nibabel.processing import resample_from_to
from PIL import Image
import re

def splitext(s):
    try :
        ssplit = os.path.basename(s).split('.')
        ext='.'+'.'.join(ssplit[1:])
        basepath= re.sub(ext,'',s)
        return [basepath, ext]
    except TypeError :  
        return s

def edge_detection(ar) :
    G = np.gradient(ar)
    return np.sqrt(G[0]**2 + G[1]**2 + G[2]**2)

def adjust_dimensions(img, t):
    vol = img.get_data()
    if len(vol.shape ) > 3 : 
        vol = vol[:,:,:,t]
    img = nib.Nifti1Image( vol , img.affine )
    return img

def rescale(ar) : 
    if np.max(ar) == np.min(ar) : return ar
    return 255. *(ar ) / (np.max(ar))

def convert(img0_fn, out_dir='./', img2_fn='',alpha_per=64, duration=150, overlay_edge=False):
    img0 = nib.load(img0_fn)

    base_name = splitext(os.path.basename(img0_fn))[0]
    out_base = out_dir+os.sep+base_name+os.sep
    
    if not os.path.exists(out_base) :
        os.makedirs(out_base)

    nFrames = len(img0.shape)
    if nFrames == 3 :
        frames=[-1] 
    elif nFrames == 4 :
        frames=range(nFrames)
    else :
        print("Error : input image must have 3 or 4 dimensions")
        exit(1)
    
    dim_map={0:'x',1:'y',2:'z'}

    for dim in range(0,3) :
        for t in frames :
            img1 = adjust_dimensions(img0,t)

            final = vol2gif(img1, dim, img2_fn=img2_fn, alpha_per=alpha_per, duration=duration*nFrames, overlay_edge=overlay_edge)

            out_fn = out_base+base_name+"_frame-"+str(t)+"_"+dim_map[dim]+".gif"
            print("Dimension :", dim_map[dim], "Frame :", str(t), "File :", out_fn)

            final[0].save(out_fn, save_all=True, append_images=final[1:]+final[::-1], duration=duration, loop=0)


def vol2gif(img1,dim, img2_fn='',alpha_per=64, duration=150, overlay_edge=False):
    alpha = int(alpha_per / 100. * 255)
    step1 = np.max(img1.affine[[0,1,2],[0,1,2]])
    if img2_fn != '' :
        img2 = nib.load(img2_fn) 
        step2 = np.max(img2.affine[[0,1,2],[0,1,2]])
    
        img2 = adjust_dimensions(img2)

        if step1 < step2 :
            img1 = nib.processing.resample_from_to( img1 , img2, order=5 )
        else :
            img2 = nib.processing.resample_from_to( img2 , img1, order=5 )
        vol2 = img2.get_data()
        if overlay_edge : vol2 = edge_detection(vol2)
        vol2 = rescale(vol2)

    vol1 = rescale(img1.get_data())

    final_list=[]
    
    for i in range(vol1.shape[dim]) :
        if dim == 0 :
            s1 = vol1[ i, :, : ]
            if img2_fn != '' :
                s2 = vol2[ i, :, : ]
        elif  dim == 1 :
            s1 = vol1[ :, i, : ]
            if img2_fn != '' :
                s2 = vol2[ :, i, : ]
        else :
            s1 = vol1[ :, :, i ]
            if img2_fn != '' :
                s2 = vol2[ :, :, i ]
        
        if img2_fn != '' :
            if np.sum(s2) == 0 : continue
        im1 = Image.fromarray(np.rot90(s1)).convert('RGBA')
        if img2_fn != '' :
            im2 = Image.fromarray(np.rot90(s2)).convert('RGBA')
            im2.putalpha(alpha)
            data=im2.getdata()
            im2.putdata( [ ( d[0], 0, 0, alpha) for d in data ] )
        final = Image.new("RGBA", im1.size)
        final = Image.alpha_composite(final, im1)
        if img2_fn != '' :
            final = Image.alpha_composite(final, im2)
        final_list.append(final)

    return final_list

if __name__ == "__main__" : 
    parser = argparse.ArgumentParser()
    parser.add_argument("volume", help="Input volume")
    parser.add_argument("-o", "--output", default='./', help="Output directory for .gif ")
    parser.add_argument("-v", "--overlay", default='', help="Optional overlay volume on top of volume")
    parser.add_argument("-d", "--duration", default=150, type=int, help="Duration of gif")
    parser.add_argument("-a", "--alpha", default=64, type=int, help="Level of alpha transparency for overlay")
    parser.add_argument("-e", "--edge", default=False, action='store_true',help="Use Edge detection on overlay image")
    args = parser.parse_args()
    convert(args.volume, args.output, args.overlay, alpha_per=args.alpha, duration=args.duration, overlay_edge=args.edge)
