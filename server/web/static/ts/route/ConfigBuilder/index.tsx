import React, { ChangeEvent, FormEvent } from 'react';
import { RouteProps } from '../../routing';
import { AnyStage, CameraConfig, CameraInfo, LocalConfig, OakSelector } from '../../config';
import Loading from '../../components/Loading';
import SelectorForm from './SelectorForm';
import PipelineStages from './stages';


interface Props extends RouteProps {

}


interface State {
	cameras: CameraInfo[] | null;
	config: LocalConfig | null;
	cancel: AbortController;
}

interface InnerProps {
	cameras: CameraInfo[];
	config: LocalConfig;
}

interface InnerState {
	config: LocalConfig;
	selectedCamera: number;
	pipeline: AnyStage[];
}

class ConfigBuilderInner extends React.Component<InnerProps, InnerState> {
	constructor(props: InnerProps) {
		super(props);
		this.state = {
			selectedCamera: 0,
			pipeline: [],
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
			this.setState(({ config }) => ({
				selectedCamera: (config?.cameras.length ?? 0),
				config: {
					...(config!),
					cameras: [
						...config!.cameras,
						{
							selector: {}
						}
					]
				}
			}));
		}
	}

	private updateCurrent(cb: (current: CameraConfig) => CameraConfig) {
		this.setState(({config, selectedCamera }) => ({
			config: {
				...config,
				cameras: config.cameras
					.map((config, i) => (i == selectedCamera) ? cb(config) : config),
			}
		}))
	}

	private readonly handleSelectorChange = (value: OakSelector) => {
		this.updateCurrent(config => ({
			...config,
			selector: value
		}));
	}

	private readonly handlePipelineChange = (value: AnyStage[]) => {
		this.updateCurrent(config => ({
			...config,
			pipeline: value,
		}))
	}

	render(): React.ReactNode {
		const currentCameraConfig = this.state.config.cameras[this.state.selectedCamera];

		const currentSelector = (typeof currentCameraConfig.selector === 'string')
			? this.state.config.camera_selectors.find(selector => selector.id == currentCameraConfig.selector)!
			: currentCameraConfig.selector;
		
		return (
			<div>
				<label htmlFor="cameras">Camera</label>
				<select id="cameras" onChange={this.handleCameraChange} value={`camera-${this.state.selectedCamera}`}>
					{this.state.config.cameras.map((camera, i) => (
						<option key={i} value={`camera-${i}`}>Camera {i}</option>
					))}
					<option key="new" value="new">Add Camera...</option>
				</select>
				<SelectorForm
					cameras={this.props.cameras}
					selector={currentSelector}
					onChange={this.handleSelectorChange}
				/>
				<PipelineStages
					config={this.state.config}
					stages={currentCameraConfig.pipeline as AnyStage[] ?? []}
					onChange={this.handlePipelineChange}
				/>
				<button>
					Save
				</button>
			</div>
		)
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
			cancel: new AbortController(),
		}
	}

	componentDidMount(): void {
		this.fetchConfig();
		this.fetchCameras();
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

	render(): React.ReactNode {
		if (this.state.config === null || this.state.cameras === null)
			return <Loading />;
		
		return (
			<ConfigBuilderInner
				cameras={this.state.cameras}
				config={this.state.config}
			/>
		);
	}
}