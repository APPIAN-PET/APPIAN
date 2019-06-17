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


#### Coregistration Options

```
--normalization-type
--user-ants-command

```
##### Please cite the following paper for the coregistration stage
Avants, B.B., Tustison, N. and Song, G., 2009. Advanced normalization tools (ANTS). Insight j, 2, pp.1-35.
