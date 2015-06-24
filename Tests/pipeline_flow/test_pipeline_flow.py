import nipype.interfaces.minc as minc         # the spm interfaces
import nipype.pipeline.engine as pe         # the workflow and node wrappers
import nipype.interfaces.io as nio
import nipype.interfaces.utility as util
from nipype.interfaces.utility import Rename
import os

wkdir="/data1/projects/nipype/tf/tka_nipype/Tests/pipeline_flow/"  #"/home/tfunck/.local/lib/python2.7/site-packages/nipype/interfaces/minc/tests/"


###Define variables###
subjects = ['C01','C02','C03']
study_prefix="test"
output_dir="output"


###Datasink###
datasink=pe.Node(interface=nio.DataSink(), name=output_dir)
datasink.inputs.base_directory= wkdir + datasink.name

###Infosource###
infosource = pe.Node(interface=util.IdentityInterface(fields=['study_prefix', 'subject_id']), name="infosource")
infosource.inputs.study_prefix = study_prefix
infosource.iterables = ('subject_id', subjects)

###Datasource###
datasource = pe.Node( interface=nio.DataGrabber(infields=['study_prefix', 'subject_id'], outfields=['pet', 'mri'], sort_filelist=False), name="datasource")
datasource.inputs.base_directory = wkdir + 'data/' 
datasource.inputs.template = '*'
datasource.inputs.field_template = dict(pet='PET/test_%s_pet.mnc', mri='CIVET/test_%s_mri.mnc')
datasource.inputs.template_args = dict(pet=[['subject_id']], mri=[['subject_id']])


###Define Node 1
node1 = pe.Node(interface=minc.ConstantMathsCommand(), name="node1")
node1.inputs.operation="mult"
node1.inputs.opt_constant="-const"
node1.inputs.operand_value=2
node1.inputs.out_file="brain_mask_2.mnc"
#node1.outputs.out_file=node1.inputs.out_file

###Rename Node 1
rnode1=pe.Node(interface=Rename(format_string="%(study_prefix)s_%(subject_id)s_node1.mnc"), name="node1_")

###Define Node 2
node2 = pe.Node(interface=minc.ConstantMathsCommand(), name="node2")
node2.inputs.operation="add"
node2.inputs.opt_constant="-const"
node2.inputs.operand_value=1
node2.inputs.out_file="brain_mask_3.mnc"

###Rename Node 2
rnode2=pe.Node(interface=Rename(format_string="%(study_prefix)s_%(subject_id)s_node2.mnc"), name="node2_")

###Define Node 3
node3 = pe.Node(interface=minc.ConstantMathsCommand(), name="node3")
node3.inputs.operation="add"
node3.inputs.opt_constant="-const"
node3.inputs.operand_value=1
node3.inputs.out_file="brain_mask_4.mnc"


###Rename Node 3
rnode3=pe.Node(interface=Rename(format_string="%(study_prefix)s_%(subject_id)s_node3.mnc"), name="node3_")


###Define workflow
workflow = pe.Workflow(name='preproc')
workflow.base_dir=wkdir



###Connect nodes together


workflow.connect([(infosource, datasource, [('subject_id', 'subject_id')]),
                  (infosource, datasource, [('study_prefix', 'study_prefix')])
                ])

#Connections for node1
workflow.connect(datasource, 'pet', node1, 'input_file')
workflow.connect(node1, 'out_file', rnode1, 'in_file')
workflow.connect([(infosource, rnode1, [('subject_id', 'subject_id')]),
                  (infosource, rnode1, [('study_prefix', 'study_prefix')])
                ])

workflow.connect(rnode1, 'out_file', datasink, 'node1')

#Connections for node2
workflow.connect(node1, 'out_file', node2, 'input_file')
workflow.connect(node1, 'out_file', rnode2, 'in_file')
workflow.connect([(infosource, rnode2, [('subject_id', 'subject_id')]),
                  (infosource, rnode2, [('study_prefix', 'study_prefix')])
                ])

workflow.connect(rnode2, 'out_file', datasink, 'node2')

#Connections for node3
workflow.connect(node2, 'out_file', node3, 'input_file')
workflow.connect(node2, 'out_file', rnode3, 'in_file')
workflow.connect([(infosource, rnode3, [('subject_id', 'subject_id')]),
                  (infosource, rnode3, [('study_prefix', 'study_prefix')])
                ])

workflow.connect(rnode3, 'out_file', datasink, 'node3')
#workflow.write_graph()

#run the work flow
workflow.run()
