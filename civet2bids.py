import os
from sys import exit, argv
from glob import glob
from shutil import copy
from ntpath import basename

def old_paths(files, attributes):
    l=[]
    for f in files:
        d={}
        file_paths, ext = os.path.splitext(f)
        filename = basename(file_paths)
        f_split = filename.split('_')
        for var  in attributes:
            d[var]=None
            for x in f_split: 
                if var in x :
                    d[var]=x
        d['ext'] = ext
        l.append(d)
    return(l)

def new_paths(files,attributes, out_dir, image_type, folder_name, l):
    for d,f in zip(l,files):
        new_pet = out_dir + os.sep + d['sub'] + os.sep
        if not os.path.exists(new_pet) : os.mkdir(new_pet)
        if d['ses'] != None:
            new_pet = new_pet + d['ses'] +  os.sep
        if not os.path.exists(new_pet) : os.mkdir(new_pet)    
        new_pet +=  folder_name + os.sep
        if not os.path.exists(new_pet) : os.mkdir(new_pet)    
        for var in  attributes:
            if d[var] != None:
                new_pet +=  d[var] + '_'
        
        new_pet = new_pet + image_type + d['ext']
        if not os.path.exists(new_pet):
            copy(f, new_pet)
            print f, new_pet

def copy_paths(file_dir, out_dir, attributes, input_image_type, image_type, folder_name):
    files = glob(file_dir+"*"+ input_image_type + ".*")
    new_paths(files, attributes, out_dir, image_type, folder_name, old_paths(files, attributes))

pet_dir = argv[1] + os.sep
civet_dir = argv[2] + os.sep
out_dir = argv[3] + os.sep 

pet_attributes = ['sub', 'ses', 'task', 'acq', 'rec']
t1_attributes = [ 'sub', 'ses', 'task']
input_image_suffixes = ['pet', 't1', 't1_nuc',  't1_tal', 'brain_mask', 'skull_mask', 't1_tal', 'nlfit_It', 'classify', 'labels_masked'  ]
output_image_suffixes=['pet', 'T1w', 'T1w_nuc', 'T1w_mni', 'brain_mask', 'skull_mask', 'nat2mni-lin', 'nat2mni-nl', 'classify', 'segmentation' ]
input_dirs = [ pet_dir, civet_dir+'*/native/', civet_dir+'*/native/', civet_dir+'*/final/', civet_dir+'*/mask/', civet_dir+'*/mask/', civet_dir+'*/transforms/linear/', civet_dir+'*/transforms/nonlinear/', civet_dir+'*/classify/' , civet_dir+'*/segment/' ]
folder_names = ['pet', 'anat', 'anat', 'final', 'mask', 'mask', 'transforms', 'transforms', 'mask', 'mask' ]
n = len(input_image_suffixes) - 1
attributes_list = [ pet_attributes ] + [ t1_attributes ] * n

if not os.path.exists(out_dir) : os.mkdir(out_dir)    

for input_dir, attributes, input_image_suffix, output_image_suffix, folder_name in zip(input_dirs, attributes_list, input_image_suffixes, output_image_suffixes, folder_names ):
    copy_paths(input_dir, out_dir, attributes, input_image_suffix, output_image_suffix, folder_name)

