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
