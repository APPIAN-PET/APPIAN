# APPIAN User Guide

# Table of Contents
1. [Quick Start](#quickstart)
2. [File Formats](#fileformat) \
	2.1 [Nifti](#nifti) \
	2.2 [MINC](#minc) 
3. [Useage](#useage) 
4. [Overview](#overview) \
	4.1 [Base Options](#options) \
	4.2 [MRI Preprocessing](https://github.com/APPIAN-PET/APPIAN/blob/master/MRI/README.md) \
	4.3 [Coregistration](https://github.com/APPIAN-PET/APPIAN/blob/master/Registration/README.md) \
	4.4 [Masking](https://github.com/APPIAN-PET/APPIAN/blob/master/Masking/README.md) \
	4.5 [Partial-Volume Correction](https://github.com/APPIAN-PET/APPIAN/blob/master/Partial_Volume_Correction/README.md) \
	4.6 [Quantification](https://github.com/APPIAN-PET/APPIAN/blob/master/Tracer_Kinetic/README.md) \
	4.7 [Reporting of Results](https://github.com/APPIAN-PET/APPIAN/blob/master/Results_Report/README.md) \
	4.8 [Quality Control](https://github.com/APPIAN-PET/APPIAN/blob/master/Quality_Control/README.md) \
	4.9 [Dashboard GUI](https://github.com/APPIAN-PET/APPIAN/blob/master/Quality_Control/README.md) 
5. [Atlases](https://github.com/APPIAN-PET/APPIAN/blob/master/Atlas/README.md) 
6. [Examples](#example) 



## 1. Quick Start

### Download CIMBI Open Data  <a name="quickstart"></a>
Download the data from https://openneuro.org/datasets/ds001421/versions/00002 or using the Amazon web service command line interface (AWS CLI):

```
apt install awscli
aws s3 sync --no-sign-request s3://openneuro.org/ds001421 ds001421-download/
```
 
### Format data
The data may need to be reformatted slightly to have the following structure. 
As of version 00002 of the Cimbi data set, you can fix it using the following commands: 
```
	find -iregex '.*\.\(json\|mnc\|nii\|nii.gz\)$'   -exec sh -c 'x="{}"; f2=`echo $x | sed 's/ses_/ses-/g'`;  mv $x $f2  ' \;
```

The .json headers also need to be corrected by removing the "," at the end of the following lines

Line 10: 

	"Name": ["[C-11]SB"], -->  "Name": ["[C-11]SB"]

Line 26: 
	
	"EffectiveResolutionAxial": [1.218750e-01], --> "EffectiveResolutionAxial": [1.218750e-01]

Line 33: 
	
	"Values": [16, 10], --> "Values": [16, 10]


A comma needs to be added to line 27,

	Line 27: }, --> }


Here is the file structure that you should end up with:

	cimbi/
		sub-01/
			_ses-01/
				anat/
					sub-01_ses-01_T1w.json  
					sub-01_ses-01_T1w.nii
				pet/
					sub-01_ses-01_pet.json  
					sub-01_ses-01_pet.nii.gz
			_ses-02/
				anat/
					sub-01_ses-02_T1w.json  
					sub-01_ses-02_T1w.nii
				pet/
					sub-01_ses-02_pet.json 
					sub-01_ses-02_pet.nii.gz

### Run Examples

You can run the following examples to see some of the basic functionality of APPIAN. Remember to mount your "cimbi" directory by changing </path/to/cimbi/dir> to the actual path to your directory. Likewise, mount your "out_cimbi" directory by changing </path/to/cimbi/dir/out_cimbi> to the actual path to your directory.  


#### Minimal Inputs
##### Default: Coregistration + MRI Preprocessing + Results Report
	docker run -v  </path/to/cimbi/dir>:"/path/to/cimbi/dir" -v </path/to/cimbi/dir/out_cimbi>:"/path/to/cimbi/dir/out_cimbi" tffunck/appian:latest bash -c "python3 /opt/APPIAN/Launcher.py -s "/path/to/cimbi/dir" -t "/path/to/cimbi/dir/out_cimbi" ";

#### PVC
	docker run -v </path/to/cimbi/dir>:"/path/to/cimbi/dir" -v </path/to/cimbi/dir/out_cimbi>:"/path/to/cimbi/dir/out_cimbi" tffunck/appian:latest bash -c "python3 /opt/APPIAN/Launcher.py --fwhm 3 3 3 --pvc-method 'GTM' --no-results-report -s /path/to/cimbi/dir -t "/path/to/cimbi/dir/out_cimbi" --sessions 01  01";

#### PVC + Quantification
	docker run -v </path/to/cimbi/dir>:"/path/to/cimbi/dir" -v </path/to/cimbi/dir/out_cimbi>:"/path/to/cimbi/dir/out_cimbi" tffunck/appian:latest bash -c "python3 /opt/APPIAN/Launcher.py --tka-method lp --tka-label 3 --results-label-erosion 5 --fwhm 3 3 3 --pvc-method 'GTM' --no-results-report -s "/path/to/cimbi/dir" -t "/path/to/cimbi/dir/out_cimbi"  ";

## 2. File Formats  <a name="fileformat"></a>

### Nifti
APPIAN uses the [BIDS][link_bidsio] file format specification for PET:

#### Example of file organization for PET and T1 
    sub-01/
       _ses-01/
          pet/
	  	sub-01_ses-01_task-01_pet.nii
		sub-01_ses-01_task-01_pet.json
		sub-01_ses-01_task-02_pet.nii
		sub-01_ses-01_task-02_pet.json
             	...
          anat/ 
	  	sub-01_ses-01_T1w.nii
      _ses-02/
               	...

    sub-02/
       _ses-01/
          pet/
	  	sub-02_ses-01_task-01_pet.nii
		sub-02_ses-01_task-01_pet.json
		sub-02_ses-01_task-02_pet.nii
		sub-02_ses-01_task-02_pet.json
             	...
          anat/ 
	  	sub-02_ses-01_T1w.nii
        _ses-02/
             ...


#### Required
##### PET (native PET space)
`sub-<participant_label>/[_ses-<session_label>/]pet/sub-<participant_label>[_ses-<session_label>]_task-<task_label>[_acq-<label>][_rec-<label>][_run-<index>]_pet.nii[.gz]`

##### PET Header
`sub-<participant_label>/[_ses-<session_label>/]pet/sub-<participant_label>[_ses-<session_label>]_task-<task_label>[_acq-<label>][_rec-<label>][_run-<index>]_pet.json`

##### T1w (native T1 space) :
`sub-%s/_ses-%s/anat/sub-%s_ses-%s*T1w.mnc`

##### Brain mask (stereotaxic space): 
`sub-%s/_ses-%s/anat/sub-%s_ses-%s*_T1w_space-mni_brainmask.mnc`

##### T1 Segmentation: 
`sub-<participant-label>/_ses-<session-label>/mask/sub-<participant-label>_ses-<session-label>_space-mni_variant-seg_dtissue.mnc`

Although BIDS is based on the Nifti file format, APPIAN will accept both MINC and Nifti inputs. All Nifti files are converted to MINC for further processing. 

## 3. Usage <a name="useage"></a>

### Launching APPIAN
APPIAN is a Python program (Python 3.6 to be specific) that is launched using a command of the form:

```
python3 <path to APPIAN directory>/Launcher.py <list of options> 
```

The <subject names> arguments are optional. If you do not provide spedific subject IDs, the APPIAN will be run on all subjects found in the source directory. When running APPIAN in a Docker container (described in detail in the following section), the APPIAN directory is located in “/opt/APPIAN/”:

```
python3 /opt/APPIAN/Launcher.py <list of options> 
```

Running APPIAN with Docker
APPIAN is run in a Docker container. To launch a container based on a specific image, run:

```
Docker run -it <name of image>:<image tag>
```

or in our case:

```
docker run -it tffunck/appian:latest
```

Here the “-it” flag means that the container is launched in interactive mode. That is, you will be dropped into a bash shell within the filesystem and will be able to do most of the typical bash/unix stuff you normally do. You can also run the container non-interactively by dropping the “-it” flag and adding a bash command at the end of the line, as follows:

```
docker run <name of image>:<image tag> <your bash command>
```

or in our case:

docker run tffunck/appian:latest ls /opt
bin
doc
etc
...

APPIAN is intended to be flexible and applicable in a wide variety of situations. However, this also means that it has many options that have to be specified by the user. Typing out these options in the command line would quickly become tedious, so it is more convenient to put the command you will use to launch the pipeline, along with all of the desired options, into a bash script (basically just a text file that you can run from the command line). For the example below, “run.sh” is just such a bash script (note that you can name your script whatever you like). Therefore, in the current example, the command would look something like 

```
python3 /opt/APPIAN/Launcher.py -s /path/to/pet/images -t /path/to/output/dir -p <study prefix> -c </path/to/civet/output> <subject names>
```

By default, you cannot access any of the data on your computer from the filesystem of the Docker container. To access your data from the Docker container it is necessary to mount the directory on your computer in the Docker container. This sounds complicated, but it’s actually very simple. All you have to do is pass the “-v” flag (“v” for volume) to the Docker “run” command, followed by the absolute path to the directory you want to mount, a colon (“:”),  and the absolute path to the location where you want to mount it. Let’s say your database is stored in “/path/to/your/data” and, for simplicity, you want to mount it to a path called “/path/to/your/data” in the Docker container. To run your Docker container with this path mounted, you would just have to run:

```
docker run -it -v /path/to/your/data:/path/to/your/data  tffunck/appian:latest
```

As mentioned above,  there are two ways in which to run APPIAN, either interactively or by passing a command to the “`docker run`” command. Assuming that you put your “run.sh” script into the same directory as your data, “/path/to/your/data”, then you would run something like the following commands:

```
docker run -it -v /path/to/your/data:/path/to/your/data tffunck/appian:latest
#You are now in the docker container
cd /path/to/your/data 
./run.sh
```

Alternatively, you can also run the pipeline through a non-interactive docker container, like so:
```
docker run /path/to/your/data:/path/to/your/data tffunck/appian:latest /path/to/your/data/run.sh
```
Either method will give you the same results, it’s up to you and what you find more convenient. 

## 4. Pipeline Overview  <a name="overview"></a>

### 4.1 Base User Options  <a name="options"></a>
APPIAN has lots of options, mostly concerned with the types of masks you want to use, and the parameters to pass to the PVC and quantification algorithms. The only mandatory options are a source directory with PET images (`-s`), a target directory where the outputs will be stored (`-t`). 

#####  Mandatory arguments:
    -s SOURCEDIR, --source=SOURCEDIR, --sourcedir=SOURCEDIR
                        Input file directory
    -t TARGETDIR, --target=TARGETDIR, --targetdir=TARGETDIR
                        Directory where output data will be saved in
#### Data Formats
APPIAN uses the BIDS specification (nifti and .json).

#### Running on a subset of data
By default, APPIAN will run for all the PET scans located in the source directory. However, a more specific subset of subjects can be specified using the "--subjects", "--sessions", "--tasks", "--runs", "--acq", and "--rec" option to specify specific subjects, sessions, tasks, runs, acquisitions (i.e., specific radiotracers), and reconstructions (e.g., "FBP" or "OSEM"). 


#####  Optional arguments:
    --radiotracer=ACQ, --acq=ACQ
                        Radiotracer
    -r REC, --rec=REC   Reconstruction algorithm
    --subjects=SUBJECTLIST List of subjects
    --sessions=SESSIONLIST List of sessions
    --tasks=TASKLIST    List of tasks
    --runs=RUNSLIST     List of runs
    
#### Scan Level Vs Group Level
APPIAN runs in 2 steps: 1) scan-level; 2) group-level. The first step is called "scan level" analysis because APPIAN processes all the individual PET scans with their corresponding T1. The group-level analysis runs once all of the scans have finished processing and combines the outputs from each of these to calculate descriptive statistics, perform quality control, and generate the dashboard GUI. 

Both the scan-level and the group-level analysis can be turned off using the "--no-scan-level" and "--no-group-level" options.

#####  Optional arguments:
    --no-group-level    Don't run group level analysis
    --no-scan-level     Don't run scan level analysis


#### Analysis Space
Users can select which coordinate space they wish to perfom their PET processing in. By default, APPIAN will run all analysis in native PET coordinate space. This can be manually specified as ```--analysis-space pet```. APPIAN can also perform the analysis in the T1 MRI native coordinate space (```--analysis-space t1```), or in stereotaxic space (```--analysis-space stereo```).

By default the steortaxic coordinate space used by APPIAN is MNI 152. However, uses can set their own stereotaxic template image with the option ```--stereotaxic-template </path/to/your/template.mnc>``` (Warning: this feature is still experimental and has not yet been thoroughly tested).

Users will typically procude a quantitative or semi-quantitative output images (e.g., tracer-kinetic analysis or with the SUVR method). If the analysis space was set to "pet" or "t1", there is an additional option to transform these output images to stereotaxic coordinate space : ```--quant-to-stereo```

##### Optional arguments:
    --analysis-space=ANALYSIS_SPACE
                        Coordinate space in which PET processing will be
                        performed (Default=pet)
    --stereotaxic-template=TEMPLATE
                        Template image in stereotaxic space
    --quant-to-stereo 
    			Transform quantitative images to stereotaxic space

#### Surface-based ROIs
In addition to supporting ROIs defined in 3D volumes, APPIAN can also use ROIs defined on a cortical surface. Currently only obj surfaces are implemented in APPIAN, but users looking to use other formats can get in contact with developers to figure out a way to do this. APPIAN currently also assumes that the surfaces are in stereotaxic coordinate space. 

Surface obj files and corresponding label .txt files should be stored in the anat/ directory for each subject. The ```--surf-label <string>```in order to identify the surface ROI mask. 

Obj files and masks should have the format: 

**obj**: ```anat/sub-<sub>_ses-<ses>_T1w_hemi-<L/R>_space-stereo_midthickness.surf.obj```

**surf**: ```sub-<sub>/_ses-<ses>/anat/sub-<sub>_ses-<ses>_T1w_hemi-<L/R>_space-stereo_<label>.txt"```


#### Optional Arguments:
    --surf              	Flag that signals APPIAN to find surfaces
    --surf-label <string>	Label string that identifies surface ROI
    --surf-space=SURFACE_SPACE
                        Set space of surfaces from : "pet", "t1", "stereo"
                        (default=icbm152)
    --surf-ext=SURF_EXT
                        Extension to use for surfaces
### Multithreading

Nipype allows multithreading and therefore allows APPIAN to run multiple scans in parrallel. By default, APPIAN only runs using 1 thread, but this can be increased using the ```--threads``` option.

#### Optional Arguments:
    --threads=NUM_THREADS
                        Number of threads to use. (defult=1)


### 4.2 [MRI Preprocessing]<a name="mri"></a>
Processing of T1 MRI for spatial normalization to stereotaxic space, intensity non-uniformity correction, brain masking, and segementation.

Prior to performing PET processing, T1 structural preprocessing can be performed if the user does not provide a binary brain mask volume and a transformation file that maps the T1 MR image into stereotaxic space. If these inputs are not provided, APPIAN will automatically coregister the T1 MR image to stereotaxic space. By default, the stereotaxic space is defined on the ICBM 152 6th generation non-linear brain atlas (Mazziotta et al., 2001), but users can provide their own stereotaxic template if desired. Coregistration is performed using an iterative implementation of minctracc (Collins et al., 1994). 

#### Non-uniformity MRI intensity correction
Distances for T1 MRI intensity non-uniformity correction with N4 (1.5T ~ 200, 3T ~ ). By default=0, which means this step will be skipped.
```
    --n4-bspline-fitting-distance  
```

Order of BSpline interpolation for N4 correction.
```
    --n4-bspline-order
```

List with number of iterations to perform. Default=50 50 30 20.
```
    --n4-n-iterations
```

Order of BSpline interpolation for N4 correction (Default=2).
```
    --n4-shrink-factor
```   

Convergence threshold for N4 correction (Default=1e-6).
```
 --n4-convergence-threshold
```

#### Spatial MRI normalization
Type of registration to use for T1 MRI normalization, rigid, linear, non-linear: rigid, affine, nl. (Default=nl)
```
    --normalization-type
```


User specified command for normalization. See \"Registration/user_ants_example.txt\" for an example
```
    --user-ants-command
```

User provided transform from to and from MRI & MNI space. Options: lin, nl. If 'lin' transformation files must end with '_affine.h5'. If 'nl', files must be a compressed nifti file that ends with '_warp.nii.gz'. Transformation files must indicate the target coordinate space of the transform: '_target-<T1/MNI>_<affine/warp>.<h5/nii.gz>
```
    --user-t1mni
```

Boolean flag to use user provided brain mask:
```
    --user-brainmask
``` 


#### MRI Segmentation
Method to segment mask from MRI: default=ANTS, currently this is the only implemented method.
```
    --segmentation-method
```

Anatomic label images to use as priors for Atropos segmentation. By default, if not set by user and template is the default ICBM152c, then APPIAN uses the GM/WM/CSF probabilistic segmentations of ICBM152c template. Users providing their own templates can specify their own priors.

```
--ants-atropos-priors
```

Weight to give to priors in Atropos segmentation (Default=0.5)
```
    --ants-atropos-prior-weighting
```

##### If you use the MRI preprocessing module, please cite the following :

###### Brain mask extraction:
Avants, B.B., Tustison, N. and Song, G., 2009. Advanced normalization tools (ANTS). Insight j, 2, pp.1-35.

###### Non-uniformity correction
Avants, B.B., Tustison, N. and Song, G., 2009. Advanced normalization tools (ANTS). Insight j, 2, pp.1-35.


### 4.3 [Coregistration]<a name="coregistration"></a> 
Rigid coregistration of PET image to T1 MRI. 

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

### 4.4 [Masking]<a name="masking"></a>

Create ROI mask volumes for partial-volume correction, quantification (tracer-kinetic analysis), and reporting of results.

The pipeline uses up to three different types of masks: a reference region mask to define a region of non-specific radiotracer binding for tracer kinetic analysis, masks for the PVC algorithms, masks to define the regions from which the user wishes to extract quantitative values (kBq/ml, BPnd, Ki, etc.). Moreover, these masks can be derived from multiple sources: manually drawn ROI for each T1 MRI, classification produced by CIVET/ANIMAL, stereotaxic atlas, user-defined regions in native PET space (e.g., region of infarcted tissue from ischemic stroke).

  #### Masking options: PVC

    --pvc-label-space=PVC_LABEL_SPACE
                        Coordinate space of labeled image to use for quant.
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

    --tka-label-space=quant_LABEL_SPACE
                        Coordinate space of labeled image to use for quant.
                        Options: [pet/t1/stereo]
    --tka-label-img=quant_LABEL_IMG
                        Options: 1. ICBM MNI 152 atlas:
                        <path/to/labeled/atlas>, 2. Stereotaxic atlas and
                        template: path/to/labeled/atlas
                        /path/to/atlas/template 3. Internal classification
                        method (antsAtropos) 4. String that identifies labels
                        in anat/ directory to be used as mask
    --tka-label=quant_LABELS
                        List of label values to use for quant
    --tka-label-erosion=quant_ERODE_TIMES
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
                        Coordinate space of labeled image to use for quant.
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


### 4.5 [Partial-Volume Correction]<a name="pvc"></a>
Partial-volume correction of point-spread function of PET scanner.

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

### 4.6 [Quantification](https://github.com/APPIAN-PET/APPIAN/blob/master/Tracer_Kinetic/README.md) 
Create quantificative (or pseudo-quantitative) parametric images with tracer-kinetic analysis, SUV, or SUVR methods. 

### 4.7 [Reporting of Results](https://github.com/APPIAN-PET/APPIAN/blob/master/Results_Report/README.md) 
Regional mean values for each ROI of results mask volumes are saved to .csv files.

### 4.8 [Quality Control](https://github.com/APPIAN-PET/APPIAN/blob/master/Quality_Control/README.md) 
Quality control metrics are calculated for each image volume and each processing stage.

### 4.9 [Dashboard GUI](https://github.com/APPIAN-PET/APPIAN/blob/master/Quality_Control/README.md) 
Web browser-based graphical-user interface for visualizing results.


## 5. [APPIAN Outputs]
APPIAN will create the target directory you specify with the "-t" or "--target" option. 

Within the target directory you will find a subdirectory called "preproc". This contains all of the intermediate files produced by APPIAN. APPIAN is built using Nipype, which defines a network of nodes (also called a workflow). The ouputs of upstream nodes are passed as inputs to downstream nodes. A directory within preproc/ is created for each node that is run as a part of the workflow. Given that the nodes that APPIAN will run will change as a function of user inputs, the outputs you find in preproc will change accordingly. 

For all nodes that are responsible for running a command in the terminal, there will be a text file called "command.txt" in the node's output directory It is also useful to note that Nipype will always create a "\_report" subdirectory within a particular node's output directory. In this "\_report" directory, you will find a text file called "report.rst". This text file describes the inputs and outputs to this node. This can help you debug APPIAN if for some reason a node fails to run. 

Within preproc you will find directories named after each scan APPIAN has processed, with the form: _args_run<run>.task<task>.ses<ses>.sid<sub>. This will contain a variety of results including the results report, automated QC, dashboard xml for that particular scan. 

You will also find several other important subdirectories in preproc/. In particular: 
```
	initialization --> centered version of initial PET image, 3D contatenated version of initial PET 
	masking --> contains the labelled images used for the PVC, quantification, and results report stages, respectively
	pet-coregistration --> transformation file from PET to MRI, and vice versa. 3D PET image in MRI space
	mri --> mri normalized into icbm152 space, brain mask in stereotaxic and MRI native space, MRI segmentation
	quantification  --> parametric image produced by quantification stage
```

The reason why there APPIAN stores the outputs in these two ways is a bit complicated and has to do with how Nipype works. Basically, the results that are stored in a subdirectory name after a processing stage, e.g., "pet-coregistration" or "quantification", are part of a sub-workflow within the larger APPIAN workflow and get their own subdirectory named after the sub-workflow.
	
When APPIAN has finished running it copies the most important outputs from preproc/ into your target directory. To save space, it may be helpful to delete the files in preproc/. However, if you decide to do so, it you should only delete the actual brain image files, while keeping all the directories and text files. This will keep the documentation about exactly what was run to generate your data.   


## 6 [Atlases](https://github.com/APPIAN-PET/APPIAN/blob/master/Atlas/README.md)
Atlases in stereotaxic space can be used to define ROI mask volumes. Atlases are assumed to be defined on MNI152 template. However, users can also use atlases specified on other templates (e.g., Colin27) by specifying both atlas volume and the template volume on which this atlas is defined. 

## 7. Examples  <a name="example"></a>

### Running APPIAN on subset of scans
By default, APPIAN will run on all the scans it can identify in the source directory. However, you may want to run APPIAN on a subset of your scans. You can do this by setting which subjects, sessions, tasks, and runs you wish to process with APPIAN.

For example, if your study contains 3 sessions "baseline", "treatment", "follow-up". You can then run APPIAN only on the, for example, "treatment" and "follow-up" images :

```
python3 /opt/APPIAN/Launcher.py -s /path/to/data -t /path/to/output --sessions baseline follow-up
```

The same can be done for : subjects using the "--subjects <subject to process>" flag, tasks with "--tasks <tasks to process>", and run with "--runs <runs to process>".


### Partial-volume correction
To use partial-volume correction (PVC), you must also specify the FWHM of the scanner you are using. The PVC method is specified with the "--pvc-method <PVC Method>" option. APPIAN will use the string you specify for <PVC Method> to find a correspdoning python module in "Partial_Volume_Correction/methods/pvc_method_<PVC Method>.py". 
	
Moreover, you may wish to use a specific labeled image to contstrain the PVC algorithm. There are multiple types of labeled images that you can select with the "--pvc-label-img" option (see the [masking](#masking) section for more information). If no such label is specified by the user, then APPIAN will by default use a GM/WM/CSF segmentation of the input T1 MRI.
	
```
python3 /opt/APPIAN/Launcher.py -s <SOURCE DIR> -t <TARGET DIR> --threads <N Threads> --pvc-label-img <label image> <label template> --pvc-label <list of labels> --fwhm <Z FWHM> <Y FWHM> <X FWHM> --pvc-method <PVC Method> 
```
For instance, let's say your images were acquired using the HR+ scanner (which has a FWHM of about 6.5 6.5 6.5) and you want to use the Geometric Transfer Matrix method (GTM). Let's say you want to use a predefined labeled image in the /anat directory of your source directory of the form sub-<subject>/ses-<session>/anat/sub-<subject>_ses-<session>_variant-segmentation_dseg.mnc. You would use : 

```
python3 /opt/APPIAN/Launcher.py -s /path/to/data -t /path/to/output --threads 2 --pvc-label-img variant-segmentation --fwhm 6.5 6.5 6.5 --pvc-method GTM
```

### Quantification
To use a quantification method (e.g., tracer-kinetic analysis), you use the option --quant-method <Quantification Method>. You can also use the "--tka-method" flag, but this flag is gradually being depreated in favor of "--quant-method".

Quantification methods may require additional options, such as "--start-time <start time>" for graphical tracer-kinetic analysis methods. 
	
You may also need to either define a reference region or use arterial sampling. To use arterial sampling, you must set the flag "--arterial" and have a arterial inputs files in the [dft](http://www.turkupetcentre.net/formats/format_dft_1_0_0.pdf) file format. 
On the other hand, you can use a labeled image to define a reference region. There are multiple types of labeled images that you can select with the "--tka-label-img" option (see the [masking](#masking) section for more information). If no such label is specified by the user, then APPIAN will by default use the WM mask from a GM/WM/CSF segmentation of the input T1 MRI. Additionally, the "--quant-labels-ones-only" is useful because it will set all of the labels you set with "--quant-label <list of labels>" to 1. 
	
```
python3 /opt/APPIAN/Launcher.py -s <SOURCE DIR> -t <TARGET DIR> --threads <N Threads> --quant-label-img <label image> <label template> --quant-label <list of labels> --start-time <Start time in Min.> --quant-labels-ones-only --quant-method <Quantification Method> 
```
	
For example, say you have FDG images and wish to use the Patlak-Gjedde plot method for tracer-kinetic analysis. In order to calculate glucose metabolism, you need to specify the lump constant (LC) and concentration of native substantce (Ca). Let's also imagine that you have a you use an atlas in MNI152 space that you want to use to specify a reference region in the cerebellum and where the two hemispheres of the cerebellum have labels 67 and 76, respectively. 

```
python3 /opt/APPIAN/Launcher.py -s <SOURCE DIR> -t <TARGET DIR> --threads 6 --quant-label-img /opt/APPIAN/Atlas/MNI152/dka.mnc --quant-label 67,76 --quant-labels-ones-only --start-time 5 --Ca 5.0 --LC 0.8  --quant-method pp 
```

To do the same analysis but with an arterial input file for each subject (instead of a reference region):

```
python3 /opt/APPIAN/Launcher.py -s <SOURCE DIR> -t <TARGET DIR> --threads 6 --arterial --start-time 5 --Ca 5.0 --LC 0.8  --quant-method pp 
```

Quantification [usuallly with tracer kinetic analysis (quant)] allows for the quantification of physiological or biological parameters from the radiotracer concentrations measured in the PET image. The appropriate quant method will depend on the radiotracer. Certain models, e.g., the Logan Plot and Simplified Reference Tissue Model (SRTM), are only suitable for radiotracers that are reversibly bound to the tissue. Currently only three quant methods are implemented: Logan plot, Patlak-Gjedde plot, and the SRTM.

#### Quantification options:
    --tka-method=quant_METHOD
                        Method for performing tracer kinetic analysis (quant):
                        lp, pp, srtm.
    --k2=quant_K2         With reference region input it may be necessary to
                        specify also the population average for regerence
                        region k2
    --thr=quant_THR       Pixels with AUC less than (threshold/100 x max AUC)
                        are set to zero. Default is 0%
    --max=quant_MAX       Upper limit for Vt or DVR values; by default max is
                        set pixel-wise to 10 times the AUC ratio.
    --min=quant_MIN       Lower limit for Vt or DVR values, 0 by default
    --t3max=quant_T3MAX   Upper limit for theta3, 0.01 by default
    --t3min=quant_T3MIN   Lower limit for theta3, 0.001 by default
    --nBF=quant_NBF       Number of basis functions.
    --filter            Remove parametric pixel values that over 4x higher
                        than their closest neighbours.
    --reg-end=quant_END   By default line is fit to the end of data. Use this
                        option to enter the fit end time (in min).
    --y-int=quant_V       Y-axis intercepts time -1 are written as an image to
                        specified file.
    --num=quant_N         Numbers of selected plot data points are written as an
                        image.
    --Ca=quant_CA         Concentration of native substrate in arterial plasma
                        (mM).
    --LC=quant_LC         Lumped constant in MR calculation; default is 1.0.
    --density=quant_DENSITY
                        Tissue density in MR calculation; default is 1.0 g/ml.
    --arterial          Use arterial input input.
    --start-time=quant_START_TIME
                        Start time of either regression in MTGA or averaging
                        time for SUV.
    --end-time=quant_END_TIME
                        End time for SUV average.
    --body-weight=BODY_WEIGHT
                        Either name of subject body weight (kg) in header or
                        path to .csv file containing subject names and body
                        weight (separated by comma).
    --radiotracer-dose=RADIOTRACER_DOSE
                        Either name of subject's injected radiotracer dose
                        (MBq) in header or path to .csv file containing
                        subject names and injected radiotracer dose (MBq).
    --tka-type=quant_TYPE
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

### Results report
APPIAN produces a .csv file with mean regional values for the results labels. If you will not use the results report produced by APPIAN, you can use the "--no-results-report".

As with PVC and quantification, the results labels are defined using the option "--results-label-img". By default, APPIAN will use all of the integer values in the label image.

For example, if you want to use a segmentation defined on your own template of Alzheimer's patients defined in T1 native space, you would use :
```
python3 /opt/APPIAN/Launcher.py -s <SOURCE DIR> -t <TARGET DIR> --results-label-img /path/to/segmentation.mnc --results-label-space t1
```
Similarly, if you want to create the results report with an atlas that is not in MNI space, but only for a single label value (i.e., 4), you would use :
```
python3 /opt/APPIAN/Launcher.py -s <SOURCE DIR> -t <TARGET DIR> --results-label-img /path/to/atlas.mnc /path/to/template.mnc --results-label 4
```
The ROI masks described [here](https://github.com/APPIAN-PET/APPIAN/blob/master/Masking/README.md) are applied on all images output from the pipeline to extract descriptive statistics for each of these regions in each of the output images. The descriptive statistics for each region and image pair are written to .csv files. The .csv file format was selected because it is easy to import into statistical packages (particularly R and Python) for further statistical analysis. 

You can find the results stored in the target directory in "results/". Here you will see multiple sub-directories that are named "results_<processing stage><_4d>". The directories with <_4d> have the TACs, while those without contain only 3D results (e.g., parametric values derived with tracer-kinetic analysis). In each of these there will be another subdirctory for each PET scan that was processed and these in turn contain a .csv with the mean regional values.

The results directory it will look something like this :
```
results_initialization/:
_args_run01.task01.ses01.sid01  _args_run01.task01.ses01.sid02

results_initialization_4d/:
_args_run01.task01.ses01.sid01  _args_run01.task01.ses01.sid02

results_pvc/:
_args_run01.task01.ses01.sid01  _args_run01.task01.ses01.sid02

results_pvc_4d/:
_args_run01.task01.ses01.sid01  _args_run01.task01.ses01.sid02

results_quantification/:
_args_run01.task01.ses01.sid01  _args_run01.task01.ses01.sid02
```
The .csv files in these subdirectories will have the following format : 

![csv](https://github.com/APPIAN-PET/APPIAN/blob/master/Results_Report/csv_example.png)

####  Results reporting options:
    --no-group-stats    Don't calculate quantitative group-wise descriptive
                        statistics.

# Masking <a name="masking"></a>
The pipeline uses up to three different types of masks: a reference region mask to define a region of non-specific radiotracer binding for tracer kinetic analysis, masks for the PVC algorithms, masks to define the regions from which the user wishes to extract quantitative values (kBq/ml, BPnd, Ki, etc.). Moreover, these masks can be derived from multiple sources: manually drawn ROI for each T1 MRI, classification produced by CIVET/ANIMAL, stereotaxic atlas, user-defined regions in native PET space (e.g., region of infarcted tissue from ischemic stroke).

  #### Masking options: PVC

    --pvc-label-space=PVC_LABEL_SPACE
                        Coordinate space of labeled image to use for quant.
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

    --tka-label-space=quant_LABEL_SPACE
                        Coordinate space of labeled image to use for quant.
                        Options: [pet/t1/stereo]
    --tka-label-img=quant_LABEL_IMG
                        Options: 1. ICBM MNI 152 atlas:
                        <path/to/labeled/atlas>, 2. Stereotaxic atlas and
                        template: path/to/labeled/atlas
                        /path/to/atlas/template 3. Internal classification
                        method (antsAtropos) 4. String that identifies labels
                        in anat/ directory to be used as mask
    --tka-label=quant_LABELS
                        List of label values to use for quant
    --tka-label-erosion=quant_ERODE_TIMES
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
                        Coordinate space of labeled image to use for quant.
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
