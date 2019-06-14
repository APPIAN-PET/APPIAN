import nibabel as nib
import numpy as np
import argparse
from nibabel.processing import resample_from_to
from PIL import Image
from os.path import splitext


def vol2gif(img1_fn, out_fn, img2_fn=''):
    img1 = nib.load(img1_fn)
    step1 = np.max(img1.affine[[0,1,2],[0,1,2]])

    if img2_fn != '' :
        img2 = nib.load(img2_fn) 
        step2 = np.max(img2.affine[[0,1,2],[0,1,2]])
    
        if step1 < step2 :
            img1 = nib.processing.resample_from_to( img1 , img2, order=5 )
        else :
            img2 = nib.processing.resample_from_to( img2 , img1, order=5 )
        vol2 = img2.get_data()

    vol1 = img1.get_data()
    
    for dim in [1] : #range(0,3) :
        final_list=[]
        for i in range(vol2.shape[dim]) :
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

            im1 = Image.fromarray(np.flip(s1,axis=0)).convert('RGBA')
            if img2_fn != '' :
                im2 = Image.fromarray(np.flip(s2,axis=0)).convert('RGBA')
                im2.putalpha(64)
                data=im2.getdata()
                im2.putdata( [ ( d[0], 0, 0, d[3]) for d in data ] )
            final = Image.new("RGBA", im1.size)
            final = Image.alpha_composite(final, im1)
            if img2_fn != '' :
                final = Image.alpha_composite(final, im2)
            
            final_list.append( final )
        final_list[0].save(splitext(out_fn)[0]+"_"+str(dim)+".gif", save_all=True, append_images=final_list[1:]+final_list[::-1], duration=100, loop=0)

#vol2gif("civet_out/mr1/final/mr1_t1_tal.mnc", "mr1_t1_tal.gif", "MR1/R_slab_1/final/flum_space-mni_0.25mm.nii.gz")
if __name__ == "__main__" : 
    parser = argparse.ArgumentParser()
    parser.add_argument("volume", help="Input volume")
    parser.add_argument("out_fn", help="Output .gif filename")
    parser.add_argument("-o", "--overlay", default='', help="Optional overlay volume on top of volume")
    args = parser.parse_args()
    vol2gif(args.volume, args.out_fn, args.overlay)
