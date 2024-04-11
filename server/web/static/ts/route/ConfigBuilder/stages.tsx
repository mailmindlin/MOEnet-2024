import React, { ChangeEvent } from 'react';
import {  AprilTagStageConfig, Apriltags, ColorCameraStageConfig, InheritStageConfig, LocalConfig, MonoCameraStageConfig, ObjectDetectionStageConfig, PipelineConfig, SaveStageConfig, ShowStageConfig, SlamStageConfig, StereoDepthStageConfig, TelemetryStageConfig, WebStreamStageConfig } from '../../config';
import { Binding, BoundCheckbox, BoundSelect, bindChangeHandler } from './bound';
import { AprilTagFieldSelector } from './apriltag';
import { boundUpdateKey } from './ds';

type ArrayElement<ArrayType extends readonly unknown[]> = 
  ArrayType extends readonly (infer ElementType)[] ? ElementType : never;
type AnyStage = ArrayElement<PipelineConfig>
interface StageProps<S extends AnyStage> {
	config: LocalConfig;
	stage: S;
	idx: number;
	onChange?(stage: S): void;
	onDelete?(): void;
}



interface RenderStageProps<S> {
	stage: S;
	title: string;
	description?: string;
	children?: React.ReactNode;
	onChange?(stage: S): void;
	onDelete?(): void;
}

function RenderStage<S extends AnyStage>({ stage, title, description, children, onChange, onDelete }: RenderStageProps<S>) {
	const Bound: Binding<AnyStage> = Binding(stage, onChange);

	return (
		<fieldset>
			{ title && <legend>{title}</legend>}
			{description && <div>{description}</div>}
			<Bound.Checkbox
				name='enabled'
				label='Enabled'
				defaultValue={true}
			/>
			<Bound.Checkbox
				name='optional'
				label='Optional'
				defaultValue={false}
			/>
			{ children }
			{onDelete && (
				<div>
					<button onClick={onDelete}>Delete</button>
				</div>
			)}
		</fieldset>
	);
}

