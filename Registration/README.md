# Coregistration <a name="coregistration"></a>
The first processing step in PET processing is the coregistration of the T1 image to the PET image. The co-registration algorithm is based on minctracc -- which estimates the best linear spatial transformation required to register two 3D volumes -- and proceeds hierarchically by performing iterative co-registrations at progressively finer spatial scales (Collins 1993). Two iterations of the co-registration are performed: one using binary masks of the PET brain mask and the T1 brain mask, the second iteration without any binary mask.

#### Coregistration Options

    --coreg-method=COREG_METHOD 	Coregistration method: minctracc, ants (default=minctracc)
    --coregistration-brain-mask 	Target T1 mask for coregistration (Default=True)
    --second-pass-no-mask    		Do a second pass of coregistration without masks (Default=True)
    --slice-factor=SLICE_FACTOR		Value (between 0. to 1.) that is multiplied by the 
    					maximum of the slices of the PET image. Used to
                        		threshold slices. Lower value means larger mask.
    --total-factor=TOTAL_FACTOR		Value (between 0. to 1.) that is multiplied by the
                        		thresholded means of each slice.
##### Please cite the following paper for the coregistration stage
Collins, D.L., Neelin, P., Peters, T.M., Evans, A.C. Automatic 3D intersubject registration of MR volumetric data in standardized Talairach space. Journal of Computer Assisted Tomography. 18 (2), 192–205. 1994
