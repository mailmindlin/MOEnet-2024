import React from 'react';
import { AnyStage, DepthConfigStage, InheritStage, LocalConfig, MonoConfigStage, ObjectDetectionStage, RgbConfigStage, SaveStage, ShowStage, StageTypes, TelemetryStage, WebStreamStage } from '../../config';

interface StageProps<S extends AnyStage> {
	config: LocalConfig;
	stage: S;
	idx: number;
}

function StageInherit({ config, stage }: StageProps<InheritStage>) {
	return (<>
		<legend>Inherit</legend>
		<PipelineStages
			config={config}
			stages={config.pipelines.find(p => p.id == stage.id)!.stages}
			legend={(
				<select value={stage.id}>
					{config.pipelines.map(pipeline => (
						<option key={pipeline.id}>Pipeline {pipeline.id}</option>
					))}
				</select>
			)}
		/>
	</>);
}
function StageWeb({ config, stage, idx }: StageProps<WebStreamStage>) {
	return (<>
		<legend>Web</legend>
		Stream images to web server
		<label htmlFor={`target_${idx}`}>Target </label>
		<select id={`target_${idx}`} value={stage.target}>
			<option value="left">Left</option>
			<option value="right">Right</option>
			<option value="rgb">RGB</option>
			<option value="depth">Depth</option>
		</select>
	</>);
}
function StageApriltag({ config, stage, idx }: StageProps<WebStreamStage>) {
	return (<>
		<legend>AprilTag</legend>
		Detect AprilTags
		<label htmlFor={`target_${idx}`}>Camera</label>
		<select id={`target_${idx}`} value={stage.target}>
			<option value="left">Left</option>
			<option value="right">Right</option>
			<option value="rgb">RGB</option>
			<option value="depth">Depth</option>
		</select>
	</>);
}
function StageMono({ stage, idx }: StageProps<MonoConfigStage>) {
	return (<>
		<legend>Mono</legend>
		Configure IR camera
		<label htmlFor={`target_${idx}`}>Target </label>
		<select id={`target_${idx}`} value={stage.target}>
			<option value="left">Left</option>
			<option value="right">Right</option>
		</select>
	</>);
}
function StageRgb({ stage, idx }: StageProps<RgbConfigStage>) {
	return (<>
		<legend>Color Camera</legend>
		Configure color camera
	</>);
}
function StageDepth({ stage, idx }: StageProps<DepthConfigStage>) {
	return (<>
		<legend>Stereo Depth</legend>
		Configure stereo depth
	</>);
}
function StageObjectDetection({ stage, idx }: StageProps<ObjectDetectionStage>) {
	return (<>
		<legend>Object Detection</legend>
		Detect objects
	</>);
}

function StageSaveImage({ stage, idx }: StageProps<SaveStage>) {
	return (<>
		<legend>Save Image</legend>
		Save image from camera to file
		<label htmlFor={`saveImagePath-${idx}`}>Path</label>
		<input id={`saveImagePath-${idx}`} type="text" />

		<label htmlFor={`target_${idx}`}>Camera</label>
		<select id={`target_${idx}`} value={stage.target}>
			<option value="left">Left IR</option>
			<option value="right">Right IR</option>
			<option value="rgb">Color camer</option>
		</select>
	</>);
}
function StageShow({ stage, idx }: StageProps<ShowStage>) {
	return (<>
		<legend>Show Image</legend>
		Show image on device (for debugging only)
	</>);
}
function StageTelemetry({ stage, idx }: StageProps<TelemetryStage>) {
	return (<>
		<legend>Telemetry</legend>
	</>);
}

const stages: Partial<Record<AnyStage['stage'], (props: StageProps<any>) => JSX.Element>> = {
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
}
function renderInner(config: LocalConfig, stage: AnyStage, idx: number, onChange?: (v: AnyStage[]) => void) {
	const Element = stages[stage.stage];
	if (Element)
		return <>
			<input type="checkbox" checked={true /* TODO */} />
			<Element config={config} stage={stage} idx={idx} />
			</>;
	return (<span>Unknown stage {stage.stage}</span>);
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
				id: config.pipelines[0].id,
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
			};
		case 'mono':
			return {
				stage: 'mono',
				target: targetsRemaining(stages, 'mono', ['left', 'right'])[0],
			};
		case 'depth':
		case 'rgb':
			return { stage };
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
}
export default function PipelineStages({ config, stages, onChange, ...props }: PipelineStagesProps) {
	const [addOption, setAddOption] = React.useState<keyof StageTypes>('inherit');

	function disableUnique(type: AnyStage['stage']): boolean {
		return !!stages.find(stage => stage.stage == type)
	}

	function disableTargets<K extends 'mono' | 'show' | 'web'>(type: K, values: StageTypes[K]['target'][]): boolean {
		return targetsRemaining(stages, type, values).length === 0;
	}

	return (
		<fieldset>
			<legend>Pipeline {props.legend}</legend>
			{
				stages.map((stage, i) => (
					<fieldset key={`stage-${i}`}>
						{renderInner(config, stage, i, onChange)}
					</fieldset>
				))
			}
			{onChange && <>
				<label htmlFor='ps_addoption'>Add stage</label>
				<select id="ps_addoption" value={addOption} onChange={e => setAddOption(e.currentTarget.value as any)}>
					<option value="inherit" disabled={config.pipelines.length == 0}>Inherit</option>
					<option value="web" disabled={disableTargets('web', ['left', 'right', 'rgb', 'depth'])}>Web</option>
					<option value="mono" disabled={disableTargets('mono', ['left', 'right'])}>IR Camera</option>
					<option value="rgb" disabled={disableUnique('rgb')}>Color Camera</option>
					<option value="stereo" disabled={disableUnique('depth')}>Stereo Depth</option>
					<option value="slam" disabled={disableUnique('slam')}>SLAM</option>
					<option value="show">Show</option>
					<option value="nn" disabled={disableUnique('nn')}>Object Detection</option>
					<option value="save">Save Image</option>
					<option value="telemetry" disabled={disableUnique('telemetry')}>Telemetry</option>
				</select>
				<button
					onClick={e => {
						onChange([
							...stages,
							makeDefault(config, stages, addOption)
						])
					}}
				>
					Add
				</button>
			</>}
		</fieldset>
	)
}