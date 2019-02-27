import nipype.interfaces.io as nio
import nipype.pipeline.engine as pe
import nipype.interfaces.utility as niu
import nipype.algorithms.misc as misc
from nipype.interfaces.utility import Function
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath, 
		BaseInterface, OutputMultiPath, BaseInterfaceInputSpec, isdefined)
from nipype.interfaces.base import CommandLine, CommandLineInputSpec
from nipype.interfaces.ants.base import ANTSCommandInputSpec
from nipype.interfaces.ants.segmentation import Atropos
from nipype.interfaces.ants import Registration, ApplyTransforms
from Extra.conversion import mnc2nii_shCommand, nii2mnc_shCommand, nii2mnc2Command, mnc2niiCommand
import scipy.io
import os
from nipype.interfaces.minc import Math


class mincRegistration(Registration):
    _cmd = 'antsRegistration --minc'


class mincAtroposInputSpec(ANTSCommandInputSpec):
    dimension = traits.Enum(3, 2, 4, argstr='--image-dimensionality %d',
                            usedefault=True,
                            desc='image dimension (2, 3, or 4)')
    intensity_images = InputMultiPath(File(exists=True),
                                      argstr="--intensity-image %s...",
                                      mandatory=True)
    mask_image = File(exists=True, argstr='--mask-image %s', mandatory=True)
    initialization = traits.Enum('Random', 'Otsu', 'KMeans',
                                 'PriorProbabilityImages', 'PriorLabelImage',
                                 argstr="%s",
                                 requires=['number_of_tissue_classes'],
                                 mandatory=True)
    prior_probability_images = InputMultiPath(File(exists=True))
    number_of_tissue_classes = traits.Int(mandatory=True)
    prior_weighting = traits.Float()
    prior_probability_threshold = traits.Float(requires=['prior_weighting'])
    likelihood_model = traits.Str(argstr="--likelihood-model %s")
    mrf_smoothing_factor = traits.Float(argstr="%s")
    mrf_radius = traits.List(traits.Int(), requires=['mrf_smoothing_factor'])
    icm_use_synchronous_update = traits.Bool(argstr="%s")
    maximum_number_of_icm_terations = traits.Int(
        requires=['icm_use_synchronous_update'])
    n_iterations = traits.Int(argstr="%s")
    convergence_threshold = traits.Float(requires=['n_iterations'])
    posterior_formulation = traits.Str(argstr="%s")
    use_random_seed = traits.Bool(True, argstr='--use-random-seed %d', desc='use random seed value over constant',
                                  usedefault=True)
    use_mixture_model_proportions = traits.Bool(
        requires=['posterior_formulation'])
    out_classified_image_name = File(argstr="%s", genfile=True,
                                     hash_files=False)
    save_posteriors = traits.Bool()
    output_posteriors_name_template = traits.Str('POSTERIOR_%02d.nii.gz',
                                                 usedefault=True)
    classified_image = File()

class mincAtroposOutputSpec(TraitedSpec):
    classified_image = File(exists=True)
    posteriors = OutputMultiPath(File(exist=True))

class mincAtroposCommand(BaseInterface):
    input_spec =  mincAtroposInputSpec
    output_spec = mincAtroposOutputSpec
        
    def _run_interface(self, runtime):
        inputnode = niu.IdentityInterface(fields=['intensity_image', 'mask_image'])
        inputnode.iterables = ('intensity_image', self.inputs.intensity_images)

        intensity_nii_list = []
        for f in self.inputs.intensity_images :
            mult = Math()
            mult.inputs.input_files=[f, self.inputs.mask_image]
            mult.inputs.output_file=os.getcwd() + os.sep+ os.path.basename(os.path.splitext(f)[0])+"_brain.mnc"
            mult.inputs.calc_mul=True
            mult.run()

            intensity_mnc2nii_sh = mnc2nii_shCommand() 
            intensity_mnc2nii_sh.inputs.in_file = mult.inputs.output_file
            intensity_mnc2nii_sh.run()
            intensity_nii_list += [intensity_mnc2nii_sh.inputs.out_file ]

	    mask_mnc2nii_sh = mnc2nii_shCommand() 
	    mask_mnc2nii_sh.inputs.truncate_path = True
	    mask_mnc2nii_sh.inputs.in_file = self.inputs.mask_image
	    mask_mnc2nii_sh.run()

        seg = Atropos()  
        seg.inputs.dimension = self.inputs.dimension 
        seg.inputs.intensity_images =  intensity_nii_list
        seg.inputs.mask_image = mask_mnc2nii_sh.inputs.out_file 
        seg.inputs.initialization = self.inputs.initialization 
        seg.inputs.prior_probability_images = self.inputs.prior_probability_images 
        seg.inputs.number_of_tissue_classes = self.inputs.number_of_tissue_classes
        seg.inputs.prior_weighting = self.inputs.prior_weighting 
        seg.inputs.prior_probability_threshold = self.inputs.prior_probability_threshold
        seg.inputs.likelihood_model = self.inputs.likelihood_model 
        seg.inputs.mrf_smoothing_factor = self.inputs.mrf_smoothing_factor
        seg.inputs.mrf_radius = self.inputs.mrf_radius 
        seg.inputs.icm_use_synchronous_update = self.inputs.icm_use_synchronous_update 
        seg.inputs.maximum_number_of_icm_terations = self.inputs.maximum_number_of_icm_terations 
        seg.inputs.convergence_threshold = self.inputs.convergence_threshold 
        seg.inputs.posterior_formulation = self.inputs.posterior_formulation 
        seg.inputs.use_random_seed = self.inputs.use_random_seed 
        seg.inputs.use_mixture_model_proportions = self.inputs.use_mixture_model_proportions
        seg.inputs.out_classified_image_name = self.inputs.out_classified_image_name 
        seg.inputs.save_posteriors = self.inputs.save_posteriors 
        seg.inputs.output_posteriors_name_template = self.inputs.output_posteriors_name_template 
        print(seg.cmdline)
        seg.run()

        seg.outputs=seg._list_outputs() #seg._outputs()
        classified_nii2mnc_sh = nii2mnc2Command() 
        classified_nii2mnc_sh.inputs.in_file = seg.outputs["classified_image"]
        classified_nii2mnc_sh.inputs.truncate_path=True
        classified_nii2mnc_sh.run()

        self.inputs.classified_image = classified_nii2mnc_sh.inputs.out_file 
        return(runtime)


    def _list_outputs(self):
            if not isdefined(self.inputs.classified_image):
                    self.inputs.classified_image = reg.inputs.classified_image
            outputs = self.output_spec().get()
            outputs["classified_image"] = self.inputs.classified_image
            return outputs



def _parse_inputs(self, skip=None):
	if skip is None:
		skip = []
		if not isdefined(self.inputs.out_file):
			self.inputs.out_file = self._gen_output(self.inputs.in_file)
		return super(mincconvertCommand, self)._parse_inputs(skip=skip)

class mincANTSOutput(TraitedSpec):
	forward_transforms = traits.List(
			File(exists=True),
			desc='List of output transforms for forward registration')
	reverse_transforms = traits.List(
			File(exists=True),
			desc='List of output transforms for reverse registration')
	forward_invert_flags = traits.List(
			traits.Bool(),
			desc='List of flags corresponding to the forward transforms')
	reverse_invert_flags = traits.List(
			traits.Bool(),
			desc='List of flags corresponding to the reverse transforms')
	composite_transform = File(exists=True, desc='Composite transform file')
	inverse_composite_transform = File(desc='Inverse composite transform file')
	warped_image = File(desc="Outputs warped image")
	inverse_warped_image = File(desc="Outputs the inverse of the warped image")
	save_state = File(desc="The saved registration state to be restored")
	metric_value = traits.Float(desc='the final value of metric')
	elapsed_time = traits.Float(desc='the total elapsed time as reported by ANTs')

class mincANTSInput(ANTSCommandInputSpec):
	dimension = traits.Enum(
			3,
			2,
			argstr='--dimensionality %d',
			usedefault=True,
			desc='image dimension (2 or 3)')
	fixed_image = InputMultiPath(
			File(exists=True),
			mandatory=True,
			desc='Image to which the moving_image should be transformed'
			'(usually a structural image)')
	fixed_image_mask = File(
			exists=True,
			argstr='%s',
			max_ver='2.1.0',
			xor=['fixed_image_masks'],
			desc='Mask used to limit metric sampling region of the fixed image'
			'in all stages')
	fixed_image_masks = InputMultiPath(
			traits.Either('NULL', File(exists=True)),
			min_ver='2.2.0',
			xor=['fixed_image_mask'],
			desc=
			'Masks used to limit metric sampling region of the fixed image, defined per registration stage'
			'(Use "NULL" to omit a mask at a given stage)')
	moving_image = InputMultiPath(
			File(exists=True),
			mandatory=True,
			desc=
			'Image that will be registered to the space of fixed_image. This is the'
			'image on which the transformations will be applied to')
	moving_image_mask = File(
			exists=True,
			requires=['fixed_image_mask'],
			max_ver='2.1.0',
			xor=['moving_image_masks'],
			desc='mask used to limit metric sampling region of the moving image'
			'in all stages')
	moving_image_masks = InputMultiPath(
			traits.Either('NULL', File(exists=True)),
			min_ver='2.2.0',
			xor=['moving_image_mask'],
			desc=
			'Masks used to limit metric sampling region of the moving image, defined per registration stage'
			'(Use "NULL" to omit a mask at a given stage)')

	save_state = File(
			argstr='--save-state %s',
			exists=False,
			desc=
			'Filename for saving the internal restorable state of the registration'
			)
	restore_state = File(
			argstr='--restore-state %s',
			exists=True,
			desc=
			'Filename for restoring the internal restorable state of the registration'
			)

	initial_moving_transform = InputMultiPath(
			File(exists=True),
			argstr='%s',
			desc='A transform or a list of transforms that should be applied'
			'before the registration begins. Note that, when a list is given,'
			'the transformations are applied in reverse order.',
			xor=['initial_moving_transform_com'])
	invert_initial_moving_transform = InputMultiPath(
			traits.Bool(),
			requires=["initial_moving_transform"],
			desc='One boolean or a list of booleans that indicate'
			'whether the inverse(s) of the transform(s) defined'
			'in initial_moving_transform should be used.',
			xor=['initial_moving_transform_com'])

	initial_moving_transform_com = traits.Enum(
			0,
			1,
			2,
			argstr='%s',
			xor=['initial_moving_transform'],
			desc="Align the moving_image nad fixed_image befor registration using"
			"the geometric center of the images (=0), the image intensities (=1),"
			"or the origin of the images (=2)")
	metric_item_trait = traits.Enum("CC", "MeanSquares", "Demons", "GC", "MI",
			"Mattes")
	metric_stage_trait = traits.Either(metric_item_trait,
			traits.List(metric_item_trait))
	metric = traits.List(
			metric_stage_trait,
			mandatory=True,
			desc='the metric(s) to use for each stage. '
			'Note that multiple metrics per stage are not supported '
			'in ANTS 1.9.1 and earlier.')
	metric_weight_item_trait = traits.Float(1.0, usedefault=True)
	metric_weight_stage_trait = traits.Either(
			metric_weight_item_trait, traits.List(metric_weight_item_trait))
	metric_weight = traits.List(
			metric_weight_stage_trait,
			value=[1.0],
			usedefault=True,
			requires=['metric'],
			mandatory=True,
			desc='the metric weight(s) for each stage. '
			'The weights must sum to 1 per stage.')
	radius_bins_item_trait = traits.Int(5, usedefault=True)
	radius_bins_stage_trait = traits.Either(
			radius_bins_item_trait, traits.List(radius_bins_item_trait))
	radius_or_number_of_bins = traits.List(
			radius_bins_stage_trait,
			value=[5],
			usedefault=True,
			requires=['metric_weight'],
			desc='the number of bins in each stage for the MI and Mattes metric, '
			'the radius for other metrics')
	sampling_strategy_item_trait = traits.Enum("None", "Regular", "Random",
			None)
	sampling_strategy_stage_trait = traits.Either(
			sampling_strategy_item_trait,
			traits.List(sampling_strategy_item_trait))
	sampling_strategy = traits.List(
			trait=sampling_strategy_stage_trait,
			requires=['metric_weight'],
			desc='the metric sampling strategy (strategies) for each stage')
	sampling_percentage_item_trait = traits.Either(
			traits.Range(low=0.0, high=1.0), None)
	sampling_percentage_stage_trait = traits.Either(
			sampling_percentage_item_trait,
			traits.List(sampling_percentage_item_trait))
	sampling_percentage = traits.List(
			trait=sampling_percentage_stage_trait,
			requires=['sampling_strategy'],
			desc="the metric sampling percentage(s) to use for each stage")
	use_estimate_learning_rate_once = traits.List(traits.Bool(), desc='')
	use_histogram_matching = traits.Either(
			traits.Bool,
			traits.List(traits.Bool(argstr='%s')),
			default=True,
			usedefault=True,
			desc='Histogram match the images before registration.')
	interpolation = traits.Enum(
			'Linear',
			'NearestNeighbor',
			'CosineWindowedSinc',
			'WelchWindowedSinc',
			'HammingWindowedSinc',
			'LanczosWindowedSinc',
			'BSpline',
			'MultiLabel',
			'Gaussian',
			argstr='%s',
			usedefault=True)
	interpolation_parameters = traits.Either(
			traits.Tuple(traits.Int()),  # BSpline (order)
			traits.Tuple(
				traits.Float(),  # Gaussian/MultiLabel (sigma, alpha)
				traits.Float()))

	write_composite_transform = traits.Bool(
					argstr='--write-composite-transform %d',
					default_value=False,
					usedefault=True,
					desc='')
	collapse_output_transforms = traits.Bool(
					argstr='--collapse-output-transforms %d',
					default_value=True,
					usedefault=True,  # This should be true for explicit completeness
					desc=('Collapse output transforms. Specifically, enabling this option '
						'combines all adjacent linear transforms and composes all '
						'adjacent displacement field transforms before writing the '
						'results to disk.'))
	
	
	initialize_transforms_per_stage = traits.Bool(
							argstr='--initialize-transforms-per-stage %d',
							default_value=False,
							usedefault=True,  # This should be true for explicit completeness
							desc=
							('Initialize linear transforms from the previous stage. By enabling this option, '
								'the current linear stage transform is directly intialized from the previous '
								'stages linear transform; this allows multiple linear stages to be run where '
								'each stage directly updates the estimated linear transform from the previous '
								'stage. (e.g. Translation -> Rigid -> Affine). '))
							# NOTE: Even though only 0=False and 1=True are allowed, ants uses integer
	# values instead of booleans
	float = traits.Bool(
			argstr='--float %d',
			default_value=False,
			desc='Use float instead of double for computations.')

	transforms = traits.List(
			traits.Enum('Rigid', 'Affine', 'CompositeAffine', 'Similarity',
				'Translation', 'BSpline', 'GaussianDisplacementField',
				'TimeVaryingVelocityField',
				'TimeVaryingBSplineVelocityField', 'SyN', 'BSplineSyN',
				'Exponential', 'BSplineExponential'),
			argstr='%s',
			mandatory=True)
	# TODO: input checking and allow defaults
	# All parameters must be specified for BSplineDisplacementField, TimeVaryingBSplineVelocityField, BSplineSyN,
	# Exponential, and BSplineExponential. EVEN DEFAULTS!
	transform_parameters = traits.List(
			traits.Either(
				traits.Tuple(traits.Float()),  # Translation, Rigid, Affine,
				# CompositeAffine, Similarity
				traits.Tuple(
					traits.Float(),  # GaussianDisplacementField, SyN
					traits.Float(),
					traits.Float()),
				traits.Tuple(
					traits.Float(),  # BSplineSyn,
					traits.Int(),  # BSplineDisplacementField,
					traits.Int(),  # TimeVaryingBSplineVelocityField
					traits.Int()),
				traits.Tuple(
					traits.Float(),  # TimeVaryingVelocityField
					traits.Int(),
					traits.Float(),
					traits.Float(),
					traits.Float(),
					traits.Float()),
				traits.Tuple(
					traits.Float(),  # Exponential
					traits.Float(),
					traits.Float(),
					traits.Int()),
				traits.Tuple(
					traits.Float(),  # BSplineExponential
					traits.Int(),
					traits.Int(),
					traits.Int(),
					traits.Int()),
				))
	restrict_deformation = traits.List(
					traits.List(traits.Enum(0, 1)),
					desc=("This option allows the user to restrict the optimization of "
						"the displacement field, translation, rigid or affine transform "
						"on a per-component basis. For example, if one wants to limit "
						"the deformation or rotation of 3-D volume to the  first two "
						"dimensions, this is possible by specifying a weight vector of "
						"'1x1x0' for a deformation field or '1x1x0x1x1x0' for a rigid "
						"transformation.  Low-dimensional restriction only works if "
						"there are no preceding transformations."))
					# Convergence flags
	number_of_iterations = traits.List(traits.List(traits.Int()))
	smoothing_sigmas = traits.List(traits.List(traits.Float()), mandatory=True)
	sigma_units = traits.List(
			traits.Enum('mm', 'vox'),
			requires=['smoothing_sigmas'],
			desc="units for smoothing sigmas")
	shrink_factors = traits.List(traits.List(traits.Int()), mandatory=True)
	convergence_threshold = traits.List(
			trait=traits.Float(),
			value=[1e-6],
			minlen=1,
			requires=['number_of_iterations'],
			usedefault=True)
	convergence_window_size = traits.List(
			trait=traits.Int(),
			value=[10],
			minlen=1,
			requires=['convergence_threshold'],
			usedefault=True)
	# Output flags
	output_transform_prefix = traits.Str(
			"transform", usedefault=True, argstr="%s", desc="")
	output_warped_image = traits.Either(
			traits.Bool, File(), hash_files=False, desc="")
	output_inverse_warped_image = traits.Either(
			traits.Bool,
			File(),
			hash_files=False,
			requires=['output_warped_image'],
			desc="")
	winsorize_upper_quantile = traits.Range(
			low=0.0,
			high=1.0,
			value=1.0,
			argstr='%s',
			usedefault=True,
			desc="The Upper quantile to clip image ranges")
	winsorize_lower_quantile = traits.Range(
			low=0.0,
			high=1.0,
			value=0.0,
			argstr='%s',
			usedefault=True,
			desc="The Lower quantile to clip image ranges")

	verbose = traits.Bool(argstr='-v', default_value=False, usedefault=True)

	out_file = File( argstr="%s", position=-1, desc="image to operate on")
	in_file= File(exists=True, argstr="%s", position=-2, desc="PET file")


def mat2xfm(mat):
	return 0


class mincANTSCommand(CommandLine):
	input_spec =  mincANTSInput
	output_spec = mincANTSOutput

	_cmd = "ANTS"

	def _run_interface(self, runtime):

		mnc2nii_sh = pe.Node(interface=mnc2nii_shCommand(), name="mnc2nii_sh")
		nii2mnc_sh = pe.Node(interface=nii2mnc_shCommand(), name="nii2mnc_sh")
		reg = pe.Node(interface=Registration(), name="registration") 

		mnc2nii_sh.inputs.in_file = self.inputs.moving_image 
		mnc2nii_sh.run()

		mnc2nii_sh_nodes=[]
		inputs=[ "fixed_image", "fixed_image_mask",  "fixed_image_mask", "fixed_image_mask", "moving_image", "moving_image_mask", "moving_image_masks"]
		self_inputs=[ self.inputs.fixed_image, self.inputs.fixed_image_mask,  self.inputs.fixed_image_mask, self.inputs.fixed_image_mask, self.inputs.moving_image, self.inputs.moving_image_mask, self.inputs.moving_image_masks]
		reg_inputs=[ reg.inputs.fixed_image, reg.inputs.fixed_image_mask,  reg.inputs.fixed_image_mask, reg.inputs.fixed_image_mask, reg.inputs.moving_image, reg.inputs.moving_image_mask, reg.inputs.moving_image_masks]
		for s, r, i in zip(self_inputs, reg_inputs, inputs) : 
			if isdefined(s) : 
				mnc2nii_sh = pe.Node(interface=mnc2nii_shCommand(), name="mnc2nii_sh_"+i, in_file=self.inputs.fixed_image)
				mnc2nii_sh.run()
				r = mnc2nii_sh.out_file

		if isdefined( self.inputs.dimension) : reg.inputs.dimension = self.inputs.dimension 
		if isdefined( self.inputs.save_state ) : reg.inputs.save_state= self.inputs.save_state
		if isdefined( self.inputs.restore_state ) : reg.inputs.restore_state= self.inputs.restore_state
		if isdefined( self.inputs.initial_moving_transform ) : reg.inputs.initial_moving_tr =self.inputs.initial_moving_tr
		if isdefined( self.inputs.invert_initial_moving_transform ) : reg.inputs.invert_initial_moving_tr = self.inputs.invert_initial_moving_tr
		if isdefined( self.inputs.initial_moving_transform_com ) : reg.inputs.initial_moving_transform_com= self.inputs.initial_moving_transform_com
		if isdefined( self.inputs.metric_item_trait  ) : reg.inputs.metric_item_trait= self.inputs.metric_item_trait
		if isdefined( self.inputs.metric_stage_trait ) : reg.inputs.metric_stage_trait= self.inputs.metric_stage_trait
		if isdefined( self.inputs.metric ) : reg.inputs.metric= self.inputs.metric
		if isdefined( self.inputs.metric_weight_item_trait ) : reg.inputs.metric_weight_item_trait= self.inputs.metric_weight_item_trait
		if isdefined( self.inputs.metric_weight_stage_trait) : reg.inputs.metric_weight_stage_trait= self.inputs.metric_weight_stage_trait
		if isdefined( self.inputs.metric_weight ) : reg.inputs.metric_weight= self.inputs.metric_weight
		if isdefined( self.inputs.radius_bins_item_trait) : reg.inputs.radius_bins_item_trait= self.inputs.radius_bins_item_trait
		if isdefined( self.inputs.radius_bins_stage_trait ) : reg.inputs.radius_bins_stage_trait= self.inputs.radius_bins_stage_trait
		if isdefined( self.inputs.radius_or_number_of_bins ) : reg.inputs.radius_or_number_of_bins= self.inputs.radius_or_number_of_bins
		if isdefined( self.inputs.sampling_strategy_item_trait ) : reg.inputs.sampling_strategy_item_trait= self.inputs.sampling_strategy_item_trait
		if isdefined( self.inputs.sampling_strategy_stage_trait) : reg.inputs.sampling_strategy_stage_trait= self.inputs.sampling_strategy_stage_trait
		if isdefined( self.inputs.sampling_strategy) : reg.inputs.sampling_strategy= self.inputs.sampling_strategy
		if isdefined( self.inputs.sampling_percentage_item_trait ) : reg.inputs.sampling_percentage_item_trait= self.inputs.sampling_percentage_item_trait
		if isdefined( self.inputs.sampling_percentage_stage_trait) : reg.inputs.sampling_percentage_stage_trait= self.inputs.sampling_percentage_stage_trait
		if isdefined( self.inputs.sampling_percentage ) : reg.inputs.sampling_percentage= self.inputs.sampling_percentage
		if isdefined( self.inputs.use_estimate_learning_rate_once ) : reg.inputs.use_estimate_learning_rate_once= self.inputs.use_estimate_learning_rate_once
		if isdefined( self.inputs.use_histogram_matching) : reg.inputs.use_histogram_matching= self.inputs.use_histogram_matching
		if isdefined( self.inputs.interpolation) : reg.inputs.interpolation= self.inputs.interpolation
		if isdefined( self.inputs.interpolation_parameters) : reg.inputs.interpolation_parameters= self.inputs.interpolation_parameters
		if isdefined( self.inputs.write_composite_transform ) : reg.inputs.write_composite_transform= self.inputs.write_composite_transform
		if isdefined( self.inputs.collapse_output_transforms) : reg.inputs.collapse_output_transforms= self.inputs.collapse_output_transforms
		if isdefined( self.inputs.initialize_transforms_per_stage ) : reg.inputs.initialize_transforms_per_stage= self.inputs.initialize_transforms_per_stage
		if isdefined( self.inputs.float ) : reg.inputs.float= self.inputs.float
		if isdefined( self.inputs.transform_parameters) : reg.inputs.transform_parameters= self.inputs.transform_parameters
		if isdefined( self.inputs.restrict_deformation ) : reg.inputs.restrict_deformation= self.inputs.restrict_deformation
		if isdefined( self.inputs.number_of_iterations ) : reg.inputs.number_of_iterations= self.inputs.number_of_iterations
		if isdefined( self.inputs.smoothing_sigmas ) : reg.inputs.smoothing_sigmas= self.inputs.smoothing_sigmas
		if isdefined( self.inputs.sigma_units) : reg.inputs.sigma_units= self.inputs.sigma_units
		if isdefined( self.inputs.shrink_factors ) : reg.inputs.shrink_factors= self.inputs.shrink_factors
		if isdefined( self.inputs.convergence_threshold) : reg.inputs.convergence_threshold= self.inputs.convergence_threshold
		if isdefined( self.inputs.convergence_window_size) : reg.inputs.convergence_window_size= self.inputs.convergence_window_size
		if isdefined( self.inputs.output_transform_prefix ) : reg.inputs.output_transform_prefix= self.inputs.output_transform_prefix
		if isdefined( self.inputs.output_warped_image ) : reg.inputs.output_warped_image= self.inputs.output_warped_image
		if isdefined( self.inputs.output_inverse_warped_image ) : reg.inputs.output_inverse_warped_image= self.inputs.output_inverse_warped_image
		if isdefined( self.inputs.winsorize_upper_quantile ) : reg.inputs.winsorize_upper_quantile= self.inputs.winsorize_upper_quantile
		if isdefined( self.inputs.winsorize_lower_quantile ) : reg.inputs.winsorize_lower_quantile= self.inputs.winsorize_lower_quantile
		if isdefined( self.inputs.verbose) : reg.inputs.verbose= self.inputs.verbose

		reg.run()


		nii2mnc_sh.inputs.in_file = reg.inputs.warped_image
		nii2mnc_sh.run()
		self.outputs.warped_image = nii2mnc_sh.inputs.warped_image
		return(runtime)


	def _list_outputs(self):
		if not isdefined(self.inputs.warped_image):
			self.inputs.warped_image = reg.inputs.warped_image
		outputs = self.output_spec().get()
		outputs["warped_image"] = self.inputs.warped_image
		return outputs



def _parse_inputs(self, skip=None):
	if skip is None:
		skip = []
		if not isdefined(self.inputs.out_file):
			self.inputs.out_file = self._gen_output(self.inputs.in_file)
		return super(mincconvertCommand, self)._parse_inputs(skip=skip)



