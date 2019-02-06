import os
import numpy as np
import tempfile
import shutil
import json
import nipype.interfaces.minc as minc
import ntpath
import minc as pyezminc
from os.path import basename
import shutil
from math import *
from time import gmtime, strftime
from glob import glob
import re

from pyminc.volumes.factory import *

from nipype.algorithms.misc import Gunzip
import nipype.pipeline.engine as pe
import nipype.interfaces.utility as niu
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath,
        BaseInterface, OutputMultiPath, BaseInterfaceInputSpec, isdefined)
from nipype.utils.filemanip import (load_json, save_json, split_filename, fname_presuffix, copyfile)
from nipype.interfaces.utility import Rename
from nipype.interfaces.minc import Resample as ResampleCommand
from Extra.minc_filemanip import update_minchd_json
from Extra.info import  InfoCommand
from Extra.modifHeader import ModifyHeaderCommand, FixCosinesCommand
from Extra.reshape import  ReshapeCommand
from Extra.modifHeader import FixHeaderCommand
#from Extra.compression import gunzipCommand, gzipCommand


global isotope_dict
isotope_dict={
        "C-11" : 20.334*60 ,
        "F-18" : 109.7*60,
        "O-15" : 122.24
        }

def string_test(s):
    t = type(s)
    if  t == str : return True
    elif t == unicode : return True
    elif t == ascii : return True
    return False


def recursive_dict_search(d, target, level=0):
    if level == 0 : print("Target:", target)
    level+=1
    for k,v  in zip(d.keys(), d.values()) :

        #End condition
        if string_test(k) :
            if target.lower() in k.lower().split("_") :
                return [k]

        #Search dictionary
        if type(v) == dict :
            test = [k] + recursive_dict_search(v, target, level)
            if not None in test :
                return test

    return [None]

def fix_df(d, target):
    dict_path = recursive_dict_search(d,target)
    temp_d = d
    value=None
    if not None in dict_path :
        for i in dict_path :
            temp_d = temp_d[i]
        value = temp_d[0]
    return value

def set_isotope_halflife(d, user_halflife=None, target="halflife"):
    #find path in dictionary to target
    dict_path = recursive_dict_search(d, target=target)
    #if there is no path to target, try backup
    if None in dict_path :
        isotope  = fix_df(d, "isotope")
        try :
            halflife = isotope_dict[ isotope ]
        except KeyError :
            if user_halflife != None :
                halflife = user_halflife
            else :
                print("Could not find either halflife or isotope")
                exit(1)
    else :
        temp_d = d
        for i in dict_path :
            temp_d = temp_d[i]
        halflife = temp_d

    if type(halflife) == list :
        halflife=halflife[0]

    try :
        d["acquisition"]
    except :
        d["acquisition"]={"radionuclide_halflife": halflife }
    else :
        d["acquisition"]["radionuclide_halflife"] = halflife

    return d



def set_frame_duration(d, minc_input=False, json_frame_path=["Time","FrameTimes","Values"], verbose=True):
    #find path in dictionary to target
    #dict_path = recursive_dict_search(d, target="FrameLengths")

    #if minc_input : # MINC Input
    #    print("Check header for MINC input")
    #    dict_path = recursive_dict_search(d, target="frames-length")
    #    temp_d = d
    #    for i in dict_path :
    #        temp_d = temp_d[i]
    #    FrameLengths=temp_d

    #    values_dict_path = recursive_dict_search(d, target="frames-time")
    #
    #    Values=None
    #
    #    if not None in values_dict_path :
    #        temp_d = d
    #        if verbose : print( values_dict_path )
    #        for i in values_dict_path :
    #            temp_d = temp_d[i]
    #            print(temp_d)
    #
    #    temp_d = [ float(i) for i in temp_d ]
    #    FrameLengths=list(np.diff(temp_d))
    #    FrameLengths.append(FrameLengths[-1])
    #    print("Warning: Could not find FrameLengths in header. Setting last frame to equal duration of second to last frame.")
    #    x = np.array(temp_d).astype(float)+np.array(FrameLengths).astype(float)
    #    Values=zip( temp_d, x.astype(str)  )

    #    d["Time"]={}
    #    d["Time"]["FrameTimes"]={}
    #    d["Time"]["FrameTimes"]["Duration"] = FrameLengths
    #    d["Time"]["FrameTimes"]["Values"] =Values
    #else : #NIFTI Input
    frame_times=[]
    try :
        frame_times = d["Time"]["FrameTimes"]["Values"]
    except KeyError :
        print("\nError Could not find Time:FrameTimes:Values in header\n")
        exit(1)
    FrameLengths=[]

    c0=c1=1 #Time unit conversion variables. Time should be in seconds
    try :
        if d["Time"]["FrameTimes"]["Units"][0] == 'm' :
            c0=60
        elif d["Time"]["FrameTimes"]["Units"][0] == 'h' :
            c0=60*60
        if d["Time"]["FrameTimes"]["Units"][1] == 'm' :
            c1=60
        elif d["Time"]["FrameTimes"]["Units"][1] == 'h' :
            c1=60*60
    except KeyError :
        print("\nError Could not find Time:FrameTimes:Units in header\n")
        exit(1)

    for s, e in frame_times :
        FrameLengths.append(c1*e - c0*s)

    d["Time"]["FrameTimes"]["Duration"] = FrameLengths

    return d


def unique_file(files, attributes, verbose=False):

    out_files=[]
    for f in files :
        skip=False
        for a in attributes :
            if not a in f :
                skip=True
                break
        if verbose : print(f,'skip file=', skip)
        if not skip :
            out_files.append(f)

    if attributes == [] or len(out_files) == 0 : return ''

    #Check if out_files contains gzip compressed and uncompressed versions of the same file
    if len(out_files) == 2 :
        if out_files[0] == out_files[1]+'.gz' or out_files[1] == out_files[0]+'.gz':
            #Check if '.gz' is in the path extension for the located file.
            #If so remove the file without .gz in the extension from the list of out_files
            if '.gz' in os.path.splitext(out_files[1])[1] :
                out_files.remove(out_files[0])
            else :
                out_files.remove(out_files[1])

    if len(out_files) > 1 :
        print("Error: PET files are not uniquely specified. Multiple files found for ", attributes)
        print("You can used --acq and --rec to specify the acquisition and receptor")
        print(out_files)
        exit(1)

    return( out_files[0] )


def gen_args(opts, subjects):
    session_ids = opts.sessionList 
    task_ids = opts.taskList 
    run_ids = opts.runList
    acq = opts.acq 
    rec = opts.rec
    
    task_args=[]
    sub_ses_args=[]
    sub_ses_dict={}
    test_arg_list=[]
    if len(session_ids) == 0 : session_ids=['']
    if len(task_ids) == 0 : task_ids=['']
    if len(run_ids) == 0 : run_ids=['']

    for sub in subjects:
        if opts.verbose: print("Sub:", sub)
        for ses in session_ids:
            if opts.verbose: print("Ses:",ses)
            for task in task_ids:
                if opts.verbose: print("Task:",task)
                for run in run_ids:
                    sub_arg='sub-'+sub
                    ses_arg='ses-'+ses
                    task_arg=rec_arg=acq_arg=""

                    pet_fn=mri_fn=""
                    if  acq == '': acq_arg='acq-'+acq
                    if  rec == '': rec_arg='rec-'+rec
                    pet_string=opts.sourceDir+os.sep+ sub_arg + os.sep+ '*'+ ses_arg + os.sep+ 'pet/*_pet.mnc'
                    pet_string_gz=opts.sourceDir+os.sep+ sub_arg + os.sep+ '*'+ ses_arg + os.sep+ 'pet/*_pet.mnc.gz'
                    pet_list=glob(pet_string) + glob(pet_string_gz)
                    arg_list = ['sub-'+sub, 'ses-'+ses]
                    mri_arg_list = ['sub-'+sub, 'ses-'+ses]
                    if not task == '': arg_list += ['task-'+task]
                    if not acq == '': arg_list += ['acq-'+acq]
                    if not rec == '': arg_list += ['rec-'+rec]
                    if not run == '': arg_list += ['run-'+run]
                    if opts.verbose : print( arg_list );
                    if pet_list != []:
                        pet_fn = unique_file(pet_list, arg_list, opts.verbose )
                    mri_list=glob(opts.sourceDir+os.sep+ sub_arg + os.sep + '*/anat/*_T1w.mnc' ) + glob(opts.sourceDir+os.sep+ sub_arg + os.sep + '*/anat/*_T1w.mnc.gz' )
                    if mri_list != []:
                        mri_fn = unique_file(mri_list, mri_arg_list )
                    #if pet_fn == [] or mri_fn == [] : continue

                    if os.path.exists(pet_fn) and os.path.exists(mri_fn):
                        #compression=''
                        #if '.gz' in pet_fn : compression='.gz'

                        d={'task':task, 'ses':ses, 'sid':sub, 'run':run} #,'compression':compression}
                        sub_ses_dict[sub]=ses
                        if opts.verbose :
                            print(pet_fn, os.path.exists(pet_fn))
                            print(mri_fn, os.path.exists(mri_fn))
                            print('Adding to dict of valid args',d)
                        task_args.append(d)
                    else:
                        if not os.path.exists(pet_fn) and opts.verbose :
                            print "Could not find PET for ", sub, ses, task, pet_fn
                        if not os.path.exists(mri_fn) and opts.verbose :
                            print "Could not find T1 for ", sub, ses, task, mri_fn

    for key, val in sub_ses_dict.items() :
        sub_ses_args.append({"sid":key,"ses":ses})

    if opts.verbose :
        print("Args:\n", task_args)
    
    opts.sub_valid_args = sub_ses_args
    opts.task_valid_args = task_args

    return sub_ses_args, task_args


class SplitArgsOutput(TraitedSpec):
    cid = traits.Str(mandatory=True, desc="Condition ID")
    sid = traits.Str(mandatory=True, desc="Subject ID")
    task = traits.Str(desc="Task ID")
    ses = traits.Str(desc="Session ID")
    run = traits.Str(desc="Run ID")
    #compression = traits.Str(desc="Compression")
    RoiSuffix = traits.Str(desc="Suffix for subject ROI")

class SplitArgsInput(BaseInterfaceInputSpec):
    task = traits.Str(desc="Task ID")
    ses = traits.Str(desc="Session ID")
    sid = traits.Str(desc="Subject ID")
    cid = traits.Str(desc="Condition ID")
    run = traits.Str(desc="Run ID")
    #compression = traits.Str(desc="Compression")
    ses_sub_only = traits.Bool(default_value=False, usedefault=True)
    #study_prefix = traits.Str(mandatory=True, desc="Study Prefix")
    RoiSuffix = traits.Str(desc="Suffix for subject ROI")
    args = traits.Dict(mandatory=True, desc="Overwrite output file")

class SplitArgsRunning(BaseInterface):
    input_spec = SplitArgsInput
    output_spec = SplitArgsOutput
    def _run_interface(self, runtime):
        cid=''
        if not isdefined(self.inputs.ses) :
            self.inputs.ses=self.inputs.args['ses']
            cid = cid + '_' +self.inputs.args['ses']
        if not isdefined(self.inputs.sid) :
            self.inputs.sid=self.inputs.args['sid']
        if self.inputs.ses_sub_only : return runtime

            #self.inputs.cid=+'_'+self.inputs.args['task']+'_'+self.inputs.args['run']

        try :
            self.inputs.task=self.inputs.args['task']
            cid = cid + '_' +self.inputs.args['task']
        except  KeyError:
            pass

        try:
            self.inputs.run=self.inputs.args['run']
            cid = cid + '_' +self.inputs.args['run']
        except  KeyError:
            pass
        self.inputs.cid=cid
        #try:
        #    self.inputs.compression=self.inputs.args['compression']
        #except  KeyError:
        #    pass

        if isdefined(self.inputs.RoiSuffix):
            self.inputs.RoiSuffix=self.inputs.RoiSuffix
        return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()
        if isdefined(self.inputs.cid):
            outputs["cid"] = self.inputs.cid
        if isdefined(self.inputs.sid):
            outputs["sid"] = self.inputs.sid

        if isdefined(self.inputs.ses):
            outputs["ses"] = self.inputs.ses

        if isdefined(self.inputs.task):
            outputs["task"] = self.inputs.task

        if isdefined(self.inputs.run):
            outputs["run"] = self.inputs.run

        #if isdefined(self.inputs.compression):
        #    outputs["compression"] = self.inputs.compression

        if isdefined(self.inputs.RoiSuffix):
            outputs["RoiSuffix"]= self.inputs.RoiSuffix
        return outputs

class MincHdrInfoOutput(TraitedSpec):
    out_file = File(desc="Output file")
    header = traits.Dict(desc="Dictionary")


class MincHdrInfoInput(BaseInterfaceInputSpec):
    in_file = File(exists=True, mandatory=True, desc="Native dynamic PET image")
    halflife = traits.Float(desc="Radioisotope halflife (in seconds)")
    json_header = File(desc="PET header")
    out_file = File(desc="Output file")

    clobber = traits.Bool(usedefault=True, default_value=True, desc="Overwrite output file")
    run = traits.Bool(usedefault=True, default_value=True, desc="Run the commands")
    verbose = traits.Bool(usedefault=True, default_value=True, desc="Write messages indicating progress")

class MincHdrInfoRunning(BaseInterface):
    input_spec = MincHdrInfoInput
    output_spec = MincHdrInfoOutput
    _suffix = ".info"
    _params={}

    def _run_interface(self, runtime):
        if not isdefined(self.inputs.out_file):
            fname = os.path.splitext(os.path.basename(self.inputs.in_file))[0]
            dname = os.getcwd() #os.path.dirname(self.inputs.nativeT1)
            self.inputs.out_file = dname+ os.sep+fname + self._suffix
        try :
            os.remove(self.inputs.out_file)
        except OSError:
            pass

        #pettot1_4d_header_fixed = pe.Node(interface=FixHeaderCommand(), name="pettot1_4d_header_fixed")
        #pettot1_4d_header_fixed.inputs.time_only=True
        #pettot1_4d_header_fixed.inputs.in_file = fixIrregular.inputs.out_file
        #pettot1_4d_header_fixed.inputs.header = self.inputs.header

        class InfoOptions:
            def __init__(self, command, variable, attribute, type_):
                self.command = command
                self.variable = variable
                self.attribute = attribute
                self.type_ = type_

        #options = [ InfoOptions('-dimnames','time','dimnames','string'),
        #        InfoOptions('-varvalue time','time','frames-time','integer'),
        #        InfoOptions('-varvalue time-width','time','frames-length','integer') ]
        temp_out_file=os.getcwd()+os.sep+"temp.json"
        #for opt in options:
        #    run_mincinfo=InfoCommand()
        #    run_mincinfo.inputs.in_file = self.inputs.in_file
        #    run_mincinfo.inputs.out_file = temp_out_file
        #    run_mincinfo.inputs.opt_string = opt.command
        #    run_mincinfo.inputs.json_var = opt.variable
        #    run_mincinfo.inputs.json_attr = opt.attribute
        #    run_mincinfo.inputs.json_type = opt.type_
        #    run_mincinfo.inputs.error = 'unknown'

        #    print run_mincinfo.cmdline
        #    if self.inputs.run:
        #        run_mincinfo.run()
        try :
            img = pyezminc.Image(self.inputs.in_file, metadata_only=True)
            hd = img.get_MINC_header()
            for key in hd.keys():
                self._params[key]={}
                for subkey in hd[key].keys():
                    self._params[key][subkey]={}
                    data_in = hd[key][subkey]
                    var = str(key)
                    attr = str(subkey)
                    #Populate dictionary with some useful image parameters (e.g., world coordinate start values of dimensions)
                    self._params[key][subkey]=data_in
                    update_minchd_json(temp_out_file, data_in, var, attr)
        except RuntimeError :
            print("Warning: Could not read header file from", self.inputs.in_file)


        header = json.load(open(temp_out_file, "r+") )
        #fp.close()

        minc_input=True
        if not isdefined(self.inputs.json_header) :
            print("Error: could not find json file", self.inputs.json_header)
            exit(1)

        json_header = json.load(open(self.inputs.json_header, "r+"))
        header.update(json_header)
        minc_input=False

        header = set_frame_duration(header, minc_input)
        header = set_isotope_halflife(header, self.inputs.halflife, 'halflife')

        fp=open(self.inputs.out_file, "w+")
        fp.seek(0)
        json.dump(header, fp, sort_keys=True, indent=4)
        fp.close()

        self._params=header

        return runtime


    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file
        outputs["header"] = self._params
        return outputs

