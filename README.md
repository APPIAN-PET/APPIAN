# APPIAN
Table of Contents
=================
[Introduction](#introduction)
[Installation](#installation)
[Documentation](#documentation)
[Publications](#publications)
[Getting Help](#getting-help)
[About us](#about-us)
[Terms and Conditions](#terms-and-conditions)

## Introduction

``APPIAN`` (Automated Pipeline for PET Image ANalysis) is an open-source automated software pipeline for analyzing PET images in conjunction with MRI. The goal of ``APPIAN`` is to facilitate reproducible research and to make PET tracer kinetic data analysis easier for users with moderate computing skills. 

The pipeline starts from the reconstructed PET images and performs all analysis steps necessary to produce outputs that can be used to run statistical tests of interest.  The input to ``APPIAN`` relies on object (.obj) files that contain surface meshes representing cortical grey matter -- for instance, surfaces could be extracted using [``CIVET``][link_civet], which can be freely accessed through the [``CBRAIN``][link_cbrain] online platform (sign-up to ``CBRAIN`` is required, but free).

## Installation 

``APPIAN`` is currently only available through [Docker][link_dockerhome]. Docker is a platform for creating containers that package a given software in a complete filesystem that contains everything it needs to run, and ensures that the software can always be run in the same environment. This means that all of the dependencies required by ``APPIAN`` are within its Docker container (no need to fumble about trying to compile obscure libraries). However, it also means that you will need to install Docker before proceeding. Don’t worry it’s very easy (except maybe for Windows). For a guide on how to install Docker on Ubuntu, Debian, Mac, Windows, or other operating system, please [visit this link][link_dockerinstall].  

The pipeline is implemented in Python using the [Nipype][link_nipypertd] library. Although the core is coded in Python, the pipeline can use tools or incorporate modules written in any programming language. The only condition is that these tools must be run from a command line, with well-defined inputs and outputs. In this sense, ``APPIAN`` is  language agnostic.
Once Docker is installed, simply run the following command line on your terminal:

```
docker pull tffunck/appian:latest
```

That’s it, ``APPIAN`` is installed on your computer. 

## Documentation

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

If you get stuck or don't know how to get started please post on our Google groups. We would be delighted to help in whatever way we can.

https://groups.google.com/forum/#!forum/appian-pet

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