function StageInherit({ config, stage, onChange, ...props }: StageProps<InheritStageConfig>) {
	return (
		<RenderStage title='Inherit' stage={stage} onChange={onChange} {...props}>
			<PipelineStages
				config={config}
				stages={ /* TODO: Handle inconsistency */ (config.pipelines ?? []).find(p => p.id == stage.id)!.stages}
				legend={(
					<BoundSelect value={stage} name='id' onChange={onChange} label='Pipeline'>
						{config.pipelines!.map(pipeline => (
							<option key={pipeline.id}>{pipeline.id}</option>
						))}
					</BoundSelect>
				)}
			/>
		</RenderStage>
	);
}
function StageWeb({ stage, onChange, ...props }: StageProps<WebStreamStageConfig>) {
	return (
		<RenderStage title='Web' description='Stream images to web server' stage={stage} onChange={onChange} {...props}>
			<BoundSelect label='Target' value={stage} name={'target'} onChange={onChange}>
				<option value="left">Left</option>
				<option value="right">Right</option>
				<option value="rgb">RGB</option>
				<option value="depth">Depth</option>
			</BoundSelect>
		</RenderStage>
	);
}
function StageApriltag({ onChange, stage, ...props }: StageProps<AprilTagStageConfig>) {
	const Bound = Binding(stage, onChange);
	return (
		<RenderStage title='AprilTag' description='Detect AprilTags' stage={stage} onChange={onChange} {...props}>
			<Bound.Select label='Runtime' name='runtime'>
				<option value="host">Host</option>
				<option value="device">Device (OAK camera)</option>
			</Bound.Select>
			<Bound.Select label='Camera' name='camera'>
				<option value="left">Left</option>
				<option value="right">Right</option>
				<option value="rgb">RGB</option>
				{/* <option value="depth">Depth</option> */}
			</Bound.Select>
			<Bound.Checkbox label='Async' name='detectorAsync' help="Should we run the detector on a different thread? Only useful if we're doing multiple things with the same camera" />
			<Bound.Number label='Detector Threads' name='detectorThreads' min={1} nullable help='How many threads should be used for computation'/>
			<Bound.Number label='Decode Sharpening' name='decodeSharpening' min={0} nullable help='How much sharpening should be done to decoded images'/>
			<Bound.Number label='Quad Decimate' name='quadDecimate' min={0} step='any' nullable />
			<Bound.Number label='Quad Sigma' name='quadSigma' min={0} step='any' nullable />
			<Bound.Checkbox label='Refine Edges' name='refineEdges' />
			<Bound.Number label='Hamming Distance' name='hammingDist' min={0} max={3} help='Maximum number of bits to correct' />
			<Bound.Number label='Decision Margin' name='decisionMargin' min={0} step='any' nullable />
			<Bound.Number label='# Iterations' name='numIterations' min={0} nullable />
			<Bound.Checkbox label='Undistort' name='undistort' help="Should we try to undistort the camera lens?" />
			<Bound.Checkbox label='Solve PnP' name='solvePNP' help='Compute position (PnP) from AprilTag detections'/>
			<Bound.Checkbox label='Multi Target' name='doMultiTarget' help='Run SolvePnP with multiple AprilTags in a single frame'/>
			<Bound.Checkbox label='Single Target Always?' name='doSingleTargetAlways' help='Always run SolvePnP for each AprilTag detection individually'/>
			<AprilTagFieldSelector
				value={stage.apriltags}
				onChange={onChange && React.useCallback((apriltags: Apriltags) => onChange({...stage, apriltags }), [stage])}
			/>
		</RenderStage>
	);
}
function StageMono({ stage, onChange, ...props }: StageProps<MonoCameraStageConfig>) {
	return (
		<RenderStage title='IR Camera' description='Configure IR camera' stage={stage} onChange={onChange} {...props}>
			<BoundSelect label='Camera' value={stage} name='target' onChange={onChange}>
				<option value="left">Left</option>
				<option value="right">Right</option>
			</BoundSelect>
			<BoundSelect label='Sensor Resolution' value={stage} name='resolution' onChange={onChange}>
				<option value="$null">Default</option>
				<option value="THE_400_P">400p</option>
				<option value="THE_480_P">480p</option>
				<option value="THE_720_P">720p</option>
				<option value="THE_800_P">800p</option>
				<option value="THE_1200_P">1200p</option>
			</BoundSelect>
		</RenderStage>
	);
}
function StageRgb({ stage, onChange, ...props }: StageProps<ColorCameraStageConfig>) {
	return (
		<RenderStage title='Color Camera' description='Configure color camera' stage={stage} onChange={onChange} {...props}>
			<BoundSelect label='Sensor Resolution' value={stage} name='resolution' onChange={onChange}>
				<option value="$null">Default</option>
				<option value="THE_720_P">720p</option>
				<option value="THE_800_P">800p</option>
				<option value="THE_1080_P">1080p</option>
				<option value="THE_1200_P">1200p</option>
				<option value="THE_4_K">4k</option>
				<option value="THE_4000X3000">4000x3000</option>
				<option value="THE_5312X6000">5312x6000</option>
				<option value="THE_1440X1080">1440x1080</option>
				<option value="THE_1352X1012">1352x1012</option>
				<option value="THE_2024X1520">2024x1520</option>
				<option value="THE_5_MP">5 MP</option>
				<option value="THE_12_MP">12 MP</option>
				<option value="THE_13_MP">13 MP</option>
				<option value="THE_48_MP">48 MP</option>
			</BoundSelect>
		</RenderStage>
	);
}
function StageDepth({ stage, onChange, ...props }: StageProps<StereoDepthStageConfig>) {
	return (
		<RenderStage title='Stereo Depth' description='Configure stereo depth' stage={stage} onChange={onChange} {...props}>
			<BoundCheckbox value={stage} onChange={onChange} name='checkLeftRight' label='Check Left/Right' />
			<BoundCheckbox value={stage} onChange={onChange} name='extendedDisparity' label='Extended Disparity' />
			<BoundSelect label='Preset' value={stage} name='preset' onChange={onChange}>
				<option value="$null">None</option>
				<option value="high_accuracy">High Accuracy</option>
				<option value="high_density">High Density</option>
			</BoundSelect>
		</RenderStage>
	);
}
function StageObjectDetection({ stage, onChange, ...props }: StageProps<ObjectDetectionStageConfig>) {
	return (
		<RenderStage title='Object Detection' description='Detect Objects' stage={stage} onChange={onChange} {...props}>

		</RenderStage>
	);
}

function StageSaveImage({ stage, idx, onChange, ...props }: StageProps<SaveStageConfig>) {
	return (
		<RenderStage title='Save Image' description='Save images from camera to disk' stage={stage} onChange={onChange} {...props}>
			<label htmlFor={`saveImagePath-${idx}`}>Path</label>
			<input id={`saveImagePath-${idx}`} type="text" />
			<BoundSelect label='Camera' value={stage} name='target' onChange={onChange}>
				<option value="left">Left IR</option>
				<option value="right">Right IR</option>
				<option value="rgb">Color</option>
			</BoundSelect>
		</RenderStage>
	);
}

function StageShow({ stage, onChange, ...props }: StageProps<ShowStageConfig>) {
	return (
		<RenderStage title='Show Image' description='Show image on device (for debugging only)' stage={stage} onChange={onChange} {...props}>
			<BoundSelect label='Camera' value={stage} name='target' onChange={onChange}>
				<option value="left">Left IR</option>
				<option value="right">Right IR</option>
				<option value="rgb">Color</option>
			</BoundSelect>
		</RenderStage>
	);
}
function StageTelemetry({ stage, onChange, ...props }: StageProps<TelemetryStageConfig>) {
	return (
		<RenderStage title='Telemetry' description='Fetch device telemetry' stage={stage} onChange={onChange} {...props}>

		</RenderStage>
	);
}

function StageSlam({ stage, onChange, ...props }: StageProps<SlamStageConfig>) {
	return (
		<RenderStage title='SLAM' description='SpectacularAI SLAM' stage={stage} onChange={onChange} {...props}>
			<BoundCheckbox value={stage} onChange={onChange} name='slam' label='Enable SLAM' />
			<BoundCheckbox value={stage} onChange={onChange} name='vio' label='Enable VIO' />
			<BoundCheckbox value={stage} onChange={onChange} name='waitForPose' label='Wait for pose' />
		</RenderStage>
	);
}
type StageType = Exclude<AnyStage['stage'], undefined>;
type StageTypes = {
	'inherit': InheritStageConfig,
	'web': WebStreamStageConfig,
	'apriltag': AprilTagStageConfig,
	'mono': MonoCameraStageConfig,
	'rgb': ColorCameraStageConfig,
	'depth': StereoDepthStageConfig,
	'nn': ObjectDetectionStageConfig,
	'save': SaveStageConfig,
	'show': ShowStageConfig,
	'telemetry': TelemetryStageConfig,
	'slam': SlamStageConfig,
}

const stages: Partial<Record<StageType, (props: StageProps<any>) => JSX.Element>> = {
	'inherit': StageInherit,
	'web': StageWeb,
	'apriltag': StageApriltag,
	'mono': StageMono,
	'rgb': StageRgb,
	'depth': StageDepth,
	'nn': StageObjectDetection,
	'save': StageSaveImage,
	'show': StageShow,
	'telemetry': StageTelemetry,
	'slam': StageSlam,
}
function renderInner(config: LocalConfig, stage: AnyStage, idx: number, onChange?: (v: AnyStage) => void, onDelete?: () => void) {
	const Element = stages[stage.stage!];
	const key = `stage-${idx}`;
	if (Element)
		return <Element key={key} config={config} stage={stage} idx={idx} onChange={onChange} onDelete={onDelete}/>;
	return (<span key={key}>Unknown stage {stage.stage}</span>);
}

function targetsRemaining<K extends 'mono' | 'show' | 'web'>(stages: AnyStage[], type: K, values: StageTypes[K]['target'][]): StageTypes[K]['target'][] {
	const unique = stages.filter(stage => stage.stage == type) as StageTypes[K][];
	const remaining = new Set(values);
	for (const e of unique)
		remaining.delete(e.target);
	return values.filter(value => remaining.has(value));
}

