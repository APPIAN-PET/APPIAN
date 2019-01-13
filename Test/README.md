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

