from Extra.base import MINCCommand, MINCCommandInputSpec
from nipype.interfaces.base import TraitedSpec, File, traits

in_file_format="MINC"
out_file_format="MINC"
reference=True
voxelwise=True


class quantOutput(TraitedSpec):
    out_file = File(argstr="%s", position=-1, desc="Output SUV image.")

class quantInput(MINCCommandInputSpec):
    
    pet_file = File(exists=True,mandatory=True, desc="PET file")
    reference = File(exists=True,mandatory=True,desc="Mask file")
    header = traits.Dict(desc="Input file ")

    out_file = File(desc="Output SUV image")

class quantCommand(quantificationCommand):
    input_spec =  quantInput
    output_spec = quantOutput

    _suffix = "_suvr" 
    def _run_interface(self, runtime):
        if not isdefined(self.inputs.out_file) : self.inputs.out_file = self._gen_output(self.inputs.pet_file, self._suffix)
        print self.inputs.pet_file
        print self.inputs.reference
        header = self.inputs.header
        pet = volumeFromFile(self.inputs.pet_file)
        reference = volumeFromFile(self.inputs.reference)
        out = volumeLikeFile(self.inputs.reference, self.inputs.out_file )
        ndim = len(pet.data.shape)
        
        vol = pet.data
        if ndim > 3 :
            try : 
                float(header['time']['frames-time'][0]) 
                time_frames = [ float(h) for h in  header['time']["frames-time"] ]
            except ValueError :
                time_frames = [1.]
            
            vol = simps( pet.data, time_frames, axis=4)
        
        idx = reference.data > 0
        ref = np.mean(vol[idx])
        print "SUVR Reference = ", ref
        vol = vol / ref
        out.data=vol
        out.writeFile()
        out.closeVolume()


        return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file
        return outputs

    def _gen_filename(self, name):
        if name == "out_file":
            return self._list_outputs()["out_file"]
        return None

    def _gen_output(self, basefile, _suffix):
        fname = ntpath.basename(basefile)
        fname_list = os.path.splitext(fname) # [0]= base filename; [1] =extension
        dname = os.getcwd() 
        return dname+ os.sep+fname_list[0] + _suffix + fname_list[1]

    def _parse_inputs(self, skip=None):
        if skip is None:
            skip = []
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_output(self.inputs.in_file, self._suffix)
        return super(suvCommand, self)._parse_inputs(skip=skip)
