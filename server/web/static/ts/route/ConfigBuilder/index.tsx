import React, { ChangeEvent } from 'react';
import { RouteProps } from '../../routing';
import { CameraConfig, CameraSelectorDefinition, LocalConfig, OakSelector, PipelineConfig, PipelineDefinition, Selector } from '../../config';
import Loading from '../../components/Loading';
import SelectorForm, { CameraFilterEditor, PoseEditor } from './camera';
import PipelineStages from './stages';
import { JsonSchemaLike, JsonSchemaRoot } from './jsonschema';
import NetworkTablesEditor from './nt';
import { BoundList, BoundListRenderItemProps, BoundTextInput } from './bound';
import LogConfigEditor from './logging';
import DatalogConfigEdtior from './datalog';
import WebConfigEditor from './web';
import EstimatorConfigEditor from './estimator';
import { boundReplaceKey, boundUpdateKey } from './ds';
import Collapsible from '../../components/Collapsible';


interface Props extends RouteProps {

}

export interface CameraInfo {
	'name': string,
	'mxid': string,
	'state': string,
	'status': string,
	'platform': string,
	'protocol': string,
}

interface State {
	schema: (JsonSchemaLike<LocalConfig> & JsonSchemaRoot) | null;
	cameras: CameraInfo[] | null;
	config: LocalConfig | null;
	cancel: AbortController;
}

interface InnerProps {
	camera_templates: CameraInfo[];
	schema: JsonSchemaLike<LocalConfig> & JsonSchemaRoot;
	config: LocalConfig;
}

interface InnerState {
	config: LocalConfig;
	selectedCamera: number;
}

class ConfigBuilderInner extends React.Component<InnerProps, InnerState> {
	constructor(props: InnerProps) {
		super(props);
		this.state = {
			selectedCamera: 0,
			config: props.config,
		};
	}

