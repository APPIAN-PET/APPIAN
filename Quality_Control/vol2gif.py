import nibabel as nib
import numpy as np
import argparse
from skimage import feature
from nibabel.processing import resample_from_to
from PIL import Image
from os.path import splitext

def edge_detection(ar) :
    G = np.gradient(ar)
    return np.sqrt(G[0]**2 + G[1]**2 + G[2]**2)

def adjust_dimensions(img):
    vol = img.get_data()
    if len(vol.shape ) > 3 : 
        vol = vol.reshape(*vol.shape[0:3])
    img = nib.Nifti1Image( vol , img.affine )
    return img

def rescale(ar) : 
    if np.max(ar) == np.min(ar) : return ar
    return 255. *(ar ) / (np.max(ar))

def vol2gif(img1_fn, out_fn, img2_fn='',alpha_per=64, duration=150, overlay_edge=False):
    alpha = int(alpha_per / 100. * 255)
    img1 = nib.load(img1_fn)
    step1 = np.max(img1.affine[[0,1,2],[0,1,2]])
    img1 = adjust_dimensions(img1)

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
    
    for dim in range(0,3) :
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
            
            final_list.append( final )
        final_list[0].save(splitext(out_fn)[0]+"_"+str(dim)+".gif", save_all=True, append_images=final_list[1:]+final_list[::-1], duration=duration, loop=0)

if __name__ == "__main__" : 
    parser = argparse.ArgumentParser()
    parser.add_argument("volume", help="Input volume")
    parser.add_argument("out_fn", help="Output .gif filename")
    parser.add_argument("-o", "--overlay", default='', help="Optional overlay volume on top of volume")
    parser.add_argument("-d", "--duration", default=150, help="Duration of gif")
    parser.add_argument("-a", "--alpha", default=64, type=int, help="Level of alpha transparency for overlay")
    parser.add_argument("-e", "--edge", default=False, action='store_true',help="Use Edge detection on overlay image")
    args = parser.parse_args()
    vol2gif(args.volume, args.out_fn, args.overlay, alpha_per=args.alpha, duration=args.duration, overlay_edge=args.edge)