class VolCenteringOutput(TraitedSpec):
    out_file = File(desc="Image after centering")

class VolCenteringInput(BaseInterfaceInputSpec):
    in_file = File(position=0, argstr="%s", mandatory=True, desc="Image")
    header = File(desc="Header")
    out_file = File(argstr="%s", desc="Image after centering")

    run = traits.Bool(argstr="-run", usedefault=True, default_value=True, desc="Run the commands")
    verbose = traits.Bool(argstr="-verbose", usedefault=True, default_value=True, desc="Write messages indicating progress")

class VolCenteringRunning(BaseInterface):
    input_spec = VolCenteringInput
    output_spec = VolCenteringOutput
    _suffix = "_center"

    def _run_interface(self, runtime):
        if not isdefined(self.inputs.out_file):
            fname = os.path.splitext(os.path.basename(self.inputs.in_file))[0]
            dname = dname = os.getcwd()
            self.inputs.out_file = dname + os.sep + fname + self._suffix + '.mnc'

        temp_fn="/tmp/tmp_mnc_"+ strftime("%Y%m%d%H%M%S", gmtime())+str(np.random.randint(9999999999))+".mnc"
        shutil.copy(self.inputs.in_file, temp_fn)
        infile = volumeFromFile(self.inputs.in_file)
        for view in ['xspace','yspace','zspace']:
            #start = -1*infile.separations[infile.dimnames.index(view)]*infile.sizes[infile.dimnames.index(view)]/2
            dim = infile.dimnames.index( view )
            start = infile.starts[dim]

            run_modifHrd=ModifyHeaderCommand()
            run_modifHrd.inputs.in_file = temp_fn
            run_modifHrd.inputs.dinsert = True;
            run_modifHrd.inputs.opt_string = view+":start="+str(start);
            run_modifHrd.run()

        node_name="fixIrregularDimension"
        fixIrregular = ModifyHeaderCommand()
        #-dinsert xspace:direction_cosines=1,0,0 -dinsert yspace:direction_cosines=0,1,0 -dinsert zspace:direction_cosines=0,0,1
        fixIrregular.inputs.opt_string = " -sinsert time:spacing=\"regular__\" -sinsert time-width:spacing=\"regular__\" -sinsert xspace:spacing=\"regular__\" -sinsert yspace:spacing=\"regular__\" -sinsert zspace:spacing=\"regular__\""
        fixIrregular.inputs.in_file = temp_fn
        print( fixIrregular.cmdline )
        fixIrregular.run()

        fixCosine = FixCosinesCommand()
        fixCosine.inputs.in_file = fixIrregular.inputs.out_file
        fixCosine.inputs.keep_real_range=True
        fixCosine.inputs.dircos=True
        fixCosine.run()
        print(fixCosine.cmdline)
        shutil.copy(fixCosine.inputs.out_file, self.inputs.out_file)
        return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file

        return outputs

class get_stepOutput(TraitedSpec):
    step =traits.Str(desc="Step size (X, Y, Z)")

class get_stepInput(BaseInterfaceInputSpec):
    in_file = File(position=0, argstr="%s", mandatory=True, desc="Step size (X, Y, Z)")
    step = traits.Str( desc="Image after centering")


class get_stepCommand(BaseInterface):
    input_spec = get_stepInput
    output_spec = get_stepOutput

    def _run_interface(self, runtime):
        img = volumeFromFile(self.inputs.in_file)
        zi=img.dimnames.index('zspace')
        yi=img.dimnames.index('yspace')
        xi=img.dimnames.index('xspace')
        zstep = img.separations[zi]
        ystep = img.separations[yi]
        xstep = img.separations[xi]
        self.inputs.step = str(xstep) +' ' + str(ystep) +' '+str(zstep)
        return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["step"] = self.inputs.step
        return outputs

class pet3DVolumeOutput(TraitedSpec):
    out_file = File(desc="Image after centering")

class pet3DVolumeInput(BaseInterfaceInputSpec):
    in_file = File(position=0, argstr="%s", mandatory=True, desc="Image")
    out_file = File(argstr="%s", desc="Image after centering")
    verbose = traits.Bool(argstr="-verbose", usedefault=True, default_value=True, desc="Write messages indicating progress")

class pet3DVolume(BaseInterface):
    input_spec = pet3DVolumeInput
    output_spec = pet3DVolumeOutput
    _suffix = "_3D"

    def _gen_output(self, basefile, _suffix):
        fname = ntpath.basename(basefile)
        fname_list = os.path.splitext(fname) # [0]= base filename; [1] =extension
        dname = os.getcwd()
        return dname+ os.sep+fname_list[0] + _suffix + fname_list[1]

    def _run_interface(self, runtime):
        #tmpDir = tempfile.mkdtemp()
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_output(self.inputs.in_file, self._suffix)
        infile = volumeFromFile(self.inputs.in_file)
        rank=10

        #If there is no "time" dimension (i.e., in 3D file), then set nFrames to 1
        try :
            nFrames = infile.sizes[infile.dimnames.index("time")]
        except ValueError :
            nFrames = 1

        if nFrames > 5 :
            first=int(ceil(float(nFrames*rank)/100))
            last=int(nFrames)-int(ceil(float(nFrames*4*rank)/100))
            count=last-first
            run_mincreshape=ReshapeCommand()
            run_mincreshape.inputs.dimrange = 'time='+str(first)+','+str(count)
            run_mincreshape.inputs.in_file = self.inputs.in_file
            run_mincreshape.run()

            temp_fn = run_mincreshape.inputs.out_file
        else :
            temp_fn = self.inputs.in_file
        
        petAverage = minc.Average()
        petAverage.inputs.avgdim = 'time'
        petAverage.inputs.width_weighted = False
        petAverage.inputs.clobber = True
        petAverage.inputs.input_files = [ temp_fn  ] 
        petAverage.inputs.output_file = self.inputs.out_file
        petAverage.run()

        return runtime

    def _list_outputs(self):
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_output(self.inputs.in_file, self._suffix)
        
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file
        
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = fname_presuffix(self.inputs.in_file, suffix=self._suffix)
        return outputs

"""
.. module:: initialization
    :platform: Unix
    :synopsis: Workflow to initialize PET images
.. moduleauthor:: Thomas Funck <tffunck@gmail.com>
"""

def get_workflow(name, infosource, opts):
    '''
    Nipype workflow that initializes the PET images by
        1. Centering the PET image: petCenter
        2. Exlcude start and end frames: petExcludeFr
        3. Average 4D PET image into 3D image: petVolume
        4. Extract information from header

    :param name: Name of workflow
    :param infosource: Infosource for basic variables like subject id (sid) and condition id (cid)
    :param datasink: Node in which output data is sent
    :param opts: User options

    :returns: workflow
    '''
    workflow = pe.Workflow(name=name)

    #Define input node that will receive input from outside of workflow
    default_field=["pet","json_header"] # ["pet", "t1"]
    inputnode = pe.Node(niu.IdentityInterface(fields=default_field), name='inputnode')

    #Define empty node for output
    outputnode = pe.Node(niu.IdentityInterface(fields=["pet_header_dict","pet_header_json","pet_center","pet_volume"]), name='outputnode')

    node_name="petCenter"
    petCenter= pe.Node(interface=VolCenteringRunning(), name=node_name)
    petCenter.inputs.verbose = opts.verbose

    node_name="petVolume"
    petVolume = pe.Node(interface=pet3DVolume(), name=node_name)
    petVolume.inputs.verbose = opts.verbose

    node_name="petSettings"
    petSettings = pe.Node(interface=MincHdrInfoRunning(), name=node_name)
    petSettings.inputs.halflife = opts.halflife
    petSettings.inputs.clobber = True

    workflow.connect([(inputnode, petCenter, [('pet', 'in_file')])])

    workflow.connect([(petCenter, petSettings, [('out_file', 'in_file')])])
    workflow.connect(inputnode, 'json_header', petSettings, 'json_header')
    workflow.connect([(petCenter, petVolume, [('out_file', 'in_file')])])


    workflow.connect(petSettings, 'header', outputnode, 'pet_header_dict')
    workflow.connect(petSettings, 'out_file', outputnode, 'pet_header_json')
    workflow.connect(petCenter, 'out_file', outputnode, 'pet_center')
    workflow.connect(petVolume, 'out_file', outputnode, 'pet_volume')

    return(workflow)