function makeDefault<K extends keyof StageTypes>(config: LocalConfig, stages: AnyStage[], stage: K): AnyStage {
	switch (stage) {
		case 'inherit':
			return {
				stage: 'inherit',
				id: config.pipelines?.[0]?.id ?? 'unknown',
			};
		case 'apriltag':
			return {
				stage: 'apriltag',
				runtime: 'host',
				camera: 'left',
				quadDecimate: 1,
				quadSigma: 0,
				refineEdges: true,
				numIterations: 40,
				hammingDist: 0,
				decisionMargin: 35,
				apriltags: '2024Crescendo',
			};
		case 'mono':
			return {
				stage: 'mono',
				target: targetsRemaining(stages, 'mono', ['left', 'right'])[0],
			};
		case 'depth':
		case 'rgb':
		case 'slam':
		case 'telemetry':
			return { stage };
		case 'show':
			return {
				stage: 'show',
				target: targetsRemaining(stages, 'show', ['left', 'right', 'rgb', 'depth'])[0],
			};
		case 'web':
			return {
				stage: 'web',
				target: targetsRemaining(stages, 'web', ['left', 'right', 'depth', 'rgb'])[0],
			};
		case 'save':
			return { stage: 'save', target: 'left', path: '' };
		case 'nn':
			return {
				stage: 'nn',
				blobPath: '',
				config: {
					anchor_masks: {},
					anchors: [],
					classes: 0,
					confidence_threshold: 0.9,
					coordinateSize: 0.5,
					labels: [],
					iou_threshold: 0.5,
					depthLowerThreshold: 0,
					depthUpperThreshold: 0,
				},
			}
		default:
			return {} as any;
	}
}
interface PipelineStagesProps {
	config: LocalConfig;
	stages: AnyStage[];
	legend?: React.ReactNode;
	onChange?(stages: AnyStage[]): void;
	onDelete?(): void;
}
export default function PipelineStages({ config, stages, onChange, ...props }: PipelineStagesProps) {
	const [addOption, setAddOption] = React.useState<keyof StageTypes>('inherit');
	const asId = React.useId();

	// Disable adding stages that must be unique
	function disableUnique(type: AnyStage['stage']): boolean {
		return !!stages.find(stage => stage.stage == type)
	}

	// Disable targets that must be unique
	function disableTargets<K extends 'mono' | 'show' | 'web'>(type: K, values: StageTypes[K]['target'][]): boolean {
		return targetsRemaining(stages, type, values).length === 0;
	}

	function replaceStage(idx: number, stage: AnyStage) {
		onChange!([
			...stages.slice(0, idx),
			stage,
			...stages.slice(idx + 1),
		])
	}

	function deleteStage(idx: number) {
		onChange!([
			...stages.slice(0, idx),
			...stages.slice(idx + 1),
		])
	}

	return (
		<fieldset>
			<legend>{props.legend}</legend>
			{
				stages.map((stage, i) => (
					renderInner(config, stage, i, onChange ? replaceStage.bind(replaceStage, i) : undefined, onChange ? deleteStage.bind(null, i) : undefined)
				))
			}
			{onChange && <>
				<label htmlFor={asId}>Add stage&nbsp;</label>
				<select id={asId} value={addOption} onChange={e => setAddOption(e.currentTarget.value as any)}>
					<option value="inherit" disabled={config.pipelines?.length == 0}>Inherit</option>
					<option value="web" disabled={disableTargets('web', ['left', 'right', 'rgb', 'depth'])}>Web</option>
					<option value="mono" disabled={disableTargets('mono', ['left', 'right'])}>IR Camera</option>
					<option value="rgb" disabled={disableUnique('rgb')}>Color Camera</option>
					<option value="depth" disabled={disableUnique('depth')}>Stereo Depth</option>
					<option value="slam" disabled={disableUnique('slam')}>SLAM</option>
					<option value="apriltag" disabled={disableUnique('apriltag')}>AprilTag</option>
					<option value="show">Show</option>
					<option value="nn" disabled={disableUnique('nn')}>Object Detection</option>
					<option value="save">Save Image</option>
					<option value="telemetry" disabled={disableUnique('telemetry')}>Telemetry</option>
				</select>
				<button
					onClick={() => {
						onChange([
							...stages,
							makeDefault(config, stages, addOption)
						])
					}}
				>
					Add
				</button>
			</>}
			{props.onDelete && <div><button onClick={props.onDelete}>Delete Pipeline</button></div> }
		</fieldset>
	)
}