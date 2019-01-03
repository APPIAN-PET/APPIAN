# Reporting of results <a name="results"></a>
The ROI masks described in *section 5.4* are applied on all images output from the pipeline to extract descriptive statistics for each of these regions in each of the output images. The descriptive statistics for each region and image pair are written to .csv files. The .csv file format was selected because it is easy to import into statistical packages (particularly R and Python) for further statistical analysis. 

####  Results reporting options:
    --no-group-stats    Don't calculate quantitative group-wise descriptive
                        statistics.
