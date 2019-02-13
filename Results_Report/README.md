# Reporting of results <a name="results"></a>
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
