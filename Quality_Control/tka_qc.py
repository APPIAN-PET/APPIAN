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

class tka_outlier_measuresOutput(TraitedSpec):
    out_file = traits.File(desc="Output file")

class tka_outlier_measuresInput(BaseInterfaceInputSpec):
    in_file = traits.File(desc="Input file")
    out_file = traits.File(desc="Output file")
    clobber = traits.Bool(desc="Overwrite output file", default=False)


class tka_outlier_measuresCommand (BaseInterface):
    input_spec = tka_outlier_measuresInput 
    output_spec = tka_outlier_measuresOutput
  
    def _gen_output(self, fname ="tka_measures.csv"):
        dname = os.getcwd() + os.sep + fname
        return dname

    def _run_interface(self, runtime):
                
        df = pd.read_csv( self.inputs.in_file  )
        out_columns=['sub','ses','task','roi','metric','measure','value'] 
        df_out = pd.DataFrame(columns=out_columns)
        print df
        for roi, roi_df in df.groupby('roi'):
            for ses, ses_df in roi_df.groupby('ses'):
                for task, task_df in df.groupby('task'):
                    for measure, measure_name in zip(outlier_measures.values(), outlier_measures.keys()):
                        meanValues = task_df.value[task_df['metric'] == 'mean']
                        r=pd.Series(measure(meanValues).flatten())
                        task_df.index=range(task_df.shape[0])
                        task_df['value'] = r                     
                        task_df['measure'] = [measure_name] * task_df.shape[0] 
                        df_out = pd.concat([df_out, task_df], axis=0)
        if not isdefined( self.inputs.out_file ) : 
            self.inputs.out_file = self._gen_output()
        df_out.fillna(0, inplace=True)
        df_out.to_csv(self.inputs.out_file,index=False)

        return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()
        if not isdefined( self.inputs.out_file) :
            self.inputs.out_file = self._gen_output()
        outputs["out_file"] = self.inputs.out_file
        return outputs



