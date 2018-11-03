# APPIAN User Guide

# Table of Contents
1. [Overview](#overview) \
	1.1 [Base Options](#options) \
	1.2 [MRI Preprocessing](#mri) \
	1.3 [Coregistration](#coregistration) \
	1.4 [Masking](#masking) \
	1.5 [Partial-Volume Correction](#pvc) \
	1.6 [Reporting of Results](#results) \
	1.7 [Quality Control](#qc)
2. [File Formats](#fileformat)
3. [Useage](#useage)
4. [Examples](#example)


## Pipeline Overview  <a name="overview"></a>

## Base User Options  <a name="options"></a>
APPIAN has lots of options, mostly concerned with the types of masks you want to use, and the parameters to pass to the PVC and TKA algorithms. Here is a list of the available options, a more detailed explanation will be written up soon. Important to note is that the only mandatory options are a source directory with PET images (-s), a target directory where the outputs will be stored (-t), the list of sessions during which the scans were acquired (-sessions). While it may be useful to run APPIAN with the default options to confirm that it is running correctly on your system, this may not produce quantitatively accurate output values for your particular data set.

####  File options (mandatory):
    -s SOURCEDIR, --source=SOURCEDIR, --sourcedir=SOURCEDIR
                        Input file directory
    -t TARGETDIR, --target=TARGETDIR, --targetdir=TARGETDIR
                        Directory where output data will be saved in
    --radiotracer=ACQ, --acq=ACQ
                        Radiotracer
    -r REC, --rec=REC   Reconstruction algorithm
    --sessions=SESSIONLIST comma-separated list of sessions

#### File options (Optional):
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
Simon Fristed Eskildsen, Pierrick Coupé, Vladimir Fonov, José V. Manjón, Kelvin K. Leung, Nicolas Guizard, Shafik N. Wassef, Lasse Riis Østergaard and D. Louis Collins: “BEaST: Brain extraction based on nonlocal segmentation technique”, NeuroImage, Volume 59, Issue 3, pp. 2362–2373.
http://dx.doi.org/10.1016/j.neuroimage.2011.09.012

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

### Masking <a name="masking"></a>
The pipeline uses up to three different types of masks: a reference region mask to define a region of non-specific radiotracer binding for TKA, masks for the PVC algorithms, masks to define the regions from which the user wishes to extract quantitative values (kBq/ml, BPnd, Ki, etc.). Moreover, these masks can be derived from multiple sources: manually drawn ROI for each T1 MRI, classification produced by CIVET/ANIMAL, stereotaxic atlas, user-defined regions in native PET space (e.g., region of infarcted tissue from ischemic stroke).

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



### Quantification
Tracer kinetic analysis (TKA) allows for the quantification of physiological or biological parameters from the radiotracer concentrations measured in the PET image. The appropriate TKA method will depend on the radiotracer. Certain models, e.g., the Logan plot and simplified reference tissue model, are only suitable for radiotracers that are reversibly bound to the tissue. Currently only three TKA methods are implemented: Logan plot, Patlak-Gjedde plot, and the simplified reference tissue model.

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


### Reporting of results <a name="results"></a>
The ROI masks described in section 1.b are applied on all images output from the pipeline to extract descriptive statistics for each of these regions in each of the output images. The descriptive statistics for each region and image pair are written to .csv files. The .csv file format was selected because it is easy to import into statistical packages (particularly R and python) for further statistical analysis. 

####  Results reporting options:
    --no-group-stats    Don't calculate quantitative group-wise descriptive
                        statistics.


### Quality control <a name="qc"></a>
Quality control is a crucial step of any automated pipeline. It is essential that the user be able to easily confirm that the pipeline has performed as expected and identify any problematic subjects or processing steps. 
Towards the end of facilitating rigorous quality control, we are implementing qualitative and quantitative quality control for every major processing step. The user will be able to peruse all output images in GIF format to verify that the images appear as expected (e.g., that there is no gross error in co-registration). Users will also be able to open the full 3D volumes using the BrainBrowser interface. 
Quantitative quality control functions by calculating a metric that attempts to measure how accurately the processing step in question was performed. For example, the accuracy of the co-registration is measured using a similarity metric between the PET and MRI image. A single metric is not by itself very informative, because we do not know what value this metric should be. However it is possible to compare the metrics of all subjects at a given processing step and find outliers within these. Thus if most of the subjects have a similarity metric of 0.6 for their co-registered PET and MRI, then a subject with a similarity metric of 0.1 would indicate that this subject had probably failed this processing step and should be further scrutinized using qualitative quality control (visual inspection).  

####  Quality control options:
    --no-group-qc       Don't perform quantitative group-wise quality control.
    --test-group-qc     Perform simulations to test quantitative group-wise
                        quality control.

## File Formats  <a name="fileformat"></a>
APPIAN uses the BIDS file format specification for PET:

### Required
#### PET (native PET space)
sub-<participant_label>/[_ses-<session_label>/]pet/sub-<participant_label>[_ses-<session_label>]_task-<task_label>[_acq-<label>][_rec-<label>][_run-<index>]_pet.nii[.gz]

#### T1w (native T1 space) :
'sub-%s/_ses-%s/anat/sub-%s_ses-%s*T1w.mnc'

### Optional
#### Linear Transform from T1 native to stereotaxic: 
'sub-%s/_ses-%s/transforms/sub-%s_ses-%s*target-MNI_affine.xfm

#### Brain mask (stereotaxic space): 
sub-%s/_ses-%s/mask/sub-%s_ses-%s*_space-mni_brainmask.mnc

#### T1 Segmentation: 
sub-<participant-label>/_ses-<session-label>/mask/sub-<participant-label>_ses-<session-label>_space-mni_variant-seg_dtissue.mnc'

Although BIDS is based on the Nifti file format, APPIAN will accept both MINC and Nifti inputs. All Nifti files are converted to MINC for further processing. 

## Usage <a name="useage"></a>

### Launching APPIAN
APPIAN is a Python program (Python 2.7 to be specific) that is launched using a command of the form:

python2.7 <path to APPIAN directory>/Launcher.py <list of options> <subject names>

When running APPIAN in a Docker container (described in detail in the following section), the APPIAN directory is located in “/opt/APPIAN/”:

python2.7 /opt/APPIAN/Launcher.py <list of options> <subject names>
Running APPIAN with Docker
APPIAN is run in a Docker container. To launch a container based on an image is to run:

Docker run -it <name of image>:<image tag>

or in our case:

docker run -it tffunck/appian:latest

Here the “-it” flag means that the container is launched in interactive mode. That is, you will be dropped into a bash shell within the filesystem and will be able to do most of the typical bash/unix stuff you normally do. You can also run the container non-interactively by dropping the “-it” flag and adding a bash command at the end of the line, as follows:

docker run <name of image>:<image tag> <your bash command>

or in our case:

docker run tffunck/appian:latest ls /opt
bin
doc
etc
...

APPIAN is intended to be flexible and applicable in a wide variety of situations, however this also means that it has many options that have to be specified by the user. Typing out these options in the command line would quickly become tedious, so it is more convenient to put the command you will use to launch the pipeline, along with all of the desired options, into a bash script (basically just a text file that you can run from the command line). For the example below, “run.sh” is just such a bash script (note that you can name your script whatever you like). Therefore, in the current example, the command would look something like 

python2.7 /opt/APPIAN/Launcher.py -s /path/to/pet/images -t /path/to/output/dir -p <study prefix> -c </path/to/civet/output> <subject names>


By default, you cannot access any of the data on your computer from the filesystem of the Docker container. To access your data from the Docker container it is necessary to mount the directory on your computer in the Docker container. This sounds complicated, but it’s actually very simple. All you have to do is pass the “-v” flag (“v” for volume) to the Docker “run” command, followed by the absolute path to the directory you want to mount, a colon (“:”),  and the absolute path to the location where you want to mount it. Let’s say you data is stored in “/path/to/your/data” and, for simplicity, you want to mount it to a path called “/path/to/your/data” in the Docker container. To run your Docker container with this path mounted, you would just have to run:

docker run -it -v /path/to/your/data:/path/to/your/data  tffunck/appian:latest

As mentioned above,  there are two ways in which to run APPIAN, either interactively or by passing a command to the “docker run” command. Assuming that you put your “run.sh” script into the same directory as your data, “/path/to/your/data”, then you would run something like the following commands:

docker run -it -v /path/to/your/data:/path/to/your/data tffunck/appian:latest
\#You are now in the docker container
cd /path/to/your/data 
./run.sh

Alternatively, you can also run the pipeline through a non-interatctive docker container, like so:

docker run /path/to/your/data:/path/to/your/data tffunck/appian:latest /path/to/your/data/run.sh

Either method will give you the same results, it’s up to you and what you find more convenient. 

## Example use cases  <a name="example"></a>

### FDG
FDG is a non-reversibly bound tracer, meaning that once it binds to its target receptor (i.e., gets transported inside the cell body) it will not become unbound for the duration of the scan. The Patlak-Gjedde plot (--tka-method "pp") is the standard TKA method for analyzing such images. The Patlak-Gjedde plot can be used to calculate the glucose metabolism rate using two variables: the lumped constant (flag: --LC) and concentration of native substrate in arterial plasma (flag: --Ca). The Turku Pet Centre has a useful description here with standard values for LC. The start time (minutes) is set to when the amount of radiotracer in the blood reaches equilibrium with that in the tissue.
   
Example:
--tka-method "pp" --Ca 5.0 --LC 0.8 --start-time 1





 

## References
Collins, et al. 1994.  J. Comput. Assist. Tomogr. 18 (2), 192–205. 


