FROM ubuntu:22.04

RUN mkdir /opt/bin /opt/lib /opt/include /opt/share
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update -y

RUN apt-get install -y software-properties-common && \
    add-apt-repository -y ppa:deadsnakes/ppa

# Install Python 3.11 and set it as the default version
RUN apt-get install -y g++ build-essential liblapack* git wget curl openssl cmake cmake-curses-gui vim \
    zlib1g-dev libssl-dev unzip python3.11 python3.11-dev python3.11-distutils && \
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1

# Install pip for Python 3.11
RUN curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py && \
    python3.11 get-pip.py && \
    update-alternatives --install /usr/bin/pip3 pip3 /usr/local/bin/pip3 1

# Add /opt/lib to library path
RUN echo "/opt/lib/" >> /etc/ld.so.conf.d/userLibraries.conf
RUN ldconfig

# Install Python packages
RUN pip3 install setuptools networkx nilearn nipype keras nibabel pydot h5py numpy scipy configparser pandas matplotlib nibabel scikit-learn seaborn wget SimpleITK scikit-image pint webcolors && \
    pip3 install --upgrade numpy

# Clean up after installing packages
RUN apt-get clean && \
    rm -rf /var/lib/apt/lists/*
    
# Vim configuration
RUN echo "syntax on" > /root/.vimrc && \
    echo "set tabstop=4 shiftwidth=4 expandtab smartindent hlsearch " >> /root/.vimrc && \
    echo set undofile undodir=~/.vim/undodir >> /root/.vimrc

# Install ANTsPy
RUN pip3 install webcolors && \
    pip3 install antspyx

# Install AWS CLI
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" && \
    unzip awscliv2.zip && \
    ./aws/install

# ANTs Scripts
RUN cd /opt/ && \
    git clone https://github.com/stnava/ANTs.git && \
    cp `find ANTs/ -name "*sh"` /opt/bin/ && \
    rm -rf /opt/ANTs

# PETPVC
RUN wget https://github.com/UCL/PETPVC/releases/download/v1.2.4/PETPVC-1.2.4-Linux.tar.gz && \
    tar -zxvf PETPVC-1.2.4-Linux.tar.gz && \
    cp -r PETPVC-1.2.4/* /opt/ && \
    rm -r PETPVC*

# Dynamic PET
RUN git clone https://github.com/bilgelm/dynamicpet.git && \
    pip3 install -e dynamicpet

# APPIAN
RUN cd /opt && \
    git clone -b dynamic-pet-integration https://github.com/cepa995/APPIAN.git

RUN echo "python3 /opt/APPIAN/Launcher.py" > /opt/bin/appian

RUN useradd -ms /bin/bash user

RUN chown -R user:user /opt/bin/ && chmod 733 /opt/bin/*

USER user
# ENVIRONMENT VARIABLES
ENV PATH /opt/bin:$PATH
ENV ANTSPATH /opt/bin

# OSError: Matplotlib requires access to a writable cache directory
# Create a writable directory for Matplotlib
RUN mkdir -p /tmp/.matplotlib && \
    chown -R user:user /tmp/.matplotlib

# Set the MPLCONFIGDIR environment variable
ENV MPLCONFIGDIR=/tmp/.matplotlib