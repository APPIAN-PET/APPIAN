# APPIAN

##Introduction
APPIAN is an open-source automated software pipeline for analyzing PET images in conjunction with MRI. The goal of APPIAN is to make PET tracer kinetic data analysis easy for users with moderate computing skills and to facilitate reproducible research. The pipeline begins with the reconstructed PET image and performs all analysis steps necessary for the user to be able to take the outputs and run her statistical tests of interest.  The input to APPIAN depends on the CIVET processing pipeline. CIVET is designed to extract surface meshes representing the cortical grey matter. It can be freely used through the CBRAIN online platform (sign-up is required, but free).
The pipeline is implemented in Python using the Nipype library. Although the core of the code is written in Python, the pipeline can use tools or incorporate modules written in any programming language. The only condition is that the tools must be capable of being run from a command line with well-defined inputs and outputs. In this sense, APPIAN is  language agnostic.

##Installation 

APPIAN is currently only available through Docker. Docker is a platform for creating containers that package a given software in a complete filesystem that contains everything it needs to run and ensures that the software can always be run in the same environment. This means that all of the dependencies needed by APPIAN are within its Docker container (no need to fumble about trying to compile obscure libraries). However, it also means that you will need to install Docker before proceeding. Don’t worry it’s very easy (except maybe for Windows). For a guide to installing Docker on Ubuntu, Debian, Mac, Windows, other.  

Once docker is installed, simply run the following command on your command line terminal:

docker pull tffunck/appian:latest

That’s it, APPIAN is installed on your computer. 


##User Documentation
https://docs.google.com/document/d/1GjPd-EoICuGWy3BVwJkHsud_znFQFVsopS9Y-6GnrcU/edit?usp=sharing

##Developper / Contributer Documentation
