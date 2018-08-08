import os
import nipype
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath, 
                                     BaseInterface, OutputMultiPath, BaseInterfaceInputSpec, isdefined)
from Extra.base import MINCCommand, MINCCommandInputSpec, Info
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath,isdefined)
from scipy.integrate import simps
import pandas as pd
import numpy as np
import nipype.pipeline.engine as pe
import nipype.interfaces.io as nio
import nipype.interfaces.utility as util
import nipype.interfaces.utility as niu

from Extra.concat import concat_df
from Quality_Control.qc import metric_columns

results_columns = metric_columns + ['frame']
"""
.. module:: Results_Report.results
    :platform: Unix
    :synopsis: Module to get results from output image
.. moduleauthor:: Thomas Funck <tffunck@gmail.com>
"""
######################################
# Group level descriptive statistics #
######################################
def group_level_descriptive_statistics(opts, args):
    vol_surf_list = ['']

    if opts.use_surfaces : 
        vol_surf_list += ['surf']

    for surf in vol_surf_list:
        print(surf, "\n")
        #Setup workflow
        workflow = pe.Workflow(name=opts.preproc_dir)
        workflow.base_dir = opts.targetDir
        
        #Datasink
        datasink=pe.Node(interface=nio.DataSink(), name="output")
        datasink.inputs.base_directory= opts.targetDir+os.sep+os.sep+"stats"+os.sep+surf
        datasink.inputs.substitutions = [('_cid_', ''), ('sid_', '')]

        #Datagrabber
        if not opts.test_group_qc : scan_stats_dict = dict(scan_stats='*'+os.sep+'results_'+surf+'*'+os.sep+'*_3d.csv')
        else : scan_stats_dict = dict(scan_stats='*'+os.sep+'*'+os.sep+'results_'+surf+'*'+os.sep+'*_3d.csv')

        datasource = pe.Node( interface=nio.DataGrabber( outfields=['scan_stats'], raise_on_empty=True, sort_filelist=False), name="datasource")
        datasource.inputs.base_directory = opts.targetDir + os.sep +opts.preproc_dir
        datasource.inputs.template = '*'
        datasource.inputs.field_template = scan_stats_dict

        #Concatenate descriptive statistics
        concat_statisticsNode=pe.Node(interface=concat_df(), name="concat_statistics")
        concat_statisticsNode.inputs.out_file="descriptive_statistics.csv"
        workflow.connect(datasource, 'scan_stats', concat_statisticsNode, 'in_list')
        workflow.connect(concat_statisticsNode, "out_file", datasink, 'results')
       
        #Calculate descriptive statistics
        descriptive_statisticsNode = pe.Node(interface=descriptive_statisticsCommand(), name="descriptive_statistics")
        workflow.connect(concat_statisticsNode, 'out_file', descriptive_statisticsNode, 'in_file')
        workflow.connect(descriptive_statisticsNode, "sub", datasink, 'sub')
        workflow.connect(descriptive_statisticsNode, "ses", datasink, 'ses')
        workflow.connect(descriptive_statisticsNode, "task", datasink, 'task')
        workflow.connect(descriptive_statisticsNode, "sub_task", datasink, 'sub_task')
        workflow.connect(descriptive_statisticsNode, "sub_ses", datasink, 'sub_ses')
        workflow.run()

class resultsInput(MINCCommandInputSpec):   
    in_file = traits.File(desc="Input file ")
    mask = traits.File(desc="ROI PET mask ")
    surf_mesh = traits.File(desc="Surface mesh (.obj) ")
    surf_mask = traits.File(desc="Surface mask (.txt) ")
    header = traits.Dict(desc="PET Header")
    out_file_3d = traits.File(desc="3d Output file ")
    out_file_4d = traits.File(desc="4d Output file ")
    dim = traits.Str("Number of dimensions")
    sub = traits.Str("Subject ID")
    task = traits.Str("Task")
    ses = traits.Str("Ses")
    node  = traits.Str(mandatory=True, desc="Node name")

class resultsOutput(TraitedSpec):
    out_file_3d = traits.File(desc="3D Output file ")
    out_file_4d = traits.File(desc="4D Output file ")

