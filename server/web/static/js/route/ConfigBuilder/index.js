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
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiaW5kZXguanMiLCJzb3VyY2VSb290IjoiIiwic291cmNlcyI6WyIuLi8uLi8uLi90cy9yb3V0ZS9Db25maWdCdWlsZGVyL2luZGV4LnRzeCJdLCJuYW1lcyI6W10sIm1hcHBpbmdzIjoiQUFBQSxPQUFPLEtBQWlDLE1BQU0sT0FBTyxDQUFDO0FBR3RELE9BQU8sT0FBTyxNQUFNLDBCQUEwQixDQUFDO0FBQy9DLE9BQU8sWUFBWSxNQUFNLGdCQUFnQixDQUFDO0FBQzFDLE9BQU8sY0FBYyxNQUFNLFVBQVUsQ0FBQztBQXlCdEMsTUFBTSxrQkFBbUIsU0FBUSxLQUFLLENBQUMsU0FBaUM7SUFDdkUsWUFBWSxLQUFpQjtRQUM1QixLQUFLLENBQUMsS0FBSyxDQUFDLENBQUM7UUFDYixJQUFJLENBQUMsS0FBSyxHQUFHO1lBQ1osY0FBYyxFQUFFLENBQUM7WUFDakIsUUFBUSxFQUFFLEVBQUU7WUFDWixNQUFNLEVBQUUsS0FBSyxDQUFDLE1BQU07U0FDcEIsQ0FBQztJQUNILENBQUM7SUFFZ0Isa0JBQWtCLEdBQUcsQ0FBQyxDQUF1QyxFQUFFLEVBQUU7UUFDakYsTUFBTSxLQUFLLEdBQUcsQ0FBQyxDQUFDLGFBQWEsQ0FBQyxLQUFLLENBQUM7UUFDcEMsQ0FBQyxDQUFDLGNBQWMsRUFBRSxDQUFDO1FBQ25CLElBQUksS0FBSyxDQUFDLFVBQVUsQ0FBQyxTQUFTLENBQUMsRUFBRSxDQUFDO1lBQ2pDLElBQUksQ0FBQyxRQUFRLENBQUM7Z0JBQ2IsY0FBYyxFQUFFLFFBQVEsQ0FBQyxLQUFLLENBQUMsU0FBUyxDQUFDLFNBQVMsQ0FBQyxNQUFNLENBQUMsQ0FBQzthQUMzRCxDQUFDLENBQUE7UUFDSCxDQUFDO2FBQU0sQ0FBQztZQUNQLElBQUksQ0FBQyxRQUFRLENBQUMsQ0FBQyxFQUFFLE1BQU0sRUFBRSxFQUFFLEVBQUUsQ0FBQyxDQUFDO2dCQUM5QixjQUFjLEVBQUUsQ0FBQyxNQUFNLEVBQUUsT0FBTyxDQUFDLE1BQU0sSUFBSSxDQUFDLENBQUM7Z0JBQzdDLE1B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