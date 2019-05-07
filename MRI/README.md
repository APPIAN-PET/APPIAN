# MRI Preprocessing <a name="mri"></a>
Prior to performing PET processing, T1 structural preprocessing can be performed if the user does not provide a binary brain mask volume and a transformation file that maps the T1 MR image into stereotaxic space. If these inputs are not provided, APPIAN will automatically coregister the T1 MR image to stereotaxic space. By default, the stereotaxic space is defined on the ICBM 152 6th generation non-linear brain atlas (Mazziotta et al., 2001), but users can provide their own stereotaxic template if desired. Coregistration is performed using an iterative implementation of minctracc (Collins et al., 1994). 

Brain tissue extraction is performed in stereotaxic space using BEaST (Eskildsen et al., 2012). In addition, tissue segmentation can also be performed on the normalized T1 MR image. Currently, only ANTs Atropos package (Avants et al., 2011) has been implemented for T1 tissue segmentation but this can be extended based on user needs.

#### MRI preprocessing options:
    --user-t1mni        Use user provided transform from MRI to MNI space
    --user-brainmask    Use user provided brain mask
    --coregistration-method=MRI_COREG_METHOD	Method to use to register MRI to stereotaxic template
    --brain-extraction-method=MRI_BRAIN_EXTRACT_METHOD	Method to use to extract brain mask from MRI
    --segmentation-method=MRI_SEGMENTATION_METHOD	Method to segment mask from MRI

##### If you use the MRI preprocessing module, please cite the following :

###### Brain mask extraction:
Eskildsen, S.F., Coupé, P., Fonov, V., Manjón, J.V.,Leung, K.K., Guizard, N., Wassef, S.N., Østergaard, L.R., Collins, D.L. “BEaST: Brain extraction based on nonlocal segmentation technique”, NeuroImage, Volume 59, Issue 3, pp. 2362–2373. http://dx.doi.org/10.1016/j.neuroimage.2011.09.012

###### Non-uniformity correction
J.G. Sled, A.P. Zijdenbos and A.C. Evans, "A non-parametric method for automatic correction of intensity non-uniformity in MRI data",in "IEEE Transactions on Medical Imaging", vol. 17, n. 1, pp. 87-97, 1998 
