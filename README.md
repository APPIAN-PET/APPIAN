# APPIAN
Table of Contents
=================
 1. [Introduction](#introduction)
 2. [Installation](#installation)
 3. [Documentation](#documentation)\
     3.1 [User Guide](https://github.com/APPIAN-PET/APPIAN/blob/master/USERGUIDE.md)\
     3.2 [Developer Guide](link_contributing)
 4. [Publications](#publications)
 5. [Getting Help](#getting-help)
 6. [About us](#about-us)
 7. [Terms and Conditions](#terms-and-conditions)


## Introduction
The APPIAN pipeline is implemented in Python using the [Nipype][nipype] library. Although the core of the code is written in Python, the pipeline can use tools or incorporate modules written in any programming language. The only condition is that the tools must be capable of being run from a command line with well-defined inputs and outputs. In this sense, APPIAN is  language agnostic.


#### Cost
APPIAN is 100% free and open-source, but in exchange we would greatly appreciate your feedback, whether it be as bug reports, pull requests to add new features, questions on our [mailing list](https://groups.google.com/forum/#!forum/appian-users), or suggestions on how to improve the documentation or the code. You can even just send us an email to let us know what kind of project you are working on!   

## Installation 

``APPIAN`` is currently only available through [Docker][link_dockerhome]. Docker is a platform for creating containers that package a given software in a complete filesystem that contains everything it needs to run, and ensures that the software can always be run in the same environment. This means that all of the dependencies required by ``APPIAN`` are within its Docker container (no need to fumble about trying to compile obscure libraries). However, it also means that you will need to install Singularity or Docker before proceeding. Don’t worry it’s very easy (except maybe for Windows). For a guide on how to install Docker on Ubuntu, Debian, Mac, Windows, or other operating system, please [visit this link][link_dockerinstall] and [Singularity][link_singularityinstall].  

The pipeline is implemented in Python using the [Nipype][link_nipypertd] library. Although the core is coded in Python, the pipeline can use tools or incorporate modules written in any programming language. The only condition is that these tools must be run from a command line, with well-defined inputs and outputs. In this sense, ``APPIAN`` is  language agnostic.
Once Docker or Singularity is installed, simply run the following command line on your terminal:

```
docker pull tffunck/appian:latest-dev

singularity pull APPIAN-PET/APPIAN:latest
```

That’s it, ``APPIAN`` is installed on your computer. 

## Documentation

### Developers
For those interested in extending or contributing to APPIAN please check out our [developer guide][link_contributing]. 

### Users
For more information please read our [user guide][link_userguide]. 

### Developers
For those interested in extending or contributing to APPIAN please check out our [contributors guidelines][link_contributors].

## Publications
1. Funck T, Larcher K, Toussaint PJ, Evans AC, Thiel A (2018) APPIAN: Automated Pipeline for PET Image Analysis. *Front Neuroinform*. PMCID: [PMC6178989][link_pmcid], DOI: [10.3389/fninf.2018.00064][link_doi]

2. APPIAN automated QC (*in preparation*)

[link_dockerinstall]: https://docs.docker.com/install/
[link_civet]: https://mcin-cnim.ca/technology/civet/
[link_cbrain]: https://github.com/aces/cbrain/wiki
[link_nipypertd]: https://nipype.readthedocs.io/en/latest/
[link_dockerhome]: https://docs.docker.com/
[link_userguide]: https://github.com/APPIAN-PET/APPIAN/blob/master/USERGUIDE.md
[link_contributors]: https://github.com/APPIAN-PET/APPIAN/blob/master/CONTRIBUTING.md
[link_pmcid]: https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6178989/
[link_doi]: https://doi.org/10.3389/fninf.2018.00064

## Getting help

If you get stuck or don't know how to get started please send a mail to the APPIAN mailing list :
https://groups.google.com/forum/#!forum/appian-users

For bugs, please post [here](#https://github.com/APPIAN-PET/APPIAN/issues) on the Github repository.

To join the discussion for APPIAN development, join our developers mailing list : 
https://groups.google.com/forum/#!forum/appian-dev



## About us
Thomas Funck, PhD Candidate (thomas.funck@mail.mcgill.ca)\
Kevin Larcher, MSc Eng.\
Paule-Joanne Toussaint, PhD

## Terms and Conditions
Copyright 2017 Thomas Funck, Kevin Larcher


Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


[link_contributing]: https://github.com/APPIAN-PET/APPIAN/blob/master/CONTRIBUTING.md
[link_user_guide]: https://github.com/APPIAN-PET/APPIAN/blob/master/USERGUIDE.md
[ubuntu_docker]: https://docs.docker.com/install/linux/docker-ce/ubuntu/
[debian_docker]: https://docs.docker.com/install/linux/docker-ce/ubuntu/
[mac_docker]: https://docs.docker.com/docker-for-mac/install/
[windows_docker]: https://docs.docker.com/docker-for-windows/install/
[nipype]: http://nipype.readthedocs.io/en/latest/
[cbrain]: https://mcin-cnim.ca/technology/cbrain/

# About
This is a script that essentially runs APPIAN a bunch of different times with varying options. In theory, it should be useable with any data set, although in practice it has only been developed using a small test data set of simulated PET images and T1 images from the 1000 Connectomes Project.

The purpose of this validatation script is to check that changes made to the APPIAN code do not break the package. As such it should be run before pushing any new changes to the Git repository and especially before creating an updated Docker container with a new version APPIAN.

More tests will need to be added in the future as the current set are not exhaustive. 

It is therefore a good idea to reuse the output of previous tests to avoid rerunning processing stages unecessarily. For example, there is no need to rerun PET-MRI co-registration everytime one wants to test a downstream processing stage, like PVC or quantification. The tests are therefore organized such that at least some of the outputs of the previous tests can be reused for subsequent ones. 

## Setup
1. Uncompress Tests/test_data.tar.bz2
2. Uncompress Atlas/MNI152/dka.mnc.tar.bz2


# Running dockerized APPIAN validation
You should generally run the APPIAN validation through the dockerized version of the validate_appian script. This will automatically mount the path to APPIAN/ directory from which you launch "dockerized_validation_script.sh". This will directory be mounted to /APPIAN in the docker container. Your test data and output directory must be accessible from this mounted directory. 

1. Clone APPIAN repo onto your system (or just download dockerized_validation_script.sh)
2. Run command :

```
./docker_validate_appian.sh <Number of Threads> <Path to APPIAN Dir> <Path to Test Data>  <Output Dir> <exit on failure> <qc> <Time stamp>
``` 

## Example 
Run dockerized validation script with 4 threads using APPIAN in docker container.

```./docker_validate_appian.sh 4 /opt/APPIAN /APPIAN/Test/test_data  /APPIAN/Test/```

# Running APPIAN validation

__Name :__        appian_validation.sh

__Description:__  Run validation test suite on current version of APPIAN

__Useage :__      
```
validate_appian.sh <n threads> <path to APPIAN dir> <path to data> <path for outputs> <exit on failure> <qc> <timestamp>
```
__Options:__
  
              n threads :             number of CPU threads to use for testing (default=1, recommended=4)
              
              path to APPIAN dir :    Abs. path to location of APPIAN repository (default=/APPIAN)
              
              path to data :          Path to data to be used to testing (default=/APPIAN/Test/cimbi)
              
              path for outputs :      Path where testing outputs will be saved (default=/APPIAN/Test)
              
              exit on failure:        Exit validation if a test fails. Set to 1 to enable (default=0)
              qc :                    Create .png images of output files. Set to 1 to enable (default=0)
              timestamp :             Timestamp for validation. Will be set each time scipt is run. 
                                      However, users that are debugging may wish to continue validation with
                                      existing timestamp to prevent rerunning all test. In this case, 
                                      users can provide timestamp from exisint validation. 
__Examples :__\
         1) Run validation defaults\
             ```./validate_appian.sh```\
          2) Run validation with 8 threads in non-default directories. Timestamp genereated at runtime\
              ```./validate_appian.sh 8 /home/APPIAN /data1/projects/cimbi /data1/projects/```  \
          3) Run with 1 thread in default directories with pre-existing timestamp\
              ```./validate_appian.sh 1 /APPIAN /APPIAN/Test/cimbi /APPIAN/Test 0 0 20181221-220648```
## Tests
Feel free to add additional tests to the validate_appian.sh script as needed.

1. Minimal APPIAN run (T1 preprocessing, Coregistration, Results Report, Automated QC)
2. PVC with GTM
3. PVC with idSURF
4. Quantification with Logan Plot (Voxelwise)
5. Quantification with Logan Plot (ROI)
6. Quantification with Patlak-Gjedde Plot (Voxelwise)
7. Quantification with Patlak-Gjedde Plot (ROI)
8. Quantification with SUV
9. Quantification with SUVR
10. Quantification with SRTM
11. APPIAN run in stereotaxic space
12. APPIAN run in MRI native space
13. APPIAN run with DKA atlas in MNI 152 space 
14. APPIAN with AAL atlas in Colin27 space

## Example output :

### Stdout :
```
    Launching APPIAN validation tests 
   -------------------------------------
Warning: You should have commited latest changes to current git branch
fatal: Not a git repository (or any of the parent directories): .git
Timestamp: 20190102-002046
Git Commit :

Test: Mininimum -- Errors = 0 --> passed.
Test: PVC-GTM -- Errors = 0 --> passed.
Test: PVC-idSURF -- Errors = 0 --> passed.
Test: Quant-lp -- Errors = 0 --> passed.
Test: Quant-pp -- Errors = 0 --> passed.
Test: Quant-suvr -- Errors = 0 --> passed.
Test: Space-Stereo -- Errors = 0 --> passed.
Test: Space-MRI -- Errors = 0 --> passed.
Test: Atlas-DKA -- Errors = 0 --> passed.
Test: Atlas-AAL -- Errors = 0 --> passed.
```
### Output files :
The output files contain stderr and stdout from APPIAN run. They have the <.passed> suffix if the test was complete successfully and <.failed> otherwise. The info.json file contains some basic information about the validation.
```
appian_validation/test_20190102-002046:
info.json              test_Mininimum.passed   test_Quant-lp.passed    test_Space-MRI.passed
test_Atlas-AAL.passed  test_PVC-GTM.passed     test_Quant-pp.passed    test_Space-Stereo.passed
test_Atlas-DKA.passed  test_PVC-idSURF.passed  test_Quant-suvr.passed
```

