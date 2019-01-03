# APPIAN User Guide

# Table of Contents
1. [Quick Start](#quickstart)
2. [File Formats](#fileformat) \
	2.1 [Nifti](#nifti) \
	2.2 [MINC](#minc) \
3. [Useage](#useage) \
4. [Examples](#example) \
5. [Overview](#overview) \
	5.1 [Base Options](#options) \
	5.2 [MRI Preprocessing](https://github.com/APPIAN-PET/APPIAN/blob/master/MRI/README.md) \
	5.3 [Coregistration](https://github.com/APPIAN-PET/APPIAN/blob/master/Registration/README.md) \
	5.4 [Masking](https://github.com/APPIAN-PET/APPIAN/blob/master/Masking/README.md) \
	5.5 [Partial-Volume Correction](https://github.com/APPIAN-PET/APPIAN/blob/master/Partial_Volume_Correction/README.md) \
	5.6 [Quantification](https://github.com/APPIAN-PET/APPIAN/blob/master/Tracer_Kinetic/README.md) \
	5.7 [Reporting of Results](https://github.com/APPIAN-PET/APPIAN/blob/master/Results_Report/README.md) \
	5.8 [Quality Control](https://github.com/APPIAN-PET/APPIAN/blob/master/Quality_Control/README.md) \
6. [Atlases](https://github.com/APPIAN-PET/APPIAN/blob/master/Atlas/README.md) \




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
      			"Isotope": ["C-11"],
			#APPIAN has a library of standard Isotopes that it can use to determine radionuclide halflife
			#Otherwise you can specify it using "Info":"Halflife" (units=seconds)
			"Halflife" : 100
      		},
		#Optional : Specify bodyweight (kg) for SUV
		"BodyWeight": 75.0
     	},
    	"Time" : {
        	"FrameTimes": {
            		"Units": ["m", "m"],
            		"Values":[[14,64]]
      		}
    	},
	#Optional : Specify injected radioactivity dose for SUV
	"RadioChem":{
		"InjectedRadioactivity": 8,
		"InjectedRadioactivityUnits": "kBq"
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

### Base User Options  <a name="options"></a>
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

### [MRI Preprocessing](https://github.com/APPIAN-PET/APPIAN/blob/master/MRI/README.md)

### [Coregistration](https://github.com/APPIAN-PET/APPIAN/blob/master/Registration/README.md) 
### [Masking](https://github.com/APPIAN-PET/APPIAN/blob/master/Masking/README.md) \
### [Partial-Volume Correction](https://github.com/APPIAN-PET/APPIAN/blob/master/Partial_Volume_Correction/README.md) \
### [Quantification](https://github.com/APPIAN-PET/APPIAN/blob/master/Tracer_Kinetic/README.md) \
### [Reporting of Results](https://github.com/APPIAN-PET/APPIAN/blob/master/Results_Report/README.md) \
### [Quality Control](https://github.com/APPIAN-PET/APPIAN/blob/master/Quality_Control/README.md) 

## [Atlases](https://github.com/APPIAN-PET/APPIAN/blob/master/Atlas/README.md)
