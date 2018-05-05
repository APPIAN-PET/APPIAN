# APPIAN User Guide

# Table of Contents
1. Overview \
	1.1 [Coregistration](#coregistration) \
	1.2 [Masking](#masking) \
	1.3 [Partial-Volume Correction](#pvc) \ 
	1.4 [Reporting of Results](#results) \
	1.5 [Quality Control](#qc)  \
2. [File Formats](#fileformat) \
3. [Useage](#useage) \
4. [Examples](#example) \
5. [User Options](#options) \

## Pipeline Overview
### Coregistration <a name="coregistration"></a>
The first processing step is the coregistration of the T1 image to the PET image. The co-registration algorithm is based on minctracc and proceeds hierarchically by performing iterative co-registrations at progressively finer spatial scales (Collins 1993). Two iterations of the co-registration are performed: one using binary masks of the PET brain mask and the T1 brain mask, the second iteration without any binary mask.


### Masking <a name="masking"></a>
The pipeline uses up to three different types of masks: a reference region mask to define a region of non-specific radiotracer binding for TKA, masks for the PVC algorithms, masks to define the regions from which the user wishes to extract quantitative values (kBq/ml, BPnd, ki, etc.). Moreover, these masks can be derived from multiple different sources: classification produced by CIVET, classification produced by ANIMAL, stereotaxic atlas, user-defined regions in native PET space (e.g., region of infarcted tissue from ischemic stroke).

 
### Partial-volume correction <a name="pvc"></a>
Partial-volume correction (PVC) is often necessary to account for the loss of resolution in the image due to the point-spread function of the PET scanner and the fact that multiple tissue types may contribute to a single PET voxel. While performing PVC is generally a good idea, this is especially true if the user is interested in regions that are less than approximately 2.5 times the full-width at half-maximum (FWHM) resolution of the scanner. 
Tracer kinetic analysis
Tracer kinetic analysis (TKA) allows for the quantification of physiological or biological parameters from the radiotracer concentrations measured in the PET image. The appropriate TKA method will depend on the radiotracer. Certain models, e.g., the Logan plot and simplified reference tissue model, are only suitable for radiotracers that are reversibly bound to the tissue. Currently only three TKA methods are implemented: Logan plot, Patlak-Gjedde plot, and the simplified reference tissue model.

### Reporting of results <a name="results"></a>
The ROI masks described in section 1.b are applied on all images output from the pipeline to extract descriptive statistics for each of these regions in each of the output images. The descriptive statistics for each region and image pair are written to .csv files. The .csv file format was selected because it is easy to import into statistical packages (particularly R and python) for further statistical analysis. 

### Quality control <a name="qc"></a>
Quality control is a crucial step of any automated pipeline. It is essential that the user be able to easily confirm that the pipeline has performed as expected and identify any problematic subjects or processing steps. 
Towards the end of facilitating rigorous quality control, we are implementing qualitative and quantitative quality control for every major processing step. The user will be able to peruse all output images in GIF format to verify that the images appear as expected (e.g., that there is no gross error in co-registration). Users will also be able to open the full 3D volumes using the BrainBrowser interface. 
Quantitative quality control functions by calculating a metric that attempts to measure how accurately the processing step in question was performed. For example, the accuracy of the co-registration is measured using a similarity metric between the PET and MRI image. A single metric is not by itself very informative, because we do not know what value this metric should be. However it is possible to compare the metrics of all subjects at a given processing step and find outliers within these. Thus if most of the subjects have a similarity metric of 0.6 for their co-registered PET and MRI, then a subject with a similarity metric of 0.1 would indicate that this subject had probably failed this processing step and should be further scrutinized using qualitative quality control (visual inspection).  

## File Formats  <a name="fileformat"></a>
APPIAN uses the BIDS file format specification for PET:

sub-<participant_label>/
      [_ses-<session_label>/]
pet/sub-<participant_label>[_ses-<session_label>]_task-<task_label>[_acq-<label>][_rec-<label>][_run-<index>]_pet.nii[.gz]

Specifically, the PET inputs in APPIAN use the ‘_ses-<session_label>’ subdirectory and the following attributes: ‘_ses-<session_label>’, ‘_task-<task_label>’, ‘_acq-<label>’, ‘_rec-<label>’.

Example:

APPIAN also requires derivative images, that is, images that have have been derived from raw, specifically raw T1 images. There is a current BIDS proposal for standardized derivative file names. These are implemented in APPIAN and will be updated as the BIDS standard evolves.
#### T1w :
'sub-%s/_ses-%s/anat/sub-%s_ses-%s*T1w.mnc'
#### T1w_nuc: 
'sub-%s/_ses-%s/anat/sub-%s_ses-%s*T1w_nuc.mnc'
#### T1 (MNI space): 
'sub-%s/_ses-%s/final/sub-%s_ses-%s*_T1w_space-mni.mnc
#### Brain mask (no skull): 
'sub-%s/_ses-%s/transforms/sub-%s_ses-%s*target-MNI_affine.xfm
#### Brain mask (skull): 
sub-%s/_ses-%s/transforms/sub-%s_ses-%s*target-MNI_warp.xfm
#### Linear Transform: 
sub-%s/_ses-%s/mask/sub-%s_ses-%s*_space-mni_brainmask.mnc
#### Non-linear Transform: 
'sub-%s/_ses-%s/mask/sub-%s_ses-%s*_space-mni_skullmask.mnc
#### GM-WM classify mask: 
’sub-%s/_ses-%s/mask/sub-%s_ses-%s*space-mni_variant-cls_dtissue.mnc'
#### T1 Segmentation: 
sub-<participant-label>/_ses-<session-label>/mask/sub-<participant-label>_ses-<session-label>_space-mni_variant-seg_dtissue.mnc'

        nativeT1=,
        nativeT1nuc=,
        T1Tal=',
        xfmT1Tal=',
        xfmT1Talnl='',
        brainmaskTal='',
        headmaskTal=',
        clsmask=',
        segmentation=,
        pet='sub-%s/_ses-%s/pet/sub-%s_ses-%s_task-%s_acq-%s_rec-%s_pet.mnc'

Although BIDS is based on the Nifti file format, APPIAN will accept both MINC and Nifti inputs. All Nifti files are converted to MINC for further processing. 

## Usage <a name="useage"></a>

### Launching APPIAN
APPIAN is a Python program (Python 2.7 to be specific) that is launched using a command of the form:

python2.7 <path to APPIAN directory>/Launcher.py <list of options> <subject names>

When running APPIAN through a Docker container (described in detail in the following section), the APPIAN directory is located in “/opt/tka_nipype”:

python2.7 /opt/tka_nipype/Launcher.py <list of options> <subject names>
Running APPIAN with Docker
APPIAN is run through a Docker container. To launch a container based on an image is to run:

Docker run -it <name of image>:<image tag>

or in our case:

docker run -it tffunck/tka:latest

Here the “-it” flag means that the container is launched in interactive mode. That is, you will be dropped into a bash shell within the filesystem and will be able to do most of the typical bash/unix stuff you normally do. You can also run the container non-interactively by dropping the “-it” flag and adding a bash command at the end of the line, as follows:

docker run <name of image>:<image tag> <your bash command>

or in our case:

docker run tffunck/tka:latest ls /opt
bin
doc
etc
...

APPIAN is intended to be flexible and applicable in a wide variety of situations, however this also means that it has many options that have to be specified by the user. Typing out these options in the command line would quickly become tedious, so it’s more convenient to put the command you will use to launch the pipeline, along with all of the desired options, into a bash script (basically just a text file that you can run from the command line). For the example below, “run.sh” is just such a bash script (note that you can name your script whatever you like). Therefore, in the current example, the command would look something like 

python2.7 /opt/tka_nipype/Launcher.py -s /path/to/pet/images -t /path/to/output/dir -p <study prefix> -c </path/to/civet/output> <subject names>


By default, you cannot access any of the data on your computer from the filesystem of the Docker container. To access your data from the Docker container it is necessary to mount the directory on your computer in the Docker container. This sounds complicated, but it’s actually very simple. All you have to do is pass the “-v” flag (“v” for volume) to the Docker “run” command, followed by the absolute path to the directory you want to mount, a colon (“:”),  and the absolute path to the location where you want to mount it. Let’s say you data is stored in “/path/to/your/data” and, for simplicity, you want to mount it to a path called “/path/to/your/data” in the Docker container. To run your Docker container with this path mounted, you would just have to run:

docker run -it -v /path/to/your/data:/path/to/your/data  tffunck/tka:latest

As mentioned above,  there are two ways in which to run APPIAN, either interactively or by passing a command to the “docker run” command. Assuming that you put your “run.sh” script into the same directory as your date, “/path/to/your/data”, then you would run something like the following commands:

docker run -it -v /path/to/your/data:/path/to/your/data tffunck/tka:latest
\#You are now in the docker container
cd /path/to/your/data 
./run.sh

Alternatively, you can also run the pipeline through a non-interatctive docker container, as so:

docker run /path/to/your/data:/path/to/your/data tffunck/tka:latest /path/to/your/data/run.sh

Either method will give you the same results, it’s up to you what you find more convenient. 

## Example use cases  <a name="example"></a>

### FDG
FDG is a non-reversibly bound tracer, meaning that once it binds to its target receptor (i.e., gets transported inside the cell body) it will not become unbound for the duration of the scan. The Patlak-Gjedde plot (--tka-method "pp") is the standard TKA method for analyzing such images. The Patlak-Gjedde plot can be used to calculate the glucose metabolism rate using two variables: the lumped constant (flag: --LC) and concentration of native substrate in arterial plasma (flag: --Ca). The Turku Pet Centre has a useful description here with standard values for LC. The start time (minutes) is set to when the amount of radiotracer in the blood reaches equilibrium with that in the tissue.
   
Example:
--tka-method "pp" --Ca 5.0 --LC 0.8 --start-time 1

Defining your ROI with an atlas
To use a stereotaxic atlas to define your ROI (flag: --roi-atlas), you need to define the anatomic template on which this atlas is defined (flag: --roi-template) and the volume containing the atlas labels (flag: --roi-mask). APPIAN includes two standard templates for defining stereotaxic atlases: Colin27 and ICBM152. 

Example: Using the AAL atlas, defined on the Colin27 template

--roi-atlas  --roi-template  /opt/tka_nipype/Atlas/COLIN27/colin27_t1_tal_lin.mnc  --roi-mask /opt/tka_nipype/Atlas/COLIN27/ROI_MNI_AAL_V4.mnc
References



## User Options  <a name="options"></a>
APPIAN has lots of options, mostly concerned with the types of masks you want to use, and the parameters to pass to the PVC and TKA algorithms. Here is a list of the available options, a more detailed explanation will be written up soon. Important to note is that the only mandatory options are a source directory with PET images (-s), a target directory where the outputs will be stored (-t), the prefix label of your study (-p), and the directory containing the CIVET outputs for each subject (-c). 

Options:
  --version             show program's version number and exit
  -h, --help            show this help message and exit

  File options (mandatory):
    -s SOURCEDIR, --petdir=SOURCEDIR
                        Native PET directory
    -t TARGETDIR, --targetdir=TARGETDIR
                        Directory where output data will be saved in
    -p PREFIX, --prefix=PREFIX
                        Study name
    -c CIVETDIR, --civetdir=CIVETDIR
                        Civet directory
    --condition=CONDILIST
                        comma-separated list of conditions or scans

  Registration options:
    --modelDir=MODELDIR
                        Models directory

  Masking options:
    Reference region

    --ref-user          User defined ROI for each subject
    --ref-animal        Use ANIMAL segmentation
    --ref-civet         Use PVE tissue classification from CIVET
    --ref-icbm152-atlas
                        Use an atlas defined on ICBM152 template
    --ref-atlas         Use atlas based on template, both provided by user
    --ref-labels=REFATLASLABELS
                        Label value(s) for segmentation.
    --ref-template=REFTEMPLATE
                        Template to segment the reference region.
    --ref-suffix=REFSUFFIX
                        ROI suffix
    --ref-gm            Gray matter of reference region (if -ref-animal is
                        used)
    --ref-wm            White matter of reference region (if -ref-animal is
                        used)
    --ref-close         Close - erosion(dialtion(X))
    --ref-erosion       Erode the ROI mask
    --ref-dir=REF_DIR   ID of the subject REF masks
    --ref-template-suffix=TEMPLATEREFSUFFIX
                        Suffix for the Ref template.
    --ref-mask=REFMASK  Ref mask on the template

  Masking options:
    Region Of Interest

    --roi-user          User defined ROI for each subject
    --roi-animal        Use ANIMAL segmentation
    --roi-civet         Use PVE tissue classification from CIVET
    --roi-icbm152       Use an atlas defined on ICBM152 template
    --roi-atlas         Use atlas based on template, both provided by user
    --roi-labels=ROIATLASLABELS
                        Label value(s) for segmentation.
    --roi-template=ROITEMPLATE
                        Template to segment the ROI.
    --roi-mask=ROIMASK  ROI mask on the template
    --roi-template-suffix=TEMPLATEROISUFFIX
                        Suffix for the ROI template.
    --roi-suffix=ROISUFFIX
                        ROI suffix
    --roi-erosion       Erode the ROI mask
    --roi-dir=ROI_DIR   ID of the subject ROI masks

  Masking options:
    ROI for PVC

    --no-pvc            Don't run PVC.
    --pvc-roi-user      User defined ROI for each subject
    --pvc-roi-animal    Use ANIMAL segmentation
    --pvc-roi-civet     Use PVE tissue classification from CIVET
    --pvc-roi-icbm152   Use an atlas defined on ICBM152 template
    --pvc-roi-atlas     Use atlas based on template, both provided by user
    --pvc-roi-labels=PVCATLASLABELS
                        Label value(s) for segmentation.
    --pvc-roi-template=PVCTEMPLATE
                        Template to segment the ROI.
    --pvc-roi-mask=PVCMASK
                        ROI mask on the template
    --pvc-roi-template-suffix=TEMPLATEPVCSUFFIX
                        Suffix for the ROI template.
    --pvc-roi-suffix=PVCSUFFIX
                        PVC suffix
    --pvc-roi-dir=PVC_ROI_DIR
                        ID of the subject ROI masks
    --pvc-method=PVC_METHOD
                        Method for PVC.
    --pet-scanner=PET_SCANNER
                        FWHM of PET scanner.
    --pvc-fwhm=SCANNER_FWHM
                        FWHM of PET scanner.
    --pvc-max-iterations=MAX_ITERATIONS
                        Maximum iterations for PVC method.
    --pvc-tolerance=TOLERANCE
                        Tolerance for PVC algorithm.
    --pvc-lambda=LAMBDA_VAR
                        Lambda for PVC algorithm (smoothing parameter for
                        anisotropic diffusion)
    --pvc-denoise-fwhm=DENOISE_FWHM
                        FWHM of smoothing filter.
    --pvc-nvoxel-to-average=NVOXEL_TO_AVERAGE
                        Number of voxels to average over.

  Tracer Kinetic analysis options:
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
    --arterial=ARTERIAL_DIR
                        Use arterial input input.
    --start-time=TKA_START_TIME
                        Start time for regression in MTGA.
    --tka-type=TKA_TYPE
                        Type of tka analysis: voxel or roi.

  Tracer Kinetic analysis options:
    --group-qc          Perform quantitative group-wise quality control.
    --test-group-qc     Perform simulations to test quantitative group-wise
                        quality control.

  Command control:
    -v, --verbose       Write messages indicating progress.

  Pipeline control:
    --run               Run the pipeline.
    --fake              do a dry run, (echo cmds only).
    --print-scan        Print the pipeline parameters for the scan.
    --print-stages      Print the pipeline stages.

## References
Collins, et al. 1994.  J. Comput. Assist. Tomogr. 18 (2), 192–205. 


