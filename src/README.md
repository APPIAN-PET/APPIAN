
# Masking <a name="masking"></a>
The pipeline uses up to three different types of masks: a reference region mask to define a region of non-specific radiotracer binding for tracer kinetic analysis, masks for the PVC algorithms, masks to define the regions from which the user wishes to extract quantitative values (kBq/ml, BPnd, Ki, etc.). Moreover, these masks can be derived from multiple sources: manually drawn ROI for each T1 MRI, classification produced by CIVET/ANIMAL, stereotaxic atlas, user-defined regions in native PET space (e.g., region of infarcted tissue from ischemic stroke).

  #### Masking options: PVC

    --pvc-label-space=PVC_LABEL_SPACE
                        Coordinate space of labeled image to use for TKA.
                        Options: [pet/t1/stereo]
    --pvc-label-img=PVC_LABEL_IMG
                        Options: 1. ICBM MNI 152 atlas:
                        <path/to/labeled/atlas>, 2. Stereotaxic atlas and
                        template: path/to/labeled/atlas
                        /path/to/atlas/template 3. Internal classification
                        method (antsAtropos) 4. String that identifies labels
                        in anat/ directory to be used as mask
    --pvc-label=PVC_LABELS
                        List of label values to use for pvc
    --pvc-label-erosion=PVC_ERODE_TIMES
                        Number of times to erode label
    --pvc-labels-brain-only
                        Mask pvc labels with brain mask
    --pvc-labels-ones-only
                        Flag to signal threshold so that label image is only
                        1s and 0s

  #### Masking options: Quantification

    --tka-label-space=TKA_LABEL_SPACE
                        Coordinate space of labeled image to use for TKA.
                        Options: [pet/t1/stereo]
    --tka-label-img=TKA_LABEL_IMG
                        Options: 1. ICBM MNI 152 atlas:
                        <path/to/labeled/atlas>, 2. Stereotaxic atlas and
                        template: path/to/labeled/atlas
                        /path/to/atlas/template 3. Internal classification
                        method (antsAtropos) 4. String that identifies labels
                        in anat/ directory to be used as mask
    --tka-label=TKA_LABELS
                        List of label values to use for TKA
    --tka-label-erosion=TKA_ERODE_TIMES
                        Number of times to erode label
    --tka-labels-brain-only
                        Mask tka labels with brain mask
    --tka-labels-ones-only
                        Flag to signal threshold so that label image is only
                        1s and 0s

 #### Masking options: Results

    --no-results-report
                        Don't calculate descriptive stats for results ROI.
    --results-label-space=RESULTS_LABEL_SPACE
                        Coordinate space of labeled image to use for TKA.
                        Options: [pet/t1/stereo]
    --results-label-img=RESULTS_LABEL_IMG
                        Options: 1. ICBM MNI 152 atlas:
                        <path/to/labeled/atlas>, 2. Stereotaxic atlas and
                        template: path/to/labeled/atlas
                        /path/to/atlas/template 3. Internal classification
                        method (antsAtropos) 4. String that identifies labels
                        in anat/ directory to be used as mask
    --results-label=RESULTS_LABELS
                        List of label values to use for results
    --results-label-erosion=RESULTS_ERODE_TIMES
                        Number of times to erode label
    --results-labels-brain-only
                        Mask results labels with brain mask
    --results-labels-ones-only
                        Flag to signal threshold so that label image is only 1s and 0s

# Registration <a name="coregistration"></a>

## PET-MRI Coregistration
Volume registration algorithm in APPIAN is performed using ANTs (Avants, 2009). The PET to MRI co-registration is performed using only rigid transformations. 

## MRI & Template Normalization
By default, the MRI is mapped to APPIAN's default stereotaxic template (MNI152) with ANTs using non-linear deformations. The same is true if the user specifies label volumes in a stereotaxic space other than on the default APPIAN stereotaxic template. If users wish to perform these transformations with rigid or affine transformations, instead of non-linear deformations, they can specify this with the option : ```-- normalization-type```. 

## User defined ANTs transformation
If APPIAN's default parameters for ANTs do not give a good registration, the user can specify their own ANTs transformation in a text file with the option ```--user-ants-command </path/to/ants/command.txt>```. You can find an example [here](https://github.com/APPIAN-PET/APPIAN/blob/master/Registration/ants_command.txt) :

```
antsRegistration --verbose 1 --float --collapse-output-transforms 1 --dimensionality 3 --initial-moving-transform [ fixed_image, moving_image, 1 ] --initialize-transforms-per-stage 0 --interpolation interpolation_method 
    --transform Rigid[ 0.1 ] --metric Mattes[ fixed_image, moving_image, 1, 32, Regular, 0.3 ] --convergence [ 250x200x100, 1e-08, 20 ] --smoothing-sigmas 4.0x2.0x1.0vox --shrink-factors 4x2x1 --use-estimate-learning-rate-once 1 --use-histogram-matching 0 
    --transform Affine[ 0.1 ] --metric Mattes[ fixed_image, moving_image, 1, 32, Regular, 0.3 ] --convergence [ 500x250x200 , 1e-08, 20 ] --smoothing-sigmas 4.0x2.0x1.0vox --shrink-factors 4x2x1 --use-estimate-learning-rate-once 1 --use-histogram-matching 0 
    --transform SyN[ 0.1, 3.0, 0.0] --metric Mattes[ fixed_image, moving_image, 0.75, 64, None ]  --convergence [ 500x400x300x200x100, 1e-6,10 ] --smoothing-sigmas 4.0x3.0x2.0x1.0x0.0vox --shrink-factors 8x6x4x2x1  --winsorize-image-intensities [ 0.005, 0.995 ]  --write-composite-transform 1
--output [ transform, warped_image, inverse_warped_image ] 
```


In order for APPIAN to know how to "fill in" the appropriate file names and parameters in the user's command, the following strings are substituted by APPIAN for the appropriate variables:

|     string                    | variable                               |
|-------------------------------|----------------------------------------|
| 'fixed_image'                 | target image for registration          |
| 'moving_image'                | image that is being aligned to target  |
| 'fixed_image_mask'            | mask for target image for registration |
| 'moving_image_mask'           | mask for image that is being aligned   |
| 'composite_transform'         | output forward transform               |
| 'inverse_composite_transform' | output inverse transform               |
| 'inverse_warped_image'        | fixed image resampled to moving image  |
| 'warped_image'                | moving image resampled to fixed image  |
| 'interpolation_method'        | interpolation method for resampling    |


##### Please cite the following paper for the coregistration stage
Avants, B.B., Tustison, N. and Song, G., 2009. Advanced normalization tools (ANTS). Insight j, 2, pp.1-35.

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
Avants, B.B., Tustison, N. and Song, G., 2009. Advanced normalization tools (ANTS). Insight j, 2, pp.1-35.

###### Non-uniformity correction
Avants, B.B., Tustison, N. and Song, G., 2009. Advanced normalization tools (ANTS). Insight j, 2, pp.1-35.