class resultsCommand( BaseInterface):
    input_spec = resultsInput
    output_spec = resultsOutput
    
    def _gen_output(self, in_file):
        print "\n\n",in_file,"\n\n"
        ii =  os.path.splitext(os.path.basename(in_file))[0]
        out_file_3d = os.getcwd() + os.sep + ii + "_3d.csv"
        out_file_4d = os.getcwd() + os.sep + ii + "_4d.csv"
        return [out_file_3d, out_file_4d]

    def _run_interface(self, runtime):
        print '\n\n', self.inputs.in_file, '\n\n'
        if not isdefined(self.inputs.out_file_3d) or not isdefined(self.inputs.out_file_4d) :
            [self.inputs.out_file_3d, self.inputs.out_file_4d ]=self._gen_output(self.inputs.in_file)

        resultsReport = groupstatsCommand()
        resultsReport.inputs.image = self.inputs.in_file
        resultsReport.inputs.vol_roi = self.inputs.mask
        if  isdefined(self.inputs.surf_mesh) and isdefined(self.inputs.surf_mask) :
            resultsReport.inputs.surf_roi = self.inputs.surf_mesh + ' ' + self.inputs.surf_mask
        resultsReport.inputs.out_file = os.getcwd()+os.sep+'temp.csv'
        print resultsReport.cmdline
        resultsReport.run()
        add_csvInfoNode = add_csvInfoCommand()
        add_csvInfoNode.inputs.in_file = resultsReport.inputs.out_file
        add_csvInfoNode.inputs.sub = self.inputs.sub
        add_csvInfoNode.inputs.ses = self.inputs.ses
        add_csvInfoNode.inputs.task =self.inputs.task
        add_csvInfoNode.inputs.node =self.inputs.node
        if self.inputs.dim == '4': add_csvInfoNode.inputs.out_file = self.inputs.out_file_4d
        else: add_csvInfoNode.inputs.out_file = self.inputs.out_file_3d
        add_csvInfoNode.run()

        
        if self.inputs.dim == '4':
            integrate_resultsReport = integrate_TACCommand()
            integrate_resultsReport.inputs.header = self.inputs.header
            integrate_resultsReport.inputs.in_file = add_csvInfoNode.inputs.out_file
            integrate_resultsReport.inputs.out_file = self.inputs.out_file_3d
            integrate_resultsReport.run()   
        
        return runtime

    def _list_outputs(self):
        if not isdefined(self.inputs.out_file_3d) or not isdefined(self.inputs.out_file_4d) :
            [ self.inputs.out_file_3d, self.inputs.out_file_4d ]  =self._gen_output(self.inputs.in_file)
        outputs = self.output_spec().get()
        outputs["out_file_3d"] = self.inputs.out_file_3d
        outputs["out_file_4d"] = self.inputs.out_file_4d
        return outputs



class groupstatsInput(MINCCommandInputSpec):   
    image    = traits.File(argstr="-i %s", mandatory=True, desc="Image")  
    vol_roi  = traits.File(argstr="-v %s", desc="Volumetric image containing ROI")  
    surf_roi = traits.File(argstr="-s %s", desc="obj and txt files containing surface ROI")
    out_file = traits.File(argstr="-o %s", desc="Output csv file")
    label = traits.Str(desc="Label for output file")

class groupstatsOutput(TraitedSpec):
    out_file = File(desc="Extract values from PET images based on ROI")

class groupstatsCommand(MINCCommand, Info):
    _cmd = "mincgroupstats"
    input_spec = groupstatsInput
    output_spec = groupstatsOutput
    _suffix='results'
    
    def _parse_inputs(self, label=None, skip=None):
        if skip is None:
            skip = []

        if not isdefined(self.inputs.out_file):
            if label == None: label_str=''
            else : label_str=label + '_'
            self.inputs.out_file = os.getcwd() + os.sep + label_str +  "results.csv" #fname_presuffix(self.inputs.image, suffix=self._suffix)

        return super(groupstatsCommand, self)._parse_inputs(skip=skip)

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file
        return outputs

    def _gen_filename(self, name):
        if name == "out_file":
            return self._list_outputs()["out_file"]
        return None

class add_csvInfoInput(MINCCommandInputSpec):   
    in_file = File(mandatory=True, desc="Input file")
    ses  = traits.Str(mandatory=True, desc="Session")
    task = traits.Str(mandatory=True, desc="Task")
    sub  = traits.Str(mandatory=True, desc="Subject")
    node  = traits.Str(mandatory=True, desc="Node name")
    out_file = File(desc="Output file")

class add_csvInfoOutput(TraitedSpec):
    out_file = File(desc="Output file")

