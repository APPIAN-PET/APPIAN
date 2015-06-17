import nipype.interfaces.minc as minc         # the spm interfaces
import nipype.pipeline.engine as pe         # the workflow and node wrappers

wkdir="/home/tfunck/.local/lib/python2.7/site-packages/nipype/interfaces/minc/tests/"
###Define Node 1
node1 = pe.Node(interface=minc.ConstantMathsCommand(), name="node1")
node1.inputs.input_file=wkdir+"data/brain_mask.mnc"
node1.inputs.operation="mult"
node1.inputs.opt_constant="-const"
node1.inputs.operand_value=2
node1.inputs.out_file=wkdir+"output/brain_mask_2.mnc"
#node1.outputs.out_file=node1.inputs.out_file

###Define Node 2
node2 = pe.Node(interface=minc.ConstantMathsCommand(), name="node2")
#node2.inputs.input_file=wkdir+"data/brain_mask_2.mnc"
node2.inputs.operation="add"
node2.inputs.opt_constant="-const"
node2.inputs.operand_value=1
node2.inputs.out_file=wkdir+"output/brain_mask_3.mnc"


###Define workflow
workflow = pe.Workflow(name='preproc')
workflow.base_dir=wkdir

###Add nodes to workflow
#workflow.add_nodes([node1])
#workflow.add_nodes([node1, node2])



###Connect nodes together
workflow.connect(node1,'out_file' , node2, 'input_file')

#workflow.write_graph()

#run the work flow
workflow.run()
