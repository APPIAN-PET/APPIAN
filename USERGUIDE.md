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
	docker run -v  </path/to/cimbi/dir>:"/path/to/cimbi/dir" -v </path/to/cimbi/dir/out_cimbi>:"/path/to/cimbi/dir/out_cimbi" tffunck/appian:latest bash -c "python2.7 /opt/APPIAN/Launcher.py -s "/path/to/cimbi/dir" -t "/path/to/cimbi/dir/out_cimbi" ";

#### PVC
	docker run -v </path/to/cimbi/dir>:"/path/to/cimbi/dir" -v </path/to/cimbi/dir/out_cimbi>:"/path/to/cimbi/dir/out_cimbi" tffunck/appian:latest bash -c "python2.7 /opt/APPIAN/Launcher.py --fwhm 3 3 3 --pvc-method 'GTM' --no-results-report -s /path/to/cimbi/dir -t "/path/to/cimbi/dir/out_cimbi" --sessions 01  01";

#### PVC + Quantification
	docker run -v </path/to/cimbi/dir>:"/path/to/cimbi/dir" -v </path/to/cimbi/dir/out_cimbi>:"/path/to/cimbi/dir/out_cimbi" tffunck/appian:latest bash -c "python2.7 /opt/APPIAN/Launcher.py --tka-method lp --tka-label 3 --results-label-erosion 5 --fwhm 3 3 3 --pvc-method 'GTM' --no-results-report -s "/path/to/cimbi/dir" -t "/path/to/cimbi/dir/out_cimbi"  ";

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

#### Optional
##### Linear Transform from T1 native to stereotaxic: 
`sub-%s/_ses-%s/transforms/sub-%s_ses-%s*target-MNI_affine.xfm`

##### Brain mask (stereotaxic space): 
`sub-%s/_ses-%s/anat/sub-%s_ses-%s*_T1w_space-mni_brainmask.mnc`

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
## 3. Usage <a name="useage"></a>

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

## 4. Pipeline Overview  <a name="overview"></a>

### 4.1 Base User Options  <a name="options"></a>
APPIAN has lots of options, mostly concerned with the types of masks you want to use, and the parameters to pass to the PVC and quantification algorithms. The only mandatory options are a source directory with PET images (`-s`), a target directory where the outputs will be stored (`-t`). 

#####  Mandatory arguments:
    -s SOURCEDIR, --source=SOURCEDIR, --sourcedir=SOURCEDIR
                        Input file directory
    -t TARGETDIR, --target=TARGETDIR, --targetdir=TARGETDIR
                        Directory where output data will be saved in
#### Data Formats
By default, APPIAN accepts either Nifti or MINC input files. If Nifti files are used, they will be converted to MINC in the source directory. This means that you must have write permissions to your source directory. In the future, this may be changed so that files converted from Nifti to MINC are saved in the target directory because it may be preferable to only write to the target directory.

The user can set whether files are output in Nifti or MINC with the ```--output-format <file format>``` option. In principal files could be converted to any format for which a converter is available and python savy users are encouraged to try to implement this. 
#####  Optional arguments:
```
    --output-format=OUTPUT_FORMAT 
    			The file format for outputs from APPIAN: minc, nifti (Default=nifti).
```

#### Running on a subset of data
By default, APPIAN will run for all the PET scans located in the source directory. However, a more specific subset of subjects can be specified using the "--subjects", "--sessions", "--tasks", "--runs", "--acq", and "rec" option to specify specific subjects, sessions, tasks, runs, acquisitions (i.e., specific radiotracers), and reconstructions. 


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
    --no-group-level    Run group level analysis
    --no-scan-level     Run scan level analysis


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


### 4.2 [MRI Preprocessing](https://github.com/APPIAN-PET/APPIAN/blob/master/MRI/README.md)
Processing of T1 MRI for spatial normalization to stereotaxic space, intensity non-uniformity correction, brain masking, and segementation.

### 4.3 [Coregistration](https://github.com/APPIAN-PET/APPIAN/blob/master/Registration/README.md) 
Rigid coregistration of PET image to T1 MRI. 

### 4.4 [Masking](https://github.com/APPIAN-PET/APPIAN/blob/master/Masking/README.md) 
Create ROI mask volumes for partial-volume correction, quantification (tracer-kinetic analysis), and reporting of results.

### 4.5 [Partial-Volume Correction](https://github.com/APPIAN-PET/APPIAN/blob/master/Partial_Volume_Correction/README.md) 
Partial-volume correction of point-spread function of PET scanner.

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

