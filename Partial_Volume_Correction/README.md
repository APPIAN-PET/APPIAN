# Partial-volume correction <a name="pvc"></a>
Partial-volume correction (PVC) is often necessary to account for the loss of resolution in the image due to the point-spread function of the PET scanner and the fact that multiple tissue types may contribute to a single PET voxel. While performing PVC is generally a good idea, this is especially true if the user is interested in regions that are less than approximately 2.5 times the full-width at half-maximum (FWHM) resolution of the scanner. 

## Options

    --no-pvc            Don't run PVC.
    --pvc-method=PVC_METHOD
                        Method for PVC.
    --pet-scanner=PET_SCANNER
                        FWHM of PET scanner.
    --fwhm=SCANNER_FWHM, --pvc-fwhm=SCANNER_FWHM
                        FWHM of PET scanner (z,y,x).
    --pvc-max-iterations=MAX_ITERATIONS	Maximum iterations for PVC method (Optional).
    --pvc-tolerance=TOLERANCE Tolerance for PVC algorithm.
    --pvc-denoise-fwhm=DENOISE_FWHM	FWHM of smoothing filter (for IdSURF).
    --pvc-nvoxel-to-average=NVOXEL_TO_AVERAGE Number of voxels to average over (for IdSURF).

##### References
###### Geometric Transfer Matrix (GTM)
Rousset, O.G., Ma, Y., Evans, A.C., 1998. Correction for Partial Volume Effects in PET : Principle and Validation. J. Nucl. Med. 39, 904–911.

###### Surface-based iterative deconvolution (idSURF)
Funck, T., Paquette, C., Evans, A., Thiel, A., 2014. Surface-based partial-volume correction for high-resolution PET. Neuroimage 102, 674–87. doi:10.1016/j.neuroimage.2014.08.037

###### Müller-Gartner (MG)
Muller-Gartner, H.W., Links, J.M., Prince, J.L., Bryan, R.N., McVeigh, E., Leal, J.P., Davatzikos, C., Frost, J.J. Measurement of radiotracer concentration in brain gray matter using positron emission tomography: MRI-based correction for partial volume effects. Journal of Cerebral Blood Flow and Metabolism 12, 571–583. 1992

###### Labbé (LAB) 
Labbe C, Koepp M, Ashburner J, Spinks T, Richardson M, Duncan J, et al. Absolute PET quantification with correction for partial volume effects within cerebral structures. In: Carson RE, Daube-Witherspoon ME, Herscovitch P, editors. Quantitative functional brain imaging with positron emission tomography. San Diego, CA: Academic Press; 1998. p. 67–76.

###### Multi-target Correction (MTC) 
Erlandsson K, Wong A T, van Heertum R, Mann J J and Parsey R V 2006 An improved method for voxel-based partial volume correction in PET and SPECT. Neuroimage 31(2), T84 

###### Region-based voxel-wise correction (RBV)
Thomas B A, Erlandsson K, Modat M, Thurfjell L, Vandenberghe R, Ourselin S and Hutton B F 2011 The importance of appropriate partial volume correction for PET quantification in Alzheimer’s disease. Eur. J. Nucl. Med. Mol. Imaging. 38(6), 1104–19.

###### Iterative Yang (IY)
Erlandsson K, Buvat I, Pretorius P H, Thomas B A and Hutton B F. 2012. A review of partial volume correction techniques for emission tomography and their applications in neurology, cardiology and oncology Phys. Med. Biol. 57 R119

###### Van-Cittert (RVC) 
NA

###### Richardson–Lucy (RL)
Richardson, W.H., 1972. Bayesian-Based Iterative Method of Image Restoration. J. Opt. Soc. Am. 62, 55. doi:10.1364/JOSA.62.000055

###### PETPVC
*Note: MG, LAB, MTC, IY, RVC, RL are all implemented with PETPVC. You should therefore cite the following paper if you use one of these.* 

Thomas, B.A., Cuplov, V., Bousse, A., Mendes, A., Thielemans, K., Hutton, B.F., Erlandsson, K., 2016. PETPVC: a toolbox for performing partial volume correction techniques in positron emission tomography. Phys. Med. Biol. 61, 7975–7993. doi:10.1088/0031-9155/61/22/7975
