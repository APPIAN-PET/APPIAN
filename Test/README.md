# Running APPIAN validation

```
./validate_appian.sh <Number of Threads> <Path to APPIAN Dir> <Path to Test Data>  <Output Dir>
```

Name :        appian_validation.sh
Description:  Run validation test suite on current version of APPIAN
Useage :      test.sh <n threads> <path to APPIAN dir> <path to data> <path for outputs> <timestamp>
              n threads :             number of CPU threads to use for testing (default=1, recommended=4)
              path to APPIAN dir :    Abs. path to location of APPIAN repository (default=/APPIAN)
              path to data :          Path to data to be used to testing (default=/APPIAN/Test/cimbi)
              path for outputs :      Path where testing outputs will be saved (default=/APPIAN/Test) 
              timestamp :             Timestamp for validation. Will be set each time scipt is run. 
                                    However, users that are debugging may wish to continue validation with
                                      existing timestamp to prevent rerunning all test. In this case, 
                                     users can provide timestamp from exisint validation. 
Examples :"
         1) Run validation defaults
             ./validate_appian.sh
          2) Run validation with 8 threads in non-default directories. Timestamp genereated at runtime
              ./validate_appian.sh 8 /home/APPIAN /data1/projects/cimbi /data1/projects/  
          3) Run with 1 thread in default directories with pre-existing timestamp
              ./validate_appian.sh 1 /APPIAN /APPIAN/Test/cimbi /APPIAN/Test 20181221-220648


# Running dockerized APPIAN validation
Dockerized version of script will automatically mount the path to the directory where "dockerized_validation_script.sh" to /APPIAN in the docker container. Your test data and output directory must be accessible from this mounted directory. 

1. Clone APPIAN repo onto your system (or just download dockerized_validation_script.sh)
2. Run command :

```
./docker_validate_appian.sh <Number of Threads> <Path to APPIAN Dir> <Path to Test Data>  <Output Dir>
``` 

## Example 
Run dockerized validation script with 4 threads using APPIAN in docker container 
./docker_validate_appian.sh 4 /opt/APPIAN /APPIAN/Test/test_data  /APPIAN/Test/
