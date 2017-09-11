import pandas as pd
import numpy as np
import nipype.pipeline.engine as pe
import nipype.interfaces.utility as niu
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath, 
                                     BaseInterface, OutputMultiPath, BaseInterfaceInputSpec, isdefined)
import pyminc.volumes.factory as pyminc
import os
from  nipype.interfaces.minc import Blur
from Quality_Control.outlier import lof, kde, MAD, lcf

outlier_measures={"KDE":kde }

class pvc_qc_metricsOutput(TraitedSpec):
    out_file = traits.File(desc="Output file")

class pvc_qc_metricsInput(BaseInterfaceInputSpec):
    pve = traits.File(exists=True, mandatory=True, desc="Input PVE PET image")
    pvc = traits.File(exists=True, mandatory=True, desc="Input PVC PET")
    fwhm = traits.List(desc='FWHM of the scanner')
    sub = traits.Str("Subject ID")
    task = traits.Str("Task")
    ses = traits.Str("Ses")
    out_file = traits.File(desc="Output file")

class pvc_qc_metrics(BaseInterface):
    input_spec = pvc_qc_metricsInput 
    output_spec = pvc_qc_metricsOutput
  
    def _gen_output(self, sid, ses, task, fname ="pvc_qc_metric.csv"):
        dname = os.getcwd() 
        return dname + os.sep + sid + '_' + ses + '_'+ task + "_" + fname

    def _run_interface(self, runtime):
        sub = self.inputs.sub
        ses = self.inputs.ses
        task = self.inputs.task
        smoothNode = pe.Node( Blur(), name="blur_pvc")
        smoothNode.inputs.fwhm3d = tuple(self.inputs.fwhm)
        smoothNode.inputs.input_file = self.inputs.pvc
        
        pve = pyminc.volumeFromFile(self.inputs.pve)
        pvc_blur = pyminc.volumeFromFile(self.inputs.pvc)
        
        mse = 0 
        for t in range(pve.sizes[0]):
            pve_frame = pve.data[t,:,:,:]
            pvc_frame = pvc_blur.data[t,:,:,:]
            
            mse += np.sum(np.sqrt((pve_frame.flatten() - pvc_frame.flatten())**3))
        metric = ["MSE"] * pve.sizes[0] 
        df = pd.DataFrame([[sub,ses,task,metric,value]], columns=["sub","ses","task","metric",'value'])
        df.fillna(0, inplace=True)
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_output(self.inputs.sub, self.inputs.ses, self.inputs.task)
        df.to_csv(self.inputs.out_file, index=False)

        return runtime


    def _list_outputs(self):
        outputs = self.output_spec().get()
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self.inputs._gen_output(self.inputs.sid, self.inputs.cid)
        outputs["out_file"] = self.inputs.out_file
        
        return outputs

class pvc_outlier_measuresOutput(TraitedSpec):
    out_file = traits.File(desc="Output file")

class pvc_outlier_measuresInput(BaseInterfaceInputSpec):
    in_file = traits.File(desc="Input file")
    out_file = traits.File(desc="Output file")
    clobber = traits.Bool(desc="Overwrite output file", default=False)


class pvc_outlier_measuresCommand(BaseInterface):
    input_spec = pvc_outlier_measuresInput 
    output_spec = pvc_outlier_measuresOutput
  
    def _gen_output(self, fname ="pvc_measures.csv"):
        dname = os.getcwd() + os.sep + fname
        return dname

    def _run_interface(self, runtime):
        
        df = pd.read_csv( self.inputs.in_file  )
        out_columns=['sub','ses','task','metric','measure', 'value'] 
        df_out = pd.DataFrame(columns=out_columns)
        for ses, ses_df in df.groupby(['ses']):
            for task, task_df in df.groupby('task'):
                for measure, measure_name in zip(outlier_measures.values(), outlier_measures.keys()):
                    r=pd.Series(measure(task_df.value.values).flatten())
                    #r=measure(metric_df.Value.values)
                    #Get column number of the current outlier measure Reindex the test_df from 0 to the number of rows it has
                    #Get the series with the calculate the distance measure for the current measure
                    task_df.index=range(task_df.shape[0])
                    task_df['value'] = r 
                    task_df['measure'] = [measure_name] * task_df.shape[0] 
                    df_out = pd.concat([df_out, task_df], axis=0)
        if not isdefined( self.inputs.out_file ) : 
            self.inputs.out_file = self._gen_output()
        df_out.to_csv(self.inputs.out_file,index=False)
        
        return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()
        if not isdefined( self.inputs.out_file) :
            self.inputs.out_file = self._gen_output()
        outputs["out_file"] = self.inputs.out_file
        return outputs


