class calc_distance_metricsOutput(TraitedSpec):
    out_file = traits.File(desc="Output file")

class calc_distance_metricsInput(BaseInterfaceInputSpec):
    pet = traits.File(exists=True, mandatory=True, desc="Input PET image")
    t1 = traits.File(exists=True, mandatory=True, desc="Input T1 MRI")
    t1_brain_mask = traits.File(exists=True, mandatory=True, desc="Input T1 MRI")
    pet_brain_mask = traits.File(exists=True, mandatory=True, desc="Input T1 MRI")
    sid = traits.Str(desc="Subject")
    ses = traits.Str(desc="Session")
    task = traits.Str(desc="Task")
    study_prefix = traits.Str(desc="Study Prefix")
    out_file = traits.File(desc="Output file")
    clobber = traits.Bool(desc="Overwrite output file", default=False)

class calc_distance_metricsCommand(BaseInterface):
    input_spec = calc_distance_metricsInput 
    output_spec = calc_distance_metricsOutput
  
    def _gen_output(self, sid, ses, task, fname ="distance_metric.csv"):
        dname = os.getcwd() 
        return dname + os.sep +'sub-'+ sid + '_ses-' + ses + '_task-' + task + '_' + fname

    def _run_interface(self, runtime):
        colnames=["Subject", "Session","Task", "Metric", "Value"] 
        sub_df=pd.DataFrame(columns=colnames)
        pet = self.inputs.pet
        t1 = self.inputs.t1
        sid = self.inputs.sid
        ses = self.inputs.ses
        task = self.inputs.task
        t1_brain_mask = self.inputs.t1_brain_mask
        pet_brain_mask = self.inputs.pet_brain_mask

        path, ext = os.path.splitext(pet)
        base=basename(path)
        param=base.split('_')[-1]
        param_type=base.split('_')[-2]

        mis_metric=distance(pet, t1, t1_brain_mask, pet_brain_mask, distance_metrics.values())

        df=pd.DataFrame(columns=colnames)
        for m,metric_name,metric_func in zip(mis_metric, distance_metrics.keys(), distance_metrics.values()):
            temp=pd.DataFrame([[sid,ses,task,metric_name,m]],columns=df.columns  ) 
            sub_df = pd.concat([sub_df, temp])
        
        if not isdefined( self.inputs.out_file) :
            self.inputs.out_file = self._gen_output(self.inputs.sid, self.inputs.ses, self.inputs.task)
        
        sub_df.to_csv(self.inputs.out_file,  index=False)
        return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()
        if not isdefined( self.inputs.out_file) :
            self.inputs.out_file = self._gen_output( self.inputs.sid, self.inputs.cid,)

        outputs["out_file"] = self.inputs.out_file
        return outputs


class calc_outlier_measuresOutput(TraitedSpec):
    out_file = traits.File(desc="Output file")

class calc_outlier_measuresInput(BaseInterfaceInputSpec):
    in_file = traits.File(desc="Input file")
    out_file = traits.File(desc="Output file")
    clobber = traits.Bool(desc="Overwrite output file", default=False)

class calc_outlier_measuresCommand(BaseInterface):
    input_spec = calc_outlier_measuresInput 
    output_spec = calc_outlier_measuresOutput
  
    def _gen_output(self, fname ="coreg_measures.csv"):
        dname = os.getcwd() + os.sep + fname
        return dname

    def _run_interface(self, runtime):
		df = pd.read_csv( self.inputs.in_file  )
		#out_columns=['Subject','Session','Task', 'Measure','Metric', 'Value']
		out_columns=['sub','ses','task','roi','metric','measure','value'] 
		df_out = pd.DataFrame(columns=out_columns)
		for ses, ses_df in df.groupby(['ses']):
			for task, task_df in ses_df.groupby(['task']):
				for measure, measure_name in zip(outlier_measures.values(), outlier_measures.keys()):
					for metric_name, metric_df in task_df.groupby(['metric']):
						r=pd.Series(measure(task_df.Value.values).flatten())
						task_df.index=range(task_df.shape[0])
						task_df['value'] = r
						task_df['measure'] = [measure_name] * task_df.shape[0]
						df_out = pd.concat([df_out, task_df], axis=0)
		df_out.fillna(0, inplace=True)
		if not isdefined( self.inputs.out_file) :
			self.inputs.out_file = self._gen_output()
		df_out.to_csv(self.inputs.out_file,index=False)
		return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()
        if not isdefined( self.inputs.out_file) :
            self.inputs.out_file = self._gen_output()
        outputs["out_file"] = self.inputs.out_file
        return outputs
