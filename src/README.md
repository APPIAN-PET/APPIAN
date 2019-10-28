



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
Avants, B.B., Tustison, N. and Song, G., 2009. Advanced normalization tools (ANTS). Insight j, 2, pp.1-35.

###### Non-uniformity correction
Avants, B.B., Tustison, N. and Song, G., 2009. Advanced normalization tools (ANTS). Insight j, 2, pp.1-35.
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
# Quantification
Quantification [usuallly with tracer kinetic analysis (TKA)] allows for the quantification of physiological or biological parameters from the radiotracer concentrations measured in the PET image. The appropriate TKA method will depend on the radiotracer. Certain models, e.g., the Logan Plot and Simplified Reference Tissue Model (SRTM), are only suitable for radiotracers that are reversibly bound to the tissue. Currently only three TKA methods are implemented: Logan plot, Patlak-Gjedde plot, and the SRTM.

#### Quantification options:
    --tka-method=TKA_METHOD
                        Method for performing tracer kinetic analysis (TKA):
                        lp, pp, srtm.
    --k2=TKA_K2         With reference region input it may be necessary to
                        specify also the population average for regerence
                        region k2
    --thr=TKA_THR       Pixels with AUC less than (threshold/100 x max AUC)
                        are set to zero. Default is 0%
    --max=TKA_MAX       Upper limit for Vt or DVR values; by default max is
                        set pixel-wise to 10 times the AUC ratio.
    --min=TKA_MIN       Lower limit for Vt or DVR values, 0 by default
    --t3max=TKA_T3MAX   Upper limit for theta3, 0.01 by default
    --t3min=TKA_T3MIN   Lower limit for theta3, 0.001 by default
    --nBF=TKA_NBF       Number of basis functions.
    --filter            Remove parametric pixel values that over 4x higher
                        than their closest neighbours.
    --reg-end=TKA_END   By default line is fit to the end of data. Use this
                        option to enter the fit end time (in min).
    --y-int=TKA_V       Y-axis intercepts time -1 are written as an image to
                        specified file.
    --num=TKA_N         Numbers of selected plot data points are written as an
                        image.
    --Ca=TKA_CA         Concentration of native substrate in arterial plasma
                        (mM).
    --LC=TKA_LC         Lumped constant in MR calculation; default is 1.0.
    --density=TKA_DENSITY
                        Tissue density in MR calculation; default is 1.0 g/ml.
    --arterial          Use arterial input input.
    --start-time=TKA_START_TIME
                        Start time of either regression in MTGA or averaging
                        time for SUV.
    --end-time=TKA_END_TIME
                        End time for SUV average.
    --body-weight=BODY_WEIGHT
                        Either name of subject body weight (kg) in header or
                        path to .csv file containing subject names and body
                        weight (separated by comma).
    --radiotracer-dose=RADIOTRACER_DOSE
                        Either name of subject's injected radiotracer dose
                        (MBq) in header or path to .csv file containing
                        subject names and injected radiotracer dose (MBq).
    --tka-type=TKA_TYPE
                        Type of tka analysis: voxel or roi.
##### References
###### Logan Plot (lp)
Logan, J., Fowler, J.S., Volkow, N.D., Wang, G.-J., Ding, Y.-S., Alexoff, D.L., 1996. Distribution Volume Ratios Without Blood Sampling from Graphical Analysis of PET Data. J. Cereb. Blood Flow Metab. 16, 834–840. doi:10.1097/00004647-199609000-00008

###### Patlak-Gjedde Plot (pp)
*Please cite both of the following papers when using the Patlak-Gjedde method*

Patlak, C. S., Blasberg, R. G., and Fenstermacher, J. D. (1983). Graphical evaluation of blood-to-brain transfer constants from multiple-time uptake data. J. Cereb. Blood Flow Metab. 3, 1–7. doi: 10.1038/jcbfm.1983.1

Gjedde, A. (1982). Calculation of cerebral glucose phosphorylation from brain uptake of glucose analogs in vivo: a re-examination. Brain Res. 257, 237–274. doi: 10.1016/0165-0173(82)90018-2

###### Simplified Reference Tissue Model (srtm)
Gunn, R.N., Lammertsma, A.A., Hume S.P., Cunningham, V.J. 1997. Parametric Imaging of Ligand-Receptor Binding in PET Using a Simplified Reference Region Model. Neuroimage. 6(4), 279-287.