	private readonly handleCameraChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
		const value = e.currentTarget.value;
		e.preventDefault();
		if (value.startsWith('camera-')) {
			this.setState({
				selectedCamera: parseInt(value.substring('camera-'.length))
			})
		} else {
			// New camera
			this.setState(({ config }) => ({
				selectedCamera: (config?.cameras?.length ?? 1),
				config: {
					...(config!),
					cameras: [
						...(config!.cameras ?? []),
						{
							selector: {},
							pose: {
								"rotation": {
									"quaternion": {
										"W": 1, "X": 0, "Y": 0, "Z": 0
									}
								},
								"translation": {
									"x": 0,
									"y": 0,
									"z": 0,
								}
							}
						}
					]
				}
			}));
		}
	}

	private readonly addCameraSelector = () => {
		this.setState(({ config }) => ({
			config: {
				...config,
				camera_selectors: [
					...(config.camera_selectors ?? []),
					{
						id: ""
					}
				]
			}
		}))
	}

	private readonly setCameraSelectors = (selectors: CameraSelectorDefinition[]) => {
		this.setState(({ config }) => ({
			config: {
				...config,
				camera_selectors: selectors
			}
		}))
	}

	private readonly addPipelineTemplate = () => {
		this.setState(({ config }) => ({
			config: {
				...config,
				pipelines: [
					...(config.pipelines ?? []),
					{
						id: "",
						stages: [],
					}
				]
			}
		}))
	}


	private updatePipelineTemplate(index: number, update: PipelineDefinition) {
		this.setState(({ config }) => {
			const result = {
				...config,
				pipelines: [
					...(config.pipelines ?? [])
				]
			}

			if (result.pipelines[index].id !== update.id) {
				// Update dependencies
				const prevId = result.pipelines[index].id;

				function updateStages(stages: PipelineConfig) {
					return stages.map(stage => {
						if (stage.stage === 'inherit' && stage.id === prevId) {
							return {
								...stage,
								id: update.id,
							}
						}
						return stage;
					})
				}

				function updateCamera(camera: CameraConfig) {
					if (camera.pipeline === prevId) {
						return {
							...camera,
							pipeline: update.id,
						}
					} else if (typeof camera.pipeline !== 'string' && camera.pipeline) {
						return {
							...camera,
							pipeline: updateStages(camera.pipeline),
						}
					} else {
						return camera;
					}
				}
				result.pipelines = result.pipelines.map(({ id, stages }) => ({
					id,
					stages: updateStages(stages),
				}));
				if (result.cameras)
					result.cameras = result.cameras.map(updateCamera);
			}
			result.pipelines[index] = update;
			return { config: result }
		})
	}

	private deletePipelineTemplate(index: number) {
		this.setState(({ config }) => ({
			config: {
				...config,
				pipelines: [
					...(config.pipelines ?? []).slice(0, index),
					...(config.pipelines ?? []).slice(index + 1),
				]
			}
		}))
	}

	private updateCurrent(cb: (current: CameraConfig) => CameraConfig) {
		this.setState(({config, selectedCamera }) => ({
			config: {
				...config,
				cameras: (config.cameras?.length ?? 0 <= selectedCamera)
					? (config.cameras ?? []).map((config, i) => (i == selectedCamera) ? cb(config) : config)
					: [...(config.cameras ?? []), cb({} as any)]
			}
		}), () => console.log(this.state));
	}

	private readonly handleSelectorChange = (value: OakSelector) => {
		console.log('selector change', value);
		this.updateCurrent(config => ({
			...config,
			selector: value
		}));
	}

	private readonly handlePipelineChange = (value: PipelineConfig | string) => {
		this.updateCurrent(config => ({
			...config,
			pipeline: value,
		}))
	}

	private getCurrentSelector(): [CameraConfig | undefined, PipelineConfig | undefined, Selector | undefined] {
		const currentCameraConfig = this.state.config.cameras?.[this.state.selectedCamera];
		if (!currentCameraConfig)
			return [undefined, undefined, undefined];

		let selector = currentCameraConfig.selector;

		// if (typeof selector === 'string') {
		// 	const selectors = this.state.config.camera_selectors;
		// 	if (selectors)
		// 		selector = selectors.find(selector => selector.id == currentCameraConfig.selector) ?? {};
		// 	else
		// 		console.log('Warning: no selectors')
		// }

		let pipeline: PipelineConfig;
		if (typeof currentCameraConfig.pipeline == 'string') {
			const pipelines = this.state.config.pipelines;
			if (pipelines)
				pipeline = pipelines.find(p1 => p1.id == currentCameraConfig.pipeline)?.stages ?? [];
			else
				pipeline = [];
		} else {
			pipeline = currentCameraConfig.pipeline ?? [];
		}
		return [currentCameraConfig, pipeline, selector];
	}

	private handleSubpropChange<K extends keyof LocalConfig>(key: K) {
		return (value: LocalConfig[K]) => {
			this.setState(({ config }) => ({
				config: {
					...config,
					[key]: value,
				},
			}));
		}
	}

	private handleNtChange = this.handleSubpropChange('nt');
	private handleLogChange = this.handleSubpropChange('log');
	private handleDatalogChange = this.handleSubpropChange('datalog');
	private handleEstimatorChange = this.handleSubpropChange('estimator');
	private handleWebChange = this.handleSubpropChange('web');

	private readonly renderCameraTemplate = ({ item, onChange, onDelete }: BoundListRenderItemProps<CameraSelectorDefinition>) => (
		<CameraFilterEditor
			legend={<BoundTextInput value={item} name='id' label='Selector' onChange={onChange} placeholder='Selector name' />}
			templates={this.props.camera_templates}
			selector={item}
			definitions={[] /* This could get recursive */}
			onChange={onChange}
			onDelete={onDelete}
		/>
	);

	private downloadJson = async () => {
		const text = JSON.stringify(this.state.config,undefined, '\t');
		try {
			const handle = await (window as any).showSaveFilePicker({
				startIn: 'downloads',
				suggestedName: 'moenet-config.json',
				types: [
					{
						"description": "MOEnet configuration",
						"accept": {
							"application/json": [".json"],
						}
					}
				]
			});
			const writable = await handle.createWritable();
			await writable.write(text);
			await writable.close();
		} catch (e) {
			console.log(e);
			var element = document.createElement('a');
			element.setAttribute('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(text));
			element.setAttribute('download', 'moenet-config.json');

			element.style.display = 'none';
			document.body.appendChild(element);

			element.click();

			document.body.removeChild(element);
		}
	}

	render(): React.ReactNode {
		const updateConfig = boundUpdateKey<InnerState, 'config'>('config', (cb) => this.setState(cb));
		const [currentCameraConfig, pipeline, selector] = this.getCurrentSelector()
		const cameras = this.state.config.cameras ?? [];

		console.log(this.state, selector);

		return (<div style={{"padding": 10}}>
			<button onClick={this.downloadJson}>
				Download JSON
			</button>
			<NetworkTablesEditor
				nt={this.state.config.nt}
				onChange={this.handleNtChange}
			/>
			<LogConfigEditor
				config={this.state.config.log}
				onChange={this.handleLogChange}
			/>
			<DatalogConfigEdtior
				config={this.state.config.datalog}
				onChange={this.handleDatalogChange}
			/>
			<EstimatorConfigEditor
				config={this.state.config.estimator}
				onChange={this.handleEstimatorChange}
			/>
			<WebConfigEditor
				config={this.state.config.web}
				onChange={this.handleWebChange}
			/>
			<Collapsible legend="Camera Templates">
				<BoundList
					value={this.state.config.camera_selectors ?? []}
					onChange={this.setCameraSelectors}
					canDelete
					renderItem={this.renderCameraTemplate}
				/>
				<button onClick={this.addCameraSelector}>Add new</button>
			</Collapsible>
			<Collapsible legend="Pipeline Templates">
				{(this.state.config.pipelines ?? []).map((pipeline, idx) => {
					const onChange = this.updatePipelineTemplate.bind(this, idx);
					const onChangeInner = (stages: PipelineConfig) => onChange({ id: pipeline.id, stages });
					return <PipelineStages
						key={idx}
						legend={<BoundTextInput value={pipeline} name='id' label='Pipeline' onChange={onChange} placeholder='Pipeline name' />}
						config={this.state.config}
						stages={pipeline.stages}
						onChange={onChangeInner}
						onDelete={this.deletePipelineTemplate.bind(this, idx)}
					/>;
				})}
				<button onClick={this.addPipelineTemplate}>Add new</button>
			</Collapsible>
			<fieldset>
				<legend>
					<label htmlFor="cameras">Camera&nbsp;</label>
					<select id="cameras" onChange={this.handleCameraChange} value={`camera-${this.state.selectedCamera}`}>
						{cameras.length == 0 && <option key="-">Select Camera</option>}
						
						{cameras.map((camera, i) => (
							<option key={i} value={`camera-${i}`}>Camera {i}</option>
						))}
						<option key="new" value="new">New Camera...</option>
					</select>
				</legend>
				{ selector && <>
					<SelectorForm
						templates={this.props.camera_templates}
						definitions={this.state.config.camera_selectors}
						selector={selector}
						onChange={this.handleSelectorChange}
					/>
					<PipelineStages
						legend={
							<select
								value={typeof currentCameraConfig!.pipeline === 'string' ? currentCameraConfig!.pipeline : '$custom'}
								onChange={e => this.handlePipelineChange(e.currentTarget.selectedIndex === 0 ? [] : e.currentTarget.value)}
							>
								<option value='$custom'>Custom</option>
								{(this.state.config.pipelines ?? []).map(definition =>
									<option id={definition.id} value={definition.id}>Template {definition.id}</option>
								)}
							</select>
						}
						config={this.state.config}
						stages={pipeline ?? []}
						onChange={typeof currentCameraConfig?.pipeline === 'string' ? undefined : this.handlePipelineChange}
					/>
					<fieldset>
						<legend>Config</legend>
						<PoseEditor
							value={currentCameraConfig?.pose!}
							onChange={boundReplaceKey('pose', currentCameraConfig!, s => this.updateCurrent(c => s))}
						/>
					</fieldset>
				</>}
			</fieldset>
		</div>);
	}

}
export default class ConfigBuilder extends React.Component<Props, State> {
	static readonly pattern: URLPattern = new URLPattern({ pathname: '/config' });
	static readonly title: string = 'Config';
	static readonly base: string = '/config';
	constructor(props: Props) {
		super(props);
		this.state = {
			cameras: null,
			config: null,
			schema: null,
			cancel: new AbortController(),
		}
	}

