# Simple build script to create Singularity images

clobber=${1:-0}

if [[ ! -f base.simg || $clobber == 1 ]]; then
    rm -r base.simg
    sudo singularity build base.simg base/Singularity.base
fi
exit 1

if [[ ! -f ants.simg || $clobber == 1 ]]; then
    rm ants.simg
    sudo singularity build ants.simg ants/ants.Singularity
fi

if [[ ! -f appian.simg || $clobber == 1 ]]; then
    rm appian.simg
    sudo singularity build appian.simg appian/Singularity
fi
