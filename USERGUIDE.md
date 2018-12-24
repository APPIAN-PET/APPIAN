# APPIAN User Guide

# Table of Contents
1. [Quick Start](#quickstart)
2. [File Formats](#fileformat) \
	2.1 [Nifti](#nifti) \
	2.2 [MINC](#minc)
4. [Useage](#useage)
5. [Examples](#example)
6. [Overview](#overview) \
	5.1 [Base Options](#options) \
	5.2 [MRI Preprocessing](#mri) \
	5.3 [Coregistration](#coregistration) \
	5.4 [Masking](#masking) \
	5.5 [Partial-Volume Correction](#pvc) \
	5.6 [Reporting of Results](#results) \
	5.7 [Quality Control](#qc) 
7. [Atlases](#atlases)




## Quick Start

### Download CIMBI Open Data  <a name="quickstart"></a>
Download the data from https://openneuro.org/datasets/ds001421/versions/00002 or using the Amazon web service command line interface (AWS CLI):

```
apt install awscli
aws s3 sync --no-sign-request s3://openneuro.org/ds001421 ds001421-download/
```

### Format data
The data may need to be reformatted slightly to have the following structure. 
As of version 00002 of the Cimbi data set, you can fix it using the following commands: 

	find cimbi-test/ -name "*{nii,json}*" -exec sh -c 'x="{}"; f2=`echo $x | sed 's/ses_/ses-/g'`;  mv $x $f2' \;

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
	docker run -v  </path/to/cimbi/dir>:"/path/to/cimbi/dir" -v </path/to/cimbi/dir/out_cimbi>:"/path/to/cimbi/dir/out_cimbi" tffunck/appian:latest bash -c "python2.7 /opt/APPIAN/Launcher.py -s "/path/to/cimbi/dir" -t "/path/to/cimbi/dir/out_cimbi" ";

#### PVC
	docker run -v </path/to/cimbi/dir>:"/path/to/cimbi/dir" -v </path/to/cimbi/dir/out_cimbi>:"/path/to/cimbi/dir/out_cimbi" tffunck/appian:latest bash -c "python2.7 /opt/APPIAN/Launcher.py --fwhm 3 3 3 --pvc-method 'GTM' --no-results-report -s /path/to/cimbi/dir -t "/path/to/cimbi/dir/out_cimbi" --sessions 01  01";

#### PVC + Quantification
	docker run -v </path/to/cimbi/dir>:"/path/to/cimbi/dir" -v </path/to/cimbi/dir/out_cimbi>:"/path/to/cimbi/dir/out_cimbi" tffunck/appian:latest bash -c "python2.7 /opt/APPIAN/Launcher.py --tka-method lp --tka-label 3 --results-label-erosion 5 --fwhm 3 3 3 --pvc-method 'GTM' --no-results-report -s "/path/to/cimbi/dir" -t "/path/to/cimbi/dir/out_cimbi"  ";

## File Formats  <a name="fileformat"></a>

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
              sub-01_ses-01_pet.nii
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
             sub-02_ses-01_pet.nii
        _ses-02/
             ...


#### Required
##### PET (native PET space)
`sub-<participant_label>/[_ses-<session_label>/]pet/sub-<participant_label>[_ses-<session_label>]_task-<task_label>[_acq-<label>][_rec-<label>][_run-<index>]_pet.nii[.gz]`

##### PET Header
`sub-<participant_label>/[_ses-<session_label>/]pet/sub-<participant_label>[_ses-<session_label>]_task-<task_label>[_acq-<label>][_rec-<label>][_run-<index>]_pet.json`

##### T1w (native T1 space) :
`sub-%s/_ses-%s/anat/sub-%s_ses-%s*T1w.mnc`

#### Optional
##### Linear Transform from T1 native to stereotaxic: 
`sub-%s/_ses-%s/transforms/sub-%s_ses-%s*target-MNI_affine.xfm`

##### Brain mask (stereotaxic space): 
`sub-%s/_ses-%s/mask/sub-%s_ses-%s*_space-mni_brainmask.mnc`

##### T1 Segmentation: 
`sub-<participant-label>/_ses-<session-label>/mask/sub-<participant-label>_ses-<session-label>_space-mni_variant-seg_dtissue.mnc`

Although BIDS is based on the Nifti file format, APPIAN will accept both MINC and Nifti inputs. All Nifti files are converted to MINC for further processing. 

### MINC
Users can opt to use MINC2 files instead of Nifti files. If the user provides MINC files, these must either contain the certain variables in the headers of the PET images or contain a BIDS-style header that has the format described below to accompany the PET files.

Required variables for MINC header ```<time>, <time-widths>, <time:units>, <acquisition:radionuclide>, <acquisition:radionuclide_halflife> ```.

```python
  {
    	"Info": {
    		"Tracer": {
      			"Isotope": ["C-11"]
			#APPIAN has a library of standard Isotopes that it can use to determine radionuclide halflife
			#Otherwise you can specify it using "Info":"Halflife" (units=seconds)
			"Halflife" : 100
      		}
     	}
    	"Time" : {
        	"FrameTimes": {
            		"Units": ["m", "m"],
            		"Values":[[14,64]]
      		}
    	}
    }
```
## Usage <a name="useage"></a>

### Launching APPIAN
APPIAN is a Python program (Python 2.7 to be specific) that is launched using a command of the form:

```
python2.7 <path to APPIAN directory>/Launcher.py <list of options> <subject names>
```

The <subject names> arguments are optional. If you do not provide spedific subject IDs, the APPIAN will be run on all subjects found in the source directory. When running APPIAN in a Docker container (described in detail in the following section), the APPIAN directory is located in “/opt/APPIAN/”:

```
python2.7 /opt/APPIAN/Launcher.py <list of options> <subject names>
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
python2.7 /opt/APPIAN/Launcher.py -s /path/to/pet/images -t /path/to/output/dir -p <study prefix> -c </path/to/civet/output> <subject names>
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

## Example use cases  <a name="example"></a>

### FDG
FDG is a non-reversibly bound tracer, meaning that once it binds to its target receptor (i.e., gets transported inside the cell body) it will not become unbound for the duration of the scan. The Patlak-Gjedde plot (`--tka-method "pp"`) is the standard TKA method for analyzing such images. The Patlak-Gjedde plot can be used to calculate the glucose metabolism rate using two variables: the lumped constant (flag: `--LC`) and concentration of native substrate in arterial plasma (flag: `--Ca`). The Turku Pet Centre has a useful [description for LC here][link_turkuLC] with standard values from the literature. The start time (minutes) is set to when the amount of radiotracer in the blood reaches equilibrium with that in the tissue.
   
Example:
```
--tka-method "pp" --Ca 5.0 --LC 0.8 --start-time 1
```

## Pipeline Overview  <a name="overview"></a>

## Base User Options  <a name="options"></a>
APPIAN has lots of options, mostly concerned with the types of masks you want to use, and the parameters to pass to the PVC and TKA algorithms. Here is a list of the available options, a more detailed explanation will be written up soon. Important to note is that the only mandatory options are a source directory with PET images (`-s`), a target directory where the outputs will be stored (`-t`), the list of sessions during which the scans were acquired (`-sessions`). While it may be useful to run APPIAN with the default options to confirm that it is running correctly on your system, this may not produce quantitatively accurate output values for your particular data set.

####  File options (mandatory):
    -s SOURCEDIR, --source=SOURCEDIR, --sourcedir=SOURCEDIR
                        Input file directory
    -t TARGETDIR, --target=TARGETDIR, --targetdir=TARGETDIR
                        Directory where output data will be saved in


#### File options (Optional):
    --radiotracer=ACQ, --acq=ACQ
                        Radiotracer
    -r REC, --rec=REC   Reconstruction algorithm
    --sessions=SESSIONLIST comma-separated list of sessions
    --tasks=TASKLIST    comma-separated list of conditions or scans
    --no-group-level    Run group level analysis
    --no-scan-level     Run scan level analysis
    --img-ext=IMG_EXT   Extension to use for images.
    --analysis-space=ANALYSIS_SPACE
                        Coordinate space in which PET processing will be
                        performed (Default=pet)
    --threads=NUM_THREADS
                        Number of threads to use. (defult=1)
    --stereotaxic-template=TEMPLATE
                        Template image in stereotaxic space
####  Surface options:
    --surf              Uses surfaces
    --surf-space=SURFACE_SPACE
                        Set space of surfaces from : "pet", "t1", "icbm152"
                        (default=icbm152)
    --surf-ext=SURF_EXT
                        Extension to use for surfaces

### MRI Preprocessing <a name="mri"></a>
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

### Coregistration <a name="coregistration"></a>
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

### Masking <a name="masking"></a>
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
                        Label values to use for pvc
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
                        Label values to use for TKA
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
                        Label values to use for results
    --results-label-erosion=RESULTS_ERODE_TIMES
                        Number of times to erode label
    --results-labels-brain-only
                        Mask results labels with brain mask
    --results-labels-ones-only
                        Flag to signal threshold so that label image is only 1s and 0s


### Partial-volume correction <a name="pvc"></a>
Partial-volume correction (PVC) is often necessary to account for the loss of resolution in the image due to the point-spread function of the PET scanner and the fact that multiple tissue types may contribute to a single PET voxel. While performing PVC is generally a good idea, this is especially true if the user is interested in regions that are less than approximately 2.5 times the full-width at half-maximum (FWHM) resolution of the scanner. 

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

### Quantification
Tracer kinetic analysis (TKA) allows for the quantification of physiological or biological parameters from the radiotracer concentrations measured in the PET image. The appropriate TKA method will depend on the radiotracer. Certain models, e.g., the Logan Plot and Simplified Reference Tissue Model (SRTM), are only suitable for radiotracers that are reversibly bound to the tissue. Currently only three TKA methods are implemented: Logan plot, Patlak-Gjedde plot, and the SRTM.

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

### Reporting of results <a name="results"></a>
The ROI masks described in *section 5.4* are applied on all images output from the pipeline to extract descriptive statistics for each of these regions in each of the output images. The descriptive statistics for each region and image pair are written to .csv files. The .csv file format was selected because it is easy to import into statistical packages (particularly R and Python) for further statistical analysis. 

####  Results reporting options:
    --no-group-stats    Don't calculate quantitative group-wise descriptive
                        statistics.


### Quality control <a name="qc"></a>
Quality control is a crucial step of any automated pipeline. It is essential that the user be able to easily confirm that the pipeline has performed as expected and identify any problematic subjects or processing steps. 
In order to facilitate rigorous quality control, we are implementing qualitative and quantitative quality control for every major processing step. The user will be able to peruse all output images in GIF format to verify that the images appear as expected (e.g., that there is no gross error in co-registration). Users will also be able to open the full 3D volumes using the BrainBrowser web interface. 
Quantitative quality control functions by calculating a metric that attempts to measure how accurately the processing step in question was performed. For example, the accuracy of the co-registration is measured using a similarity metric between the PET and MRI image. A single metric is not by itself very informative, because we do not know what value this metric should be. However it is possible to compare the metrics of all subjects at a given processing step and find outliers within these. Thus if most of the subjects have a similarity metric of 0.6 for their co-registered PET and MRI, then a subject with a similarity metric of 0.1 would indicate that this subject had probably failed this processing step and should be further scrutinized using qualitative quality control (visual inspection).  

####  Quality control options:
    --no-group-qc       Don't perform quantitative group-wise quality control.
    --test-group-qc     Perform simulations to test quantitative group-wise
                        quality control.

## Atlases <a name="atlases"></a>
### Please cite the following papers if you use one of the available atlases.
### Don't hesitate to make pull requests to add more atlases! 
#### MNI 152 Template
##### Automated Anatomic Labelling Atlas
N. Tzourio-Mazoyer, B. Landeau, D. Papathanassiou, F. Crivello, O. Etard, N. Delcroix, Bernard Mazoyer, M. Joliot (2002). "Automated anatomical labeling of activations in SPM using a macroscopic anatomical parcellation of the MNI MRI single-subject brain". NeuroImage 15: 273-289.
#### Colin27 Template
##### Desikan Killiany Atlas 
Desikan, R. S., Ségonne, F., Fischl, B., Quinn, B. T., Dickerson, B. C., Blacker, D., … Killiany, R. J. (2006). An automated labeling system for subdividing the human cerebral cortex on MRI scans into gyral based regions of interest. NeuroImage, 31(3), 968–980. doi:10.1016/j.neuroimage.2006.01.021

[link_bidsio]: http://bids.neuroimaging.io/
[link_turkuLC]: http://www.turkupetcentre.net/petanalysis/lumped_constant.html