	componentDidMount(): void {
		this.fetchConfig();
		this.fetchCameras();
		this.fetchSchema();
	}

	componentWillUnmount(): void {
		this.state.cancel.abort();
	}

	async fetchCameras() {
		try {
			const res = await fetch('/api/cameras', {
				signal: this.state.cancel.signal,
				headers: { 'Content-Type': 'application/json' }
			});
			var data = await res.json();
		} catch {
			console.error('No config');
			return;
		}
		this.setState({
			cameras: data,
		});
	}

	async fetchConfig() {
		console.log('fetch config');
		try {
			const res = await fetch('/api/config', {
				signal: this.state.cancel.signal,
				headers: { 'Content-Type': 'application/json' }
			});
			var data = await res.json();
		} catch {
			console.error('No config');
			return;
		}
		this.setState({
			config: data,
		})
	}

	async fetchSchema() {
        try {
            const res = await fetch('/api/schema', {
                signal: this.state.cancel.signal,
                headers: { 'Content-Type': 'application/json' }
            });
            var data = await res.json();
        } catch {
            console.error('No schema');
            return;
        }
        this.setState({
            schema: data
        })
    }

	render(): React.ReactNode {
		if (this.state.config === null || this.state.cameras === null || this.state.schema === null)
			return <Loading />;
		
		return (
			<ConfigBuilderInner
				camera_templates={this.state.cameras}
				schema={this.state.schema}
				config={this.state.config}
			/>
		);
	}
}