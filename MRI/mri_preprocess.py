import nipype.pipeline.engine as pe
import nipype.interfaces.utility as niu
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath, 
                                    BaseInterface, OutputMultiPath, BaseInterfaceInputSpec, isdefined)
from nipype.interfaces.ants import registration, segmentation


def get_workflow(name, preinfosource, datasink, opts):
    workflow = pe.Workflow(name=name)

    inputnode = pe.Node(niu.IdentityInterface(fields=["t1", "pet2mri", "template"]), name='inputnode')
    outputnode = pe.Node(niu.IdentityInterface(fields=["t1_mni", "t1mni_tfm", "brainmask"]), name='outputnode')

    infosource=pe.Node()
    infosource.iterables = ( 'args', valid_args )
    

    t1_mnc2nii = pe.Node()


    workflow.connect(inputnode, 't1', t1_mnc2nii, 'in_file')

    template_mnc2nii = pe.Node()
    workflow.connect(inputnode, 'template', template_mnc2nii, 'in_file')

    reg = Node(Registration(args='--float',
                    collapse_output_transforms=True,
                    fixed_image=template,
                    initial_moving_transform_com=True,
                    num_threads=1,
                    output_inverse_warped_image=True,
                    output_warped_image=True,
                    sigma_units=['vox']*3,
                    transforms=['Rigid', 'Affine', 'SyN'],
                    terminal_output='file',
                    winsorize_lower_quantile=0.005,
                    winsorize_upper_quantile=0.995,
                    convergence_threshold=[1e-08, 1e-08, -0.01],
                    convergence_window_size=[20, 20, 5],
                    metric=['Mattes', 'Mattes', ['Mattes', 'CC']],
                    metric_weight=[1.0, 1.0, [0.5, 0.5]],
                    number_of_iterations=[[10000, 11110, 11110],
                                          [10000, 11110, 11110],
                                          [100, 30, 20]],
                    radius_or_number_of_bins=[32, 32, [32, 4]],
                    sampling_percentage=[0.3, 0.3, [None, None]],
                    sampling_strategy=['Regular',
                                       'Regular',
                                       [None, None]],
                    shrink_factors=[[3, 2, 1],
                                    [3, 2, 1],
                                    [4, 2, 1]],
                    smoothing_sigmas=[[4.0, 2.0, 1.0],
                                      [4.0, 2.0, 1.0],
                                      [1.0, 0.5, 0.0]],
                    transform_parameters=[(0.1,),
                                          (0.1,),
                                          (0.2, 3.0, 0.0)],
                    use_estimate_learning_rate_once=[True]*3,
                    use_histogram_matching=[False, False, True],
                    write_composite_transform=True),
                    name='antsregfast')

    workflow.connect(t1_mnc2nii, 'out_file', reg, 'fixed_image')
    workflow.connect(template_mnc2nii, 'out_file', reg, 'moving_image')
    
    
    


    return(workflow)
    

