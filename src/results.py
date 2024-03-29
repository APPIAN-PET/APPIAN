import os
import re
import nipype
import json
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath, CommandLine, CommandLineInputSpec, BaseInterface, OutputMultiPath, BaseInterfaceInputSpec, isdefined)
from scipy.integrate import simps
from src.utils import concat_df, splitext
from src.qc import metric_columns
import pandas as pd
import numpy as np
import nipype.pipeline.engine as pe
import nipype.interfaces.io as nio
import nipype.interfaces.utility as util
import nipype.interfaces.utility as niu
import src.ants_nibabel as nib


results_columns = metric_columns + ['frame']
"""
.. module:: src.results
    :platform: Unix
    :synopsis: Module to get results from output image
.. moduleauthor:: Thomas Funck <tffunck@gmail.com>
"""
final_dir="stats"

######################################
# Group level descriptive statistics #
######################################
def group_level_descriptive_statistics(opts, args):
    vol_surf_list = ['']
    #if using surfaces, add an extra set of outputs to iterate over
    if opts.use_surfaces : 
        vol_surf_list += ['_surf']
    print('Hello') 
    for surf in vol_surf_list:
        print('Hello Again')
        #Setup workflow
        workflow = pe.Workflow(name=opts.preproc_dir)
        workflow.base_dir = opts.targetDir
        
        #Datasink
        datasink=pe.Node(interface=nio.DataSink(), name="output")
        datasink.inputs.base_directory= opts.targetDir+os.sep
        datasink.inputs.substitutions = [('_cid_', ''), ('sid_', '')]
    
        #Datagrabber
        scan_stats = '/*'+os.sep+'results'+surf+'*'+os.sep+'*_results.csv'
        scan_stats_dict = dict(scan_stats=scan_stats)
        from glob import glob
        in_list = glob( opts.targetDir + os.sep +opts.preproc_dir + os.sep+scan_stats) 
        

        #output_images='*'+os.sep+'output_images'+os.sep+'*output_images.csv')

        #datasource = pe.Node( interface=nio.DataGrabber( outfields=['scan_stats'], raise_on_empty=True, sort_filelist=False), name="datasource"+surf)
        #datasource = pe.Node( interface=nio.DataGrabber( outfields=['scan_stats','output_images'], raise_on_empty=True, sort_filelist=False), name="datasource"+surf)
        #datasource.inputs.base_directory = opts.targetDir + os.sep +opts.preproc_dir + os.sep
        #datasource.inputs.template = '*'
        #datasource.inputs.field_template = scan_stats_dict


        #Concatenate output files
        #concat_outputfileNode=pe.Node(interface=concat_df(), name="concat_output_images")
        #concat_outputfileNode.inputs.out_file="output_images.csv"
        #workflow.connect(datasource, 'output_images', concat_outputfileNode, 'in_list')
        #workflow.connect(concat_outputfileNode, "out_file", datasink, 'output_images')

        #Concatenate scan-level statistics
        os.makedirs(opts.targetDir+'/stats/',exist_ok=True)
        concat_statisticsNode=pe.Node(interface=concat_df(), name="statistics"+surf)
        concat_statisticsNode.inputs.in_list=in_list
        concat_statisticsNode.inputs.out_file=opts.targetDir+'/stats/descriptive_statistics'+surf+".csv"
        concat_statisticsNode.run()
        #workflow.connect(datasource, 'scan_stats', concat_statisticsNode, 'in_list')
        #workflow.connect(concat_statisticsNode, "out_file", datasink, 'stats/' +surf+'all')
    
        
        if len(args) > 1 :
            print('Calculating descriptive statistics')
            #Calculate descriptive statistics
            descriptive_statisticsNode = pe.Node(interface=descriptive_statisticsCommand(),name="descriptive_statistics"+surf)
            workflow.connect(concat_statisticsNode, 'out_file', descriptive_statisticsNode, 'in_file')
            workflow.connect(descriptive_statisticsNode, "sub", datasink, 'stats/sub')
            workflow.connect(descriptive_statisticsNode, "ses", datasink, 'stats/ses')
            workflow.connect(descriptive_statisticsNode, "task", datasink, 'stats/task')
            workflow.connect(descriptive_statisticsNode, "sub_task", datasink, 'stats/sub_task')
            workflow.connect(descriptive_statisticsNode, "sub_ses", datasink, 'stats/sub_ses')
            workflow.run() 
        else :
            print('Not calculating descriptive statistics because only 1 scan')

def set_roi_labels(unique_labels, roi_labels_file) :
    roi_labels = []
    if os.path.exists(roi_labels_file) :
        df = pd.read_csv(roi_labels_file, header=None,names=['roi','labels'])    
        for label in unique_labels :
            try :
                new_roi_label = df['labels'].loc[ df['roi'] == label ].values[0]
            except IndexError :
                new_roi_label = label
            roi_labels.append(new_roi_label)
        return roi_labels
    else :
        return unique_labels

class resultsInput(TraitedSpec):   
    in_file = traits.File(mandatory=True,exists=True, desc="Input file ")
    out_file = traits.File(desc="Output file ")
    roi_labels_file = traits.File( desc="Output file")
    mask = traits.File(mandatory=True,exists=True,desc="ROI PET mask ")
    surf_left = traits.File(desc="Left Surface mesh (.obj) ")
    mask_left = traits.File(desc="Left Surface mask (.txt) ")
    surf_right = traits.File(desc="Right Surface mesh (.obj) ")
    mask_right = traits.File(desc="Right Surface mask (.txt) ")

    pet_header_json = traits.File(desc="PET Header")
    dim = traits.Str("Number of dimensions")
    sub = traits.Str("Subject ID")
    task = traits.Str(default_value='NA',usedefault=True)
    ses = traits.Str(desc="Ses",usedefault=True,default_value="NA")
    run = traits.Str(desc="Run",usedefault=True,default_value="NA")
    trc = traits.Str(desc="Acquisition",usedefault=True,default_value="NA")
    rec = traits.Str(desc="Reconstruction",usedefault=True,default_value="NA")
    node  = traits.Str(mandatory=True, desc="Node name")

class resultsOutput(TraitedSpec):
    out_file = traits.File(desc="Output file ")

class resultsCommand( BaseInterface):
    input_spec = resultsInput
    output_spec = resultsOutput
    
    def _gen_output(self, in_file, suffix):
        ii =  splitext(os.path.basename(in_file))[0]
        out_file = os.getcwd() + os.sep + ii + suffix +".csv"
        return out_file

    def _run_interface(self, runtime):
        print('1',os.stat(self.inputs.pet_header_json))
        header = json.load(open(self.inputs.pet_header_json, 'r'))
        frames = header['FrameTimes']

        if not isdefined(self.inputs.out_file) :
            self.inputs.out_file=self._gen_output(self.inputs.in_file, '_results')
        
        #Load PET image
        image = nib.load(self.inputs.in_file).get_data()

        print('-->', image.shape[-1], len(frames))
        if len(image.shape) == 4 and image.shape[-1] != len(frames) :
            print('Error: Length of PET time dimension and frames specified in header do not match')
            print(self.inputs.in_file, image.shape[-1])
            print(self.inputs.pet_header_json, len(frames))
            exit(1)
        
        #Load Label image
        labels_all = np.round(nib.load(self.inputs.mask).get_data()).astype(int).reshape(-1,)
        
        #Time Dimensions
        #ti=np.argmin(image.shape) #FIXME : Not a good way to identify time dimension

        #Keep only voxel values above 0
        idx = labels_all > 0
        labels = labels_all[ idx ]

        #Create a replacement label image with continuous label values
        #Example : 10,15,20 --> 1,2,3
        labels_cont = np.zeros(labels.shape).astype(int)
        #Find unique values in labels
        unique_labels = np.unique(labels)
        for i, val in enumerate(unique_labels) :
            labels_cont[ labels == val ] = i
        roi_labels = set_roi_labels(unique_labels, self.inputs.roi_labels_file) 
        
        #Define number of labels
        n=len(unique_labels)
        
        if n == 0 :
            print("\n","Error: No labels in image", self.inputs.roi_labels_file,"\n")
            exit(1)

        #Find number of counts for each label
        counts = np.bincount(labels_cont)
        #Determine if 3D/4D PET image
        if len(image.shape) == 4 :
            nFrames=int(image.shape[3])
        else :
            nFrames=1

        #if nFrames != len(frames) : 
        #    print('Error: frames in json header = {} but frames in PET volume is {}'.format(nFrames,len(frames)))
        #    print("\tVolume file that was read:",self.inputs.in_file)
        #    exit(1)
        
        df_list=[]
        for f in range(nFrames) :
            #Get 3D Frames
            if nFrames != 1 :
                frame_img_all = image[:,:,:,f]
            else :
                frame_img_all = image
            
            #Reshape image and get rid of voxels with 0 values
            frame_img = frame_img_all.reshape(-1,)[ idx ]
            #Get weighted sum for each label in the PET image frame
            sums = np.bincount(labels_cont, weights=frame_img )
            #Calculate srcs from weighted sum and count
            srcs = sums / counts

            #Calculate mid frame
            mid_frame = (float(frames[f][0])+float(frames[f][1]))/2.

            #Create frame
            frame_df=pd.DataFrame({
                'analysis': [self.inputs.node] * n,
                'sub': [self.inputs.sub] * n,
                'ses': [self.inputs.ses] * n,
                'task': [self.inputs.task] * n,
                'run': [self.inputs.run] * n,
                'trc': [self.inputs.trc] * n,
                'rec': [self.inputs.rec] * n,
                'roi': roi_labels,
                'metric': ['mean'] * n,
                'value': srcs,
                'frame':  [mid_frame] * n
                })
            df_list.append(frame_df)
        df=pd.concat(df_list)
        df.sort_values(['analysis','sub','ses','task','run','roi','frame'],inplace=True)
        #print(df)
        df.to_csv(self.inputs.out_file,index=False)
        print('2',os.stat(self.inputs.pet_header_json))

        return runtime

    def _list_outputs(self):
        if not isdefined(self.inputs.out_file) :
            self.inputs.out_file=self._gen_output(self.inputs.in_file, '_results')
        
        outputs = self.output_spec().get()
        outputs['out_file'] = self.inputs.out_file
        return outputs


class descriptive_statisticsInput(CommandLineInputSpec):   
    in_file = traits.File(desc="Input file ")
    ses = traits.File(desc="Output srcd by sesion")
    task = traits.File(desc="Output srcd by task")
    sub = traits.File(desc="Output srcd by subject")  
    sub_task = traits.File(desc="Output srcd by subject x task")  
    sub_ses = traits.File(desc="Output srcd by subject x ses")

class descriptive_statisticsOutput(TraitedSpec):
    ses = traits.File(desc="Output srcd by sesion")
    task = traits.File(desc="Output srcd by task")
    sub = traits.File(desc="Output srcd by subject")  
    sub_task = traits.File(desc="Output srcd by subject x task")  
    sub_ses = traits.File(desc="Output srcd by subject x ses")

class descriptive_statisticsCommand( BaseInterface):
    input_spec = descriptive_statisticsInput
    output_spec = descriptive_statisticsOutput

    def _parse_inputs(self, skip=None):
        if skip is None:
            skip = []
        if not isdefined(self.inputs.in_file):
            self.inputs.out_file = os.getcwd() + os.sep + "results.csv"

        return super(descriptive_statisticsCommand, self)._parse_inputs(skip=skip)

    def _run_interface(self, runtime):
        print('Reading', self.inputs.in_file)
        df = pd.read_csv( self.inputs.in_file   )
