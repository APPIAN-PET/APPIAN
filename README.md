# APPIAN
Table of Contents
=================
[Introduction](#introduction)

[Installation](#installation)

[Documentation](#documentation)

[Publications](#publications)

[About us](#about-us)

[Terms and Conditions](#terms-and-conditions)


## Introduction
APPIAN (Automated Pipeline for PET Image ANalysis) is an open-source automated software pipeline for analyzing PET images in conjunction with MRI. The goal of APPIAN is to make PET tracer kinetic data analysis easy for users with moderate computing skills and to facilitate reproducible research. The pipeline begins with the reconstructed PET image and performs all analysis steps necessary for the user to be able to take the outputs and run her statistical tests of interest.  APPIAN also uses a structural brain image (e.g., T1 MRI), images derived from this structural image (e.g., brainmask), and linear transformation file from MRI native to MNI152 space. CIVET is designed to extract surface meshes representing the cortical grey matter and can be used in conjuction with APPIAN. It can be freely used through the [CBRAIN][cbrain] online platform (sign-up is required, but free).
The APPIAN pipeline is implemented in Python using the [Nipype][nipype] library. Although the core of the code is written in Python, the pipeline can use tools or incorporate modules written in any programming language. The only condition is that the tools must be capable of being run from a command line with well-defined inputs and outputs. In this sense, APPIAN is  language agnostic.

## Installation 

APPIAN is currently only available through Docker. Docker is a platform for creating containers that package a given software in a complete filesystem that contains everything it needs to run and ensures that the software can always be run in the same environment. This means that all of the dependencies needed by APPIAN are within its Docker container (no need to fumble about trying to compile obscure libraries). However, it also means that you will need to install Docker before proceeding. Don’t worry it’s very easy (except maybe for Windows). For a guide to installing Docker on [Ubuntu][ubuntu_docker], [Debian][debian_docker], [Mac][mac_docker], [Windows][windows_docker].


Once docker is installed, simply run the following command on your command line terminal:

docker pull tffunck/appian:latest

That’s it, APPIAN is installed on your computer. 


## Documentation
### Developers
For those interested in extending or contributing to APPIAN please check out our [developper guide][link_contributing]. 

### Users

Users seeking more information can check the [user guide][link_user_guide].

## Publications
1. APPIAN overview paper (coming soon)
2. APPIAN automated QC paper (coming soon)

## About us
Thomas Funck, PhD Candidate (tffunck@gmail.com)\
Kevin Larcher, MSc Eng.\
Paule Joanne Toussaint, PhD

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
