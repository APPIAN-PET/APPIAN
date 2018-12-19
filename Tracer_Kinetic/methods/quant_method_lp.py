from quantification_template import *

in_file_format="ECAT"
out_file_format="ECAT"
reference=True
voxelwise=True


class quantOutput(TraitedSpec):
    out_file = File(argstr="%s",  desc="Parametric image")

class quantInput( CommandLineInputSpec):
    out_file = File(argstr="%s",  position=-1, desc="image to operate on")
    in_file= File(exists=True, mandatory=True, position=-3, argstr="%s", desc="PET file")
    reference = File(exists=True, mandatory=True,  position=-4, argstr="%s", desc="Reference file")
    start_time=traits.Float(argstr="%s", mandatory=True, position=-2, desc="Start time for regression in mtga.")
    k2=  traits.Float(argstr="-k2=%f", desc="With reference region input it may be necessary to specify also the population average for regerence region k2")
    thr=traits.Float(argstr="-thr=%f", desc="Pixels with AUC less than (threshold/100 x max AUC) are set to zero. Default is 0%")
    Max=traits.Float(argstr="-max=%f",default=10000, use_default=True, desc="Upper limit for Vt or DVR values; by default max is set pixel-wise to 10 times the AUC ratio.")
    Min=traits.Float(argstr="-min=%f", desc="Lower limit for Vt or DVR values, 0 by default")
    Filter=traits.Bool(argstr="-filter",  desc="Remove parametric pixel values that over 4x higher than their closest neighbours.")
    end=traits.Float(argstr="-end %f", desc="By default line is fit to the end of data. Use this option to enter the fit end time.")
    v=traits.Str(argstr="-v %s", desc="Y-axis intercepts time -1 are written as an image to specified file.")
    n=traits.Str(argstr="-n %s", desc="Numbers of selected plot data points are written as an image.")
    
class quantCommand(BaseInterface):
    input_spec = quantInput
    output_spec = quantOutput
    _suffix = "_suv" 
    def _run_interface(self, runtime):
        if not isdefined(self.inputs.out_file) : self.inputs.out_file = self._gen_output(self.inputs.in_file, self._suffix)
        header = self.inputs.header
        pet = volumeFromFile(self.inputs.in_file)
        reference = volumeFromFile(self.inputs.reference)
        out = volumeLikeFile(self.inputs.reference, self.inputs.out_file )
        ndim = len(pet.data.shape)
        
        vol = pet.data
        if ndim > 3 :

            dims = pet.getDimensionNames()
            idx = dims.index('time')
            try : 
                time_frames = [ float(s) for s,e in  header['Time']["FrameTimes"]["Values"] ]
            except ValueError :
                time_frames = [1.]
            vol = simps( pet.data, time_frames, axis=idx)
        
        idx = reference.data > 0
        ref = np.mean(vol[idx])
        print "SUVR Reference = ", ref
        vol = vol / ref
        out.data=vol
        out.writeFile()
        out.closeVolume()



def check_options(tkaNode, opts):
    #Define node for logan plot analysis 
    if opts.tka_k2 != None: tkaNode.inputs.k2=opts.tka_k2
    if opts.tka_thr != None: tkaNode.inputs.thr=opts.tka_thr
    if opts.tka_max != None: tkaNode.inputs.Max=opts.tka_max
    if opts.tka_filter != None: tkaNode.inputs.Filter=opts.tka_filter
    if opts.tka_end != None: tkaNode.inputs.end=opts.tka_end
    if opts.tka_v != None: tkaNode.inputs.v=opts.tka_v
    if opts.tka_start_time != None: tkaNode.inputs.start_time=opts.tka_start_time

    return tkaNode