#        df_pivot = lambda y : pd.DataFrame(df.pivot_table(rows=y,values=["value"], aggfunc=np.mean).reset_index(level=y))
        print(df)
        df_pivot = lambda y : pd.DataFrame(df.pivot_table(index=y,values=["value"], aggfunc=np.mean).reset_index(level=y))
        ses_df =  df_pivot(["analysis", "metric", "roi", "ses"]) 
        task_df =df_pivot(["analysis", "metric","roi", "task"])  
        sub_df = df_pivot(["analysis", "metric","roi", "sub"])   
        sub_ses_df = df_pivot(["analysis", "metric","roi", "sub","ses"]) 
        sub_task_df = df_pivot(["analysis", "metric","roi", "sub","task"])   

        self.inputs.ses  = self._gen_output(self.inputs.in_file, "ses")
        self.inputs.task  = self._gen_output(self.inputs.in_file, "task")
        self.inputs.sub = self._gen_output(self.inputs.in_file, "sub")
        self.inputs.sub_task  = self._gen_output(self.inputs.in_file, "sub_task")
        self.inputs.sub_ses= self._gen_output(self.inputs.in_file, "sub_ses")

        ses_df.to_csv(self.inputs.ses, index=False) 
        task_df.to_csv(self.inputs.task, index=False)
        sub_df.to_csv(self.inputs.sub, index=False)
        sub_ses_df.to_csv(self.inputs.sub_task, index=False)
        sub_task_df.to_csv(self.inputs.sub_ses, index=False)
        return runtime
    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["ses"] = self.inputs.ses
        outputs["task"] = self.inputs.task
        outputs["sub"] = self.inputs.sub
        outputs["sub_task"] = self.inputs.sub_task
        outputs["sub_ses"] = self.inputs.sub_ses
        return outputs

    def _gen_output(self, in_file, label):
        ii =  splitext(os.path.basename(in_file))[0]
        out_file = os.getcwd() + os.sep + ii + "_"+label+".csv"
        return out_file

### TKA metrics
class integrate_TACInput(CommandLineInputSpec):   
    in_file = traits.File(desc="Input file ")
    header = traits.File(desc="PET Header file ")
    out_file = traits.File(desc="Output file ")

class integrate_TACOutput(TraitedSpec):
    out_file = traits.File(desc="Output file ")

class integrate_TACCommand( BaseInterface):
    input_spec = integrate_TACInput
    output_spec = integrate_TACOutput

    def _gen_output(self, in_file):
        ii =  splitext(os.path.basename(in_file))[0]
        out_file = os.getcwd() + os.sep + ii + "_int.csv"
        return out_file 

    def _run_interface(self, runtime):
        header = json.load(open( self.inputs.header ,"r"))

        
        df = pd.read_csv( self.inputs.in_file )
        #if time frames is not a list of numbers, .e.g., "unknown",
        #then set time frames to 1
        time_frames = []
       
        if time_frames == [] :
            try :
                header['FrameTimes']
                time_frames = [ float(s) for s,e in  header["FrameTimes"] ]
                #for i in range(1, len(time_frames)) :
                #    time_frames[i] = time_frames[i] + time_frames[i-1]
                    
            except ValueError : 
                time_frames = []
   
        if time_frames == [] : time_frames = [1.]
        value_cols=['metric','value']
        groups=list(df.columns.values) #["analysis", "sub", "ses", "task","run", "trc", "rec", "roi"]
        groups = [ i for i in groups if not i in value_cols+['frame'] ] 
        #out_df = pd.DataFrame( columns=metric_columns)
        df.fillna("NA", inplace=True )
        out_df = pd.DataFrame( columns=groups)
        print(df)
        for name, temp_df in  df.groupby(groups):
            if len(time_frames) > 1 :
                print(len(temp_df["value"]) )
                print(len(time_frames))
                print(temp_df)
                mean_int = simps(temp_df["value"], time_frames)
                print("Integral of mean:", mean_int)
            else :
                mean_int = temp_df.value.values[0] * time_frames[0]
            row = pd.DataFrame( [list(name) + ['integral', mean_int]], columns=groups + value_cols  )
            out_df = pd.concat( [out_df, row] )
        out_df["frame"] = [0] * out_df.shape[0]
        if not isdefined(self.inputs.in_file): 
            self.inputs.out_file = self._gen_output(self.inputs.in_file)
        out_df.to_csv(self.inputs.out_file, index=False)

        return runtime


    def _parse_inputs(self):
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file =self._gen_output(self.inputs.in_file)
        return super(integrate_TACCommand, self)._parse_inputs(skip=skip)

    def _list_outputs(self):
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = _gen_output(self.inputs.in_file)
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file
        return outputs