class add_csvInfoCommand(BaseInterface):
    input_spec = add_csvInfoInput
    output_spec = add_csvInfoOutput
    
    def _run_interface(self, runtime):
        sub = self.inputs.sub
        task= self.inputs.task
        ses= self.inputs.ses
        node = self.inputs.node
        
        print "\nadd_csvInfo: ", self.inputs.in_file, "\n"

        df = pd.read_csv( self.inputs.in_file, header=None    ) 
        df.columns= ['ndim', 'roi', 'frame', 'mean','sd','max','min','vol']
        dfo =pd.DataFrame( columns=results_columns)
        dfo["analysis"] = [node] * df.shape[0]
        dfo["sub"] = [sub] * df.shape[0]
        dfo["ses"] = [ses] * df.shape[0]
        dfo["task"] = [task] * df.shape[0]
        dfo["roi"] =  df['roi']
        dfo['metric'] = ['mean'] * df.shape[0]
        dfo['value'] = df['mean']
        if 'frame' in df.columns:
            dfo['frame'] = df['frame']
        else: dfo['frame'] = [0] * df.shape[0]
        dfo = dfo[ results_columns ]

        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_output(self.inputs.in_file)
        dfo.to_csv(self.inputs.out_file, index=False)
        
        return runtime

    def _gen_output(self, basename):
        sbasename = os.path.splitext(basename)
        return sbasename[0]+'_withInfo'+sbasename[1]

    def _list_outputs(self):
        outputs = self.output_spec().get()
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_output(self.inputs.in_file)
        outputs["out_file"] = self.inputs.out_file

        return outputs




class descriptive_statisticsInput(MINCCommandInputSpec):   
    in_file = traits.File(desc="Input file ")
    ses = traits.File(desc="Output averaged by sesion")
    task = traits.File(desc="Output averaged by task")
    sub = traits.File(desc="Output averaged by subject")  
    sub_task = traits.File(desc="Output averaged by subject x task")  
    sub_ses = traits.File(desc="Output averaged by subject x ses")

class descriptive_statisticsOutput(TraitedSpec):
    ses = traits.File(desc="Output averaged by sesion")
    task = traits.File(desc="Output averaged by task")
    sub = traits.File(desc="Output averaged by subject")  
    sub_task = traits.File(desc="Output averaged by subject x task")  
    sub_ses = traits.File(desc="Output averaged by subject x ses")

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
        df = pd.read_csv( self.inputs.in_file   )
#        df_pivot = lambda y : pd.DataFrame(df.pivot_table(rows=y,values=["value"], aggfunc=np.mean).reset_index(level=y))
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
        ii =  os.path.splitext(os.path.basename(in_file))[0]
        out_file = os.getcwd() + os.sep + ii + "_"+label+".csv"
        return out_file

### TKA metrics
class integrate_TACInput(MINCCommandInputSpec):   
    in_file = traits.File(desc="Input file ")
    header = traits.Dict(desc="Input file ")
    out_file = traits.File(desc="Output file ")

class integrate_TACOutput(TraitedSpec):
    out_file = traits.File(desc="Output file ")

class integrate_TACCommand( BaseInterface):
    input_spec = integrate_TACInput
    output_spec = integrate_TACOutput

    def _gen_output(self, in_file):
        ii =  os.path.splitext(os.path.basename(in_file))[0]
        out_file = os.getcwd() + os.sep + ii + "_int.csv"
        return out_file 

    def _run_interface(self, runtime):
        header = self.inputs.header
        df = pd.read_csv( self.inputs.in_file )
        #if time frames is not a list of numbers, .e.g., "unknown",
        #then set time frames to 1
        time_frames = []
        try : 
            float(header['time']['frames-time'][0]) 
            time_frames = [ float(h) for h in  header['time']["frames-time"] ]
        except ValueError : time_frames = []
       
        if time_frames == [] :
            try :
                header['ecat_acquisition']['frame_lengths']
                time_frames = [ float(h) for h in  header['ecat_acquisition']["frame_lengths"] ]
                for i in range(1, len(time_frames)) :
                    time_frames[i] = time_frames[i] + time_frames[i-1]
                    
            except ValueError : 
                time_frames = []
   
        if time_frames == [] : time_frames = [1.]

        out_df = pd.DataFrame( columns=metric_columns)
        for name, temp_df in  df.groupby(["analysis", "sub", "ses", "task", "roi"]):
            print temp_df
            print time_frames
            if len(time_frames) > 1 :
                mean_int = simps(temp_df["value"], time_frames)
                print("Integral of mean:", mean_int)
            else:
                mean_int = temp_df.value.values[0] * time_frames[0]
                print "\n",mean_int, "=", temp_df.value.values[0], "x", time_frames[0], "\n"

            row = pd.DataFrame( [list(name) + ['integral', mean_int]], columns=metric_columns  )
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

