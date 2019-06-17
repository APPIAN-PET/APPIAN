from Extra.base import MINCCommand, MINCCommandInputSpec
from nipype.interfaces.base import (TraitedSpec, File, traits, BaseInterface,  BaseInterfaceInputSpec, isdefined, CommandLineInputSpec, CommandLine)
from Extra.utils import splitext, check_gz, cmd
import ntpath
import os
class quantificationCommand(CommandLine):

    def _list_outputs(self):
        outputs = self.output_spec().get()
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_output(self.inputs.in_file, self._suffix)
        outputs["out_file"] = self.inputs.out_file
        return outputs

    def _gen_output(self, basefile, _suffix):
        fname = ntpath.basename(basefile)
        fname_list = splitext(fname) # [0]= base filename; [1] =extension
        dname = os.getcwd() 
        return dname+ os.sep+fname_list[0] + _suffix + fname_list[1]

    def _parse_inputs(self, skip=None):
        if skip is None:
            skip = []
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_output(self.inputs.in_file, self._suffix)

        return super(quantificationCommand, self)._parse_inputs(skip=skip)


class QuantificationCommandWrapper(BaseInterface):
    _quantCommand=None

    def _run_interface(self, runtime) :

        quantNode = self._quantCommand()
        quantNode.inputs = self.inputs
        init_command = quantNode.cmdline
        modified_command=[]
        self.inputs.out_file = quantNode.inputs.out_file
        for f in init_command.split(' ') :
            if os.path.exists(f)  :
                f = check_gz(f)
            elif f == quantNode.inputs.out_file and splitext(f)[1] == '.nii.gz' :
                f =  splitext(f)[0] + '.nii'
                self.inputs.out_file = f
            modified_command.append(f)

       

        print(modified_command)
        command=' '.join(modified_command)
        print command 
        cmd( command)




        print "Out file", self.inputs.out_file
        return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file
        return outputs


