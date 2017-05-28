from nipype.interfaces.base import (
    TraitedSpec,
    CommandLineInputSpec,
    CommandLine,
    File
)
import os

class GZipInputSpec(CommandLineInputSpec):
    input_file = File(desc="File", exists=True, mandatory=True, argstr="%s")

class GZipOutputSpec(TraitedSpec):
    output_file = File(desc = "Zip file", exists = True)

class GZipTask(CommandLine):
    input_spec = GZipInputSpec
    output_spec = GZipOutputSpec
    cmd = 'gzip'
    
    def _list_outputs(self):
            outputs = self.output_spec().get()
            outputs['output_file'] = os.path.abspath(self.inputs.input_file + ".gz")
            return outputs

if __name__ == '__main__':

    zipper = GZipTask(input_file='an_existing_file')
    print zipper.cmdline
    zipper.run()