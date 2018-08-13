# APPIAN

## Introduction

``APPIAN`` (Automated Pipeline for PET Image ANalysis) is an open-source automated software pipeline for analyzing PET images in conjunction with MRI. The goal of ``APPIAN`` is to facilitate reproducible research and to make PET tracer kinetic data analysis easier for users with moderate computing skills. 

The pipeline starts from the reconstructed PET images and performs all analysis steps necessary to produce outputs that can be used to run statistical tests of interest.  The input to ``APPIAN`` relies on object (.obj) files that contain surface meshes representing cortical grey matter -- for instance, surfaces could be extracted using [``CIVET``][link_civet], which can be freely accessed through the [``CBRAIN``][link_cbrain] online platform (sign-up to ``CBRAIN`` is required, but free).

The pipeline is implemented in Python using the [Nipype][link_nipypertd] library. Although the core is coded in Python, the pipeline can use tools or incorporate modules written in any programming language. The only condition is that these tools must be run from a command line, with well-defined inputs and outputs. In this sense, ``APPIAN`` is  language agnostic.

## Installation 

``APPIAN`` is currently only available through [Docker][link_dockerhome]. Docker is a platform for creating containers that package a given software in a complete filesystem that contains everything it needs to run, and ensures that the software can always be run in the same environment. This means that all of the dependencies required by ``APPIAN`` are within its Docker container (no need to fumble about trying to compile obscure libraries). However, it also means that you will need to install Docker before proceeding. Don’t worry it’s very easy (except maybe for Windows). For a guide to installing Docker on Ubuntu, Debian, Mac, Windows, or other, [visit this link][link_dockerinstall].  

Once Docker is installed, simply run the following command line on your terminal:

docker pull tffunck/appian:latest

That’s it, ``APPIAN`` is installed on your computer. 

## Documentation

### Users
For more information please read our [user guide][link_userguide]. 

### Developers
For those interested in extending or contributing to APPIAN please check out our [contributors guidelines][link_contributors].

## Publications


[link_dockerinstall]: https://docs.docker.com/install/
[link_civet]: https://mcin-cnim.ca/technology/civet/
[link_cbrain]: https://github.com/aces/cbrain/wiki
[link_nipypertd]: https://nipype.readthedocs.io/en/latest/
[link_dockerhome]: https://docs.docker.com/
[link_userguide]: https://github.com/APPIAN-PET/APPIAN/blob/master/USERGUIDE.md
[link_contributors]: https://github.com/APPIAN-PET/APPIAN/blob/master/CONTRIBUTING.md
