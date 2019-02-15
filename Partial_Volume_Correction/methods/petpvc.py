from pvc_template import *
from nipype.interfaces.base import CommandLine, CommandLineInputSpec
import nibabel as nib
import numpy as np
import shutil

file_format="NIFTI"
separate_labels=True
split_frames=True


class petpvcOutput(TraitedSpec):
    out_file = File(argstr="%s",  desc="Parametric image of binding potential.")

class petpvcInput(MINCCommandInputSpec):
    out_file = File(argstr="-o %s", desc="image to operate on")
    mask_file = File(argstr="-m %s",  desc="Integer mask file")
    in_file = File(argstr="-i %s", exists=True, desc="PET file")
    pvc = traits.Str(argstr="--pvc %s", exists=True, desc="PVC type")
    iterations = traits.Int(argstr="--iter %s", exists=True, desc="Number of iterations")
    k = traits.Int(argstr="-k %d", exists=True, desc="Number of deconvolution iterations")
    x_fwhm = traits.Float( argstr="-x %f", desc="FWHM of PSF x axis") 
    y_fwhm = traits.Float( argstr="-y %f", desc="FWHM of PSF y axis") 
    z_fwhm = traits.Float( argstr="-z %f", desc="FWHM of PSF z axis") 


class petpvcCommand(CommandLine):
    input_spec =  petpvcInput
    output_spec = petpvcOutput
    #_cmd='petpvc --iter 1 -k 1'
    _cmd='petpvc'


class petpvc4DCommand(BaseInterface):
    input_spec =  petpvcInput
    output_spec = petpvcOutput
    #petpvc -i <PET> -m <MASK> -o <OUTPUT> --pvc IY -x 6.0 -y 6.0 -z 6.0 [--debug]

    def _run_interface(self, runtime) :
        
        in_file = self.inputs.in_file
        vol = nib.nifti1.load(in_file)

        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_output(self.inputs.in_file)

        if len(vol.shape) > 3 :
            vol = nib.nifti1.load(in_file) 
            if not os.path.exists("tmp") :
                os.makedirs("tmp/")
            tmax = vol.shape[-1]
            for i in range(tmax)  : 
                temp_vol = vol.dataobj[:, :, :, i ]
                temp_in_file = "tmp/pet_"+str(i)+".nii.gz"
                temp_out_file = "tmp/pvc_"+str(i)+".nii.gz"
                nib.save( nib.nifti1.Nifti1Image(temp_vol, vol.affine), temp_in_file)

                petpvc4dNode = petpvcCommand()
                petpvc4dNode.inputs.z_fwhm  = self.inputs.z_fwhm
                petpvc4dNode.inputs.y_fwhm  = self.inputs.y_fwhm
                petpvc4dNode.inputs.x_fwhm  = self.inputs.x_fwhm
                petpvc4dNode.inputs.iterations  = self.inputs.iterations
                petpvc4dNode.inputs.k = self.inputs.k
                petpvc4dNode.inputs.in_file = temp_in_file
                petpvc4dNode.inputs.out_file= temp_out_file
                petpvc4dNode.inputs.pvc= self._suffix
                print(petpvc4dNode.cmdline)
                    
                petpvc4dNode.run()

            for i in range(tmax) :
                temp_out_file = "tmp/pvc_"+str(i)+".nii.gz"
                temp_vol =  nib.nifti1.load(temp_out_file)
                if i == 0 :
                    ar = np.zeros(list(temp_vol.shape) + [vol.shape[-1]] )
                ar[:, :, :, i ] = np.array(temp_vol.dataobj)
                affine = temp_vol.affine
            out_vol = nib.nifti1.Nifti1Image(ar, affine)
            nib.save( out_vol, self.inputs.out_file)
            shutil.rmtree("tmp/") 
        else :
            petpvc4dNode = petpvc()
            petpvc4dNode.inputs.z_fwhm  = self.inputs.z_fwhm
            petpvc4dNode.inputs.y_fwhm  = self.inputs.y_fwhm
            petpvc4dNode.inputs.x_fwhm  = self.inputs.x_fwhm
            petpvc4dNode.inputs.x_fwhm  = self.inputs.x_fwhm
            petpvc4dNode.inputs.iterations  = self.inputs.iterations
            petpvc4dNode.inputs.in_file = self.inputs.in_file
            petpvc4dNode.inputs.out_file= self.inputs.out_file
            petpvc4dNode.inputs.pvc= self._suffix
            print(petpvcNode.cmdline)
            petpvc4dNode.run()
        return runtime

    def _list_outputs(self):
        print("_list_outputs")
        outputs = self.output_spec().get()
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_output(self.inputs.in_file)
        outputs["out_file"] = self.inputs.out_file
        return outputs

    def _gen_filename(self, name):
        if name == "out_file":
            return self._list_outputs()["out_file"]
        return None

    def _gen_output(self, basefile):
        print("_gen_output")
        fname = ntpath.basename(basefile)
        fname_list = os.path.splitext(fname) # [0]= base filename; [1] =extension
        dname = os.getcwd() 
        suffix=self._suffix
        if suffix[0] != '_' :
            suffix = '_' + suffix
        
        out_fn = dname+ os.sep+fname_list[0] + suffix + fname_list[1]
        if '.gz' not in fname_list[1] :
            out_fn += '.gz'

        return out_fn
    def _parse_inputs(self, skip=None):
        print("_parse_inputs")
        if skip is None:
            skip = []
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_output(self.inputs.in_file, self._suffix)
        return super(pvcCommand, self)._parse_inputs(skip=skip)