For all nodes that are responsible for running a command in the terminal, there will be a text file called "commant.txt" in the node's output directory It is also useful to note that Nipype will always create a "\_report" subdirectory within a particular node's output directory. In this "\_report" directory, you will find a text file called "report.rst". This text file describes the inputs and outputs to this node. This can help you debug APPIAN if for some reason a node fails to run. 

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
python2.7 /opt/APPIAN/Launcher.py -s /path/to/data -t /path/to/output --sessions baseline follow-up
```

The same can be done for : subjects using the "--subjects <subject to process>" flag, tasks with "--tasks <tasks to process>", and run with "--runs <runs to process>".


### Partial-volume correction
To use partial-volume correction (PVC), you must also specify the FWHM of the scanner you are using. The PVC method is specified with the "--pvc-method <PVC Method>" option. APPIAN will use the string you specify for <PVC Method> to find a correspdoning python module in "Partial_Volume_Correction/methods/pvc_method_<PVC Method>.py". 
	
Moreover, you may wish to use a specific labeled image to contstrain the PVC algorithm. There are multiple types of labeled images that you can select with the "--pvc-label-img" option (see the [masking](#masking) section for more information). If no such label is specified by the user, then APPIAN will by default use a GM/WM/CSF segmentation of the input T1 MRI.
	
```
python2.7 /opt/APPIAN/Launcher.py -s <SOURCE DIR> -t <TARGET DIR> --threads <N Threads> --pvc-label-img <label image> <label template> --pvc-label <list of labels> --fwhm <Z FWHM> <Y FWHM> <X FWHM> --pvc-method <PVC Method> 
```
For instance, let's say your images were acquired using the HR+ scanner (which has a FWHM of about 6.5 6.5 6.5) and you want to use the Geometric Transfer Matrix method (GTM). Let's say you want to use a predefined labeled image in the /anat directory of your source directory of the form sub-<subject>/ses-<session>/anat/sub-<subject>_ses-<session>_variant-segmentation_dseg.mnc. You would use : 

```
python2.7 /opt/APPIAN/Launcher.py -s /path/to/data -t /path/to/output --threads 2 --pvc-label-img variant-segmentation --fwhm 6.5 6.5 6.5 --pvc-method GTM
```

### Quantification
To use a quantification method (e.g., tracer-kinetic analysis), you use the option --quant-method <Quantification Method>. You can also use the "--tka-method" flag, but this flag is gradually being depreated in favor of "--quant-method".

Quantification methods may require additional options, such as "--start-time <start time>" for graphical tracer-kinetic analysis methods. 
	
You may also need to either define a reference region or use arterial sampling. To use arterial sampling, you must set the flag "--arterial" and have a arterial inputs files in the [dft](http://www.turkupetcentre.net/formats/format_dft_1_0_0.pdf) file format. 
On the other hand, you can use a labeled image to define a reference region. There are multiple types of labeled images that you can select with the "--tka-label-img" option (see the [masking](#masking) section for more information). If no such label is specified by the user, then APPIAN will by default use the WM mask from a GM/WM/CSF segmentation of the input T1 MRI. Additionally, the "--quant-labels-ones-only" is useful because it will set all of the labels you set with "--quant-label <list of labels>" to 1. 
	
```
python2.7 /opt/APPIAN/Launcher.py -s <SOURCE DIR> -t <TARGET DIR> --threads <N Threads> --quant-label-img <label image> <label template> --quant-label <list of labels> --start-time <Start time in Min.> --quant-labels-ones-only --quant-method <Quantification Method> 
```
	
For example, say you have FDG images and wish to use the Patlak-Gjedde plot method for tracer-kinetic analysis. In order to calculate glucose metabolism, you need to specify the lump constant (LC) and concentration of native substantce (Ca). Let's also imagine that you have a you use an atlas in MNI152 space that you want to use to specify a reference region in the cerebellum and where the two hemispheres of the cerebellum have labels 67 and 76, respectively. 

```
python2.7 /opt/APPIAN/Launcher.py -s <SOURCE DIR> -t <TARGET DIR> --threads 6 --quant-label-img /opt/APPIAN/Atlas/MNI152/dka.mnc --quant-label 67,76 --quant-labels-ones-only --start-time 5 --Ca 5.0 --LC 0.8  --quant-method pp 
```

To do the same analysis but with an arterial input file for each subject (instead of a reference region):

```
python2.7 /opt/APPIAN/Launcher.py -s <SOURCE DIR> -t <TARGET DIR> --threads 6 --arterial --start-time 5 --Ca 5.0 --LC 0.8  --quant-method pp 
```

### Results report
APPIAN produces a .csv file with mean regional values for the results labels. If you will not use the results report produced by APPIAN, you can use the "--no-results-report".

As with PVC and quantification, the results labels are defined using the option "--results-label-img". By default, APPIAN will use all of the integer values in the label image.

For example, if you want to use a segmentation defined on your own template of Alzheimer's patients defined in T1 native space, you would use :
```
python2.7 /opt/APPIAN/Launcher.py -s <SOURCE DIR> -t <TARGET DIR> --results-label-img /path/to/segmentation.mnc --results-label-space t1
```
Similarly, if you want to create the results report with an atlas that is not in MNI space, but only for a single label value (i.e., 4), you would use :
```
python2.7 /opt/APPIAN/Launcher.py -s <SOURCE DIR> -t <TARGET DIR> --results-label-img /path/to/atlas.mnc /path/to/template.mnc --results-label 4
```
