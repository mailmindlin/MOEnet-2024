import React from 'react';
import Loading from '../../components/Loading';
import SelectorForm from './SelectorForm';
import PipelineStages from './stages';
class ConfigBuilderInner extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            selectedCamera: 0,
            pipeline: [],
            config: props.config,
        };
    }
    handleCameraChange = (e) => {
        const value = e.currentTarget.value;
        e.preventDefault();
        if (value.startsWith('camera-')) {
            this.setState({
                selectedCamera: parseInt(value.substring('camera-'.length))
            });
        }
        else {
            this.setState(({ config }) => ({
                selectedCamera: (config?.cameras.length ?? 0),
                config: {
                    ...(config),
                    cameras: [
                        ...config.cameras,
                        {
                            selector: {}
                        }
                    ]
                }
            }));
        }
    };
    updateCurrent(cb) {
        this.setState(({ config, selectedCamera }) => ({
            config: {
                ...config,
                cameras: config.cameras
                    .map((config, i) => (i == selectedCamera) ? cb(config) : config),
            }
        }));
    }
    handleSelectorChange = (value) => {
        this.updateCurrent(config => ({
            ...config,
            selector: value
        }));
    };
    handlePipelineChange = (value) => {
        this.updateCurrent(config => ({
            ...config,
            pipeline: value,
        }));
    };
    render() {
        const currentCameraConfig = this.state.config.cameras[this.state.selectedCamera];
        const currentSelector = (typeof currentCameraConfig.selector === 'string')
            ? this.state.config.camera_selectors.find(selector => selector.id == currentCameraConfig.selector)
            : currentCameraConfig.selector;
        return (React.createElement("div", null,
            React.createElement("label", { htmlFor: "cameras" }, "Camera"),
            React.createElement("select", { id: "cameras", onChange: this.handleCameraChange, value: `camera-${this.state.selectedCamera}` },
                this.state.config.cameras.map((camera, i) => (React.createElement("option", { key: i, value: `camera-${i}` },
                    "Camera ",
                    i))),
                React.createElement("option", { key: "new", value: "new" }, "Add Camera...")),
            React.createElement(SelectorForm, { cameras: this.props.cameras, selector: currentSelector, onChange: this.handleSelectorChange }),
            React.createElement(PipelineStages, { config: this.state.config, stages: currentCameraConfig.pipeline ?? [], onChange: this.handlePipelineChange }),
            React.createElement("button", null, "Save")));
    }
}
export default class ConfigBuilder extends React.Component {
    static pattern = new URLPattern({ pathname: '/config' });
    static title = 'Config';
    static base = '/config';
    constructor(props) {
        super(props);
        this.state = {
            cameras: null,
            config: null,
            cancel: new AbortController(),
        };
    }
    componentDidMount() {
        this.fetchConfig();
        this.fetchCameras();
    }
    componentWillUnmount() {
        this.state.cancel.abort();
    }
    async fetchCameras() {
        try {
            const res = await fetch('/api/cameras', {
                signal: this.state.cancel.signal,
                headers: { 'Content-Type': 'application/json' }
            });
            var data = await res.json();
        }
        catch {
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
        }
        catch {
            console.error('No config');
            return;
        }
        this.setState({
            config: data,
        });
    }
    render() {
        if (this.state.config === null || this.state.cameras === null)
            return React.createElement(Loading, null);
        return (React.createElement(ConfigBuilderInner, { cameras: this.state.cameras, config: this.state.config }));
    }
}
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiaW5kZXguanMiLCJzb3VyY2VSb290IjoiIiwic291cmNlcyI6WyIuLi8uLi8uLi90cy9yb3V0ZS9Db25maWdCdWlsZGVyL2luZGV4LnRzeCJdLCJuYW1lcyI6W10sIm1hcHBpbmdzIjoiQUFBQSxPQUFPLEtBQWlDLE1BQU0sT0FBTyxDQUFDO0FBR3RELE9BQU8sT0FBTyxNQUFNLDBCQUEwQixDQUFDO0FBQy9DLE9BQU8sWUFBWSxNQUFNLGdCQUFnQixDQUFDO0FBQzFDLE9BQU8sY0FBYyxNQUFNLFVBQVUsQ0FBQztBQXlCdEMsTUFBTSxrQkFBbUIsU0FBUSxLQUFLLENBQUMsU0FBaUM7SUFDdkUsWUFBWSxLQUFpQjtRQUM1QixLQUFLLENBQUMsS0FBSyxDQUFDLENBQUM7UUFDYixJQUFJLENBQUMsS0FBSyxHQUFHO1lBQ1osY0FBYyxFQUFFLENBQUM7WUFDakIsUUFBUSxFQUFFLEVBQUU7WUFDWixNQUFNLEVBQUUsS0FBSyxDQUFDLE1BQU07U0FDcEIsQ0FBQztJQUNILENBQUM7SUFFZ0Isa0JBQWtCLEdBQUcsQ0FBQyxDQUF1QyxFQUFFLEVBQUU7UUFDakYsTUFBTSxLQUFLLEdBQUcsQ0FBQyxDQUFDLGFBQWEsQ0FBQyxLQUFLLENBQUM7UUFDcEMsQ0FBQyxDQUFDLGNBQWMsRUFBRSxDQUFDO1FBQ25CLElBQUksS0FBSyxDQUFDLFVBQVUsQ0FBQyxTQUFTLENBQUMsRUFBRTtZQUNoQyxJQUFJLENBQUMsUUFBUSxDQUFDO2dCQUNiLGNBQWMsRUFBRSxRQUFRLENBQUMsS0FBSyxDQUFDLFNBQVMsQ0FBQyxTQUFTLENBQUMsTUFBTSxDQUFDLENBQUM7YUFDM0QsQ0FBQyxDQUFBO1NBQ0Y7YUFBTTtZQUNOLElBQUksQ0FBQyxRQUFRLENBQUMsQ0FBQyxFQUFFLE1BQU0sRUFBRSxFQUFFLEVBQUUsQ0FBQyxDQUFDO2dCQUM5QixjQUFjLEVBQUUsQ0FBQyxNQUFNLEVBQUUsT0FBTyxDQUFDLE1BQU0sSUFBSSxDQUFDLENBQUM7Z0JBQzdDLE1BQU0sRUFBRTtvQkFDUCxH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