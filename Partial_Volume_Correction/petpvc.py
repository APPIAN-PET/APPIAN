from pvc_template import *
import nibabel as nib
file_format="NIFTI"
separate_labels=True
split_frames=True

class petpvcOutput(TraitedSpec):
    out_file = File(argstr="%s",  desc="Parametric image of binding potential.")

class petpvcInput(MINCCommandInputSpec):
    out_file = File(argstr="-o %s", desc="image to operate on")
    mask_file = File(argstr="-m %s",  desc="Integer mask file")
    in_file = File(argstr="-i %s", exists=True, position=1,desc="PET file")
    pvc = File(argstr="--pvc %s", exists=True, position=1,desc="PVC type")
    x_fwhm = traits.Float( argstr="-x %f", desc="FWHM of PSF x axis") 
    y_fwhm = traits.Float( argstr="-y %f", desc="FWHM of PSF y axis") 
    z_fwhm = traits.Float( argstr="-z %f", desc="FWHM of PSF z axis") 


class petpvcCommand(CommandLine):
    input_spec =  petpvcInput
    output_spec = petpvcOutput
    _cmd='petpvc'


class petpvc4DCommand(CommandLine):
    input_spec =  pvcInput
    output_spec = pvcOutput
    _cmd='petpvc'
    _suffix='VC'
    #petpvc -i <PET> -m <MASK> -o <OUTPUT> --pvc IY -x 6.0 -y 6.0 -z 6.0 [--debug]

    def _run_interface(self, runtime) :
        
        in_file = self.inputs.in_file
        vol = nib.nifti1.load(in_file)
        if len(vol.shape) > 3 :
            vol = nib.nifti1.Nifti1Image(in_file) 
            for i in range(vol.shape[-1])  : 
                temp_vol = vol.dataobj[:, :, :, i ]
                temp_in_file = "tmp/pet_"+str(i)+".nii.gz"
                temp_out_file = "tmp/pvc_"+str(i)+".nii.gz"
                nib.save(temp_vol, temp_in_file)

                petpvc4dNode = petpvc()
                petpvc4dNode.inputs.z_fwhm  = self.inputs.z_fwhm
                petpvc4dNode.inputs.y_fwhm  = self.inputs.y_fwhm
                petpvc4dNode.inputs.x_fwhm  = self.inputs.x_fwhm
                petpvc4dNode.inputs.in_file = temp_in_file
                petpvc4dNode.inputs.out_file= temp_out_file
                petpvc4dNode.inputs.pvc= self.inputs._suffix
                print(petpvcNode.cmdline)
                petpvc4dNode.run()

            for i in range(vol.shape[-1]) :
                temp_out_file = "tmp/pvc_"+str(i)+".nii.gz"
                temp_vol =  nib.nifti1.load(temp_out_file)
                if i == 0 :
                    ar = np.array(list(temp_vol) + [vol.shape[-1]] )
                ar[:, :, :, i ] = np.array(temp_vol.dataobj)
                affine = temp_vol.affine

            nib.save( nib.nifti1.Nifti1Image(ar, affine), self.inputs.out_file)
        else :
            petpvc4dNode = petpvc()
            petpvc4dNode.inputs.z_fwhm  = self.inputs.z_fwhm
            petpvc4dNode.inputs.y_fwhm  = self.inputs.y_fwhm
            petpvc4dNode.inputs.x_fwhm  = self.inputs.x_fwhm
            petpvc4dNode.inputs.in_file = self.inputs.in_file
            petpvc4dNode.inputs.out_file= self.inputs.out_file
            petpvc4dNode.inputs.pvc= self.inputs._suffix
            print(petpvcNode.cmdline)
            petpvc4dNode.run()

        return runtime

    def _list_outputs(self):
        print("_list_outputs")
        outputs = self.output_spec().get()
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_output(self.inputs.in_file, self._suffix)
        outputs["out_file"] = self.inputs.out_file
        return outputs

    def _gen_filename(self, name):
        if name == "out_file":
            return self._list_outputs()["out_file"]
        return None

    def _gen_output(self, basefile, _suffix):
        print("_gen_output")
        fname = ntpath.basename(basefile)
        fname_list = os.path.splitext(fname) # [0]= base filename; [1] =extension
        dname = os.getcwd() 
        return dname+ os.sep+fname_list[0] + _suffix + fname_list[1]

    def _parse_inputs(self, skip=None):
        print("_parse_inputs")
        if skip is None:
            skip = []
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_output(self.inputs.in_file, self._suffix)
        return super(pvcCommand, self)._parse_inputs(skip=skip)


