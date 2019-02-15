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

``APPIAN`` is currently only available through [Docker][link_dockerhome]. Docker is a platform for creating containers that package a given software in a complete filesystem that contains everything it needs to run, and ensures that the software can always be run in the same environment. This means that all of the dependencies required by ``APPIAN`` are within its Docker container (no need to fumble about trying to compile obscure libraries). However, it also means that you will need to install Docker before proceeding. Don’t worry it’s very easy (except maybe for Windows). For a guide on how to install Docker on Ubuntu, Debian, Mac, Windows, or other operating system, please [visit this link][link_dockerinstall].  

The pipeline is implemented in Python using the [Nipype][link_nipypertd] library. Although the core is coded in Python, the pipeline can use tools or incorporate modules written in any programming language. The only condition is that these tools must be run from a command line, with well-defined inputs and outputs. In this sense, ``APPIAN`` is  language agnostic.
Once Docker is installed, simply run the following command line on your terminal:

```
docker pull tffunck/appian:latest
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

