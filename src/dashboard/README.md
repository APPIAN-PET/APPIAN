# Quality control <a name="qc"></a>
Quality control is a crucial step of any automated pipeline. It is essential that the user be able to easily confirm that the pipeline has performed as expected and identify any problematic subjects or processing steps. 
In order to facilitate rigorous quality control, we are implementing qualitative and quantitative quality control for every major processing step. The user will be able to peruse all output images in GIF format to verify that the images appear as expected (e.g., that there is no gross error in co-registration). Users will also be able to open the full 3D volumes using the BrainBrowser web interface. 
Quantitative quality control functions by calculating a metric that attempts to measure how accurately the processing step in question was performed. For example, the accuracy of the co-registration is measured using a similarity metric between the PET and MRI image. A single metric is not by itself very informative, because we do not know what value this metric should be. However it is possible to compare the metrics of all subjects at a given processing step and find outliers within these. Thus if most of the subjects have a similarity metric of 0.6 for their co-registered PET and MRI, then a subject with a similarity metric of 0.1 would indicate that this subject had probably failed this processing step and should be further scrutinized using qualitative quality control (visual inspection).  

####  Quality control options:
    --no-group-qc       Don't perform quantitative group-wise quality control.
    --no-dashboard      Don't create the xml files necessary to create the visual dashboard
    --test-group-qc     Perform simulations to test quantitative group-wise
                        quality control.
