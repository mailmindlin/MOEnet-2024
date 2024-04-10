import React from 'react';
import Loading from '../../components/Loading';
import SelectorForm, { CameraSelector, PoseEditor } from './camera';
import PipelineStages from './stages';
import NetworkTablesEditor from './nt';
import { BoundTextInput, Collapsible } from './bound';
import LogConfigEditor from './logging';
import DatalogConfigEdtior from './datalog';
import WebConfigEditor from './web';
import EstimatorConfigEditor from './estimator';
import { boundReplaceKey, boundUpdateIdx, boundUpdateKey } from './ds';
class ConfigBuilderInner extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            selectedCamera: 0,
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
            // New camera
            this.setState(({ config }) => ({
                selectedCamera: (config?.cameras?.length ?? 1),
                config: {
                    ...(config),
                    cameras: [
                        ...(config.cameras ?? []),
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
    };
    addCameraSelector = () => {
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
        }));
    };
    deleteCameraSelector(index) {
        this.setState(({ config }) => ({
            config: {
                ...config,
                camera_selectors: [
                    ...(config.camera_selectors ?? []).slice(0, index),
                    ...(config.camera_selectors ?? []).slice(index + 1),
                ]
            }
        }));
    }
    addPipelineTemplate = () => {
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
        }));
    };
    updatePipelineTemplate(index, update) {
        this.setState(({ config }) => {
            const result = {
                ...config,
                pipelines: [
                    ...(config.pipelines ?? [])
                ]
            };
            if (result.pipelines[index].id !== update.id) {
                // Update dependencies
                const prevId = result.pipelines[index].id;
                function updateStages(stages) {
                    return stages.map(stage => {
                        if (stage.stage === 'inherit' && stage.id === prevId) {
                            return {
                                ...stage,
                                id: update.id,
                            };
                        }
                        return stage;
                    });
                }
                function updateCamera(camera) {
                    if (camera.pipeline === prevId) {
                        return {
                            ...camera,
                            pipeline: update.id,
                        };
                    }
                    else if (typeof camera.pipeline !== 'string' && camera.pipeline) {
                        return {
                            ...camera,
                            pipeline: updateStages(camera.pipeline),
                        };
                    }
                    else {
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
            return { config: result };
        });
    }
    deletePipelineTemplate(index) {
        this.setState(({ config }) => ({
            config: {
                ...config,
                pipelines: [
                    ...(config.pipelines ?? []).slice(0, index),
                    ...(config.pipelines ?? []).slice(index + 1),
                ]
            }
        }));
    }
    updateCurrent(cb) {
        this.setState(({ config, selectedCamera }) => ({
            config: {
                ...config,
                cameras: (config.cameras?.length ?? 0 <= selectedCamera)
                    ? (config.cameras ?? []).map((config, i) => (i == selectedCamera) ? cb(config) : config)
                    : [...(config.cameras ?? []), cb({})]
            }
        }), () => console.log(this.state));
    }
    handleSelectorChange = (value) => {
        console.log('selector change', value);
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
    getCurrentSelector() {
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
        let pipeline;
        if (typeof currentCameraConfig.pipeline == 'string') {
            const pipelines = this.state.config.pipelines;
            if (pipelines)
                pipeline = pipelines.find(p1 => p1.id == currentCameraConfig.pipeline)?.stages ?? [];
            else
                pipeline = [];
        }
        else {
            pipeline = currentCameraConfig.pipeline ?? [];
        }
        return [currentCameraConfig, pipeline, selector];
    }
    handleSubpropChange(key) {
        return (value) => {
            this.setState(({ config }) => ({
                config: {
                    ...config,
                    [key]: value,
                },
            }));
        };
    }
    handleNtChange = this.handleSubpropChange('nt');
    handleLogChange = this.handleSubpropChange('log');
    handleDatalogChange = this.handleSubpropChange('datalog');
    handleEstimatorChange = this.handleSubpropChange('estimator');
    handleWebChange = this.handleSubpropChange('web');
    downloadJson = async () => {
        const text = JSON.stringify(this.state.config, undefined, '\t');
        try {
            const handle = await window.showSaveFilePicker({
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
        }
        catch (e) {
            console.log(e);
            var element = document.createElement('a');
            element.setAttribute('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(text));
            element.setAttribute('download', 'moenet-config.json');
            element.style.display = 'none';
            document.body.appendChild(element);
            element.click();
            document.body.removeChild(element);
        }
    };
    render() {
        const updateConfig = boundUpdateKey('config', (cb) => this.setState(cb));
        const [currentCameraConfig, pipeline, selector] = this.getCurrentSelector();
        const cameras = this.state.config.cameras ?? [];
        console.log(this.state, selector);
        return (React.createElement("div", { style: { "padding": 10 } },
            React.createElement("button", { onClick: this.downloadJson }, "Download JSON"),
            React.createElement(NetworkTablesEditor, { nt: this.state.config.nt, onChange: this.handleNtChange }),
            React.createElement(LogConfigEditor, { config: this.state.config.log, onChange: this.handleLogChange }),
            React.createElement(DatalogConfigEdtior, { config: this.state.config.datalog, onChange: this.handleDatalogChange }),
            React.createElement(EstimatorConfigEditor, { config: this.state.config.estimator, onChange: this.handleEstimatorChange }),
            React.createElement(WebConfigEditor, { config: this.state.config.web, onChange: this.handleWebChange }),
            React.createElement(Collapsible, { legend: "Camera Templates" },
                (this.state.config.camera_selectors ?? []).map((selector, idx) => {
                    const onChange = boundUpdateIdx(idx, boundUpdateKey('camera_selectors', updateConfig, []));
                    return React.createElement(CameraSelector, { key: idx, legend: React.createElement(BoundTextInput, { value: selector, name: 'id', label: 'Selector', onChange: onChange, placeholder: 'Selector name' }), cameras: this.props.cameras, selector: selector, definitions: [], onChange: onChange, onDelete: this.deleteCameraSelector.bind(this, idx) });
                }),
                React.createElement("button", { onClick: this.addCameraSelector }, "Add new")),
            React.createElement(Collapsible, { legend: "Pipeline Templates" },
                (this.state.config.pipelines ?? []).map((pipeline, idx) => {
                    const onChange = this.updatePipelineTemplate.bind(this, idx);
                    const onChangeInner = (stages) => onChange({ id: pipeline.id, stages });
                    return React.createElement(PipelineStages, { key: idx, legend: React.createElement(BoundTextInput, { value: pipeline, name: 'id', label: 'Pipeline', onChange: onChange, placeholder: 'Pipeline name' }), config: this.state.config, stages: pipeline.stages, onChange: onChangeInner, onDelete: this.deletePipelineTemplate.bind(this, idx) });
                }),
                React.createElement("button", { onClick: this.addPipelineTemplate }, "Add new")),
            React.createElement("fieldset", null,
                React.createElement("legend", null,
                    React.createElement("label", { htmlFor: "cameras" }, "Camera\u00A0"),
                    React.createElement("select", { id: "cameras", onChange: this.handleCameraChange, value: `camera-${this.state.selectedCamera}` },
                        cameras.length == 0 && React.createElement("option", { key: "-" }, "Select Camera"),
                        cameras.map((camera, i) => (React.createElement("option", { key: i, value: `camera-${i}` },
                            "Camera ",
                            i))),
                        React.createElement("option", { key: "new", value: "new" }, "New Camera..."))),
                selector && React.createElement(React.Fragment, null,
                    React.createElement(SelectorForm, { cameras: this.props.cameras, selector: selector ?? {}, definitions: this.state.config.camera_selectors, onChange: this.handleSelectorChange }),
                    React.createElement(PipelineStages, { legend: React.createElement("select", { value: typeof currentCameraConfig.pipeline === 'string' ? currentCameraConfig.pipeline : '$custom', onChange: e => this.handlePipelineChange(e.currentTarget.selectedIndex === 0 ? [] : e.currentTarget.value) },
                            React.createElement("option", { value: '$custom' }, "Custom"),
                            (this.state.config.pipelines ?? []).map(definition => React.createElement("option", { id: definition.id, value: definition.id },
                                "Template ",
                                definition.id))), config: this.state.config, stages: pipeline ?? [], onChange: typeof currentCameraConfig?.pipeline === 'string' ? undefined : this.handlePipelineChange }),
                    React.createElement("fieldset", null,
                        React.createElement("legend", null, "Config"),
                        React.createElement(PoseEditor, { value: currentCameraConfig?.pose, onChange: boundReplaceKey('pose', currentCameraConfig, s => this.updateCurrent(c => s)) }))))));
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
            schema: null,
            cancel: new AbortController(),
        };
    }
    componentDidMount() {
        this.fetchConfig();
        this.fetchCameras();
        this.fetchSchema();
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
        console.log('fetch config');
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
    async fetchSchema() {
        try {
            const res = await fetch('/api/schema', {
                signal: this.state.cancel.signal,
                headers: { 'Content-Type': 'application/json' }
            });
            var data = await res.json();
        }
        catch {
            console.error('No schema');
            return;
        }
        this.setState({
            schema: data
        });
    }
    render() {
        if (this.state.config === null || this.state.cameras === null || this.state.schema === null)
            return React.createElement(Loading, null);
        return (React.createElement(ConfigBuilderInner, { cameras: this.state.cameras, schema: this.state.schema, config: this.state.config }));
    }
}
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiaW5kZXguanMiLCJzb3VyY2VSb290IjoiIiwic291cmNlcyI6WyIuLi8uLi8uLi90cy9yb3V0ZS9Db25maWdCdWlsZGVyL2luZGV4LnRzeCJdLCJuYW1lcyI6W10sIm1hcHBpbmdzIjoiQUFBQSxPQUFPLEtBQWlDLE1BQU0sT0FBTyxDQUFDO0FBR3RELE9BQU8sT0FBTyxNQUFNLDBCQUEwQixDQUFDO0FBQy9DLE9BQU8sWUFBWSxFQUFFLEVBQUUsY0FBYyxFQUFFLFVBQVUsRUFBRSxNQUFNLFVBQVUsQ0FBQztBQUNwRSxPQUFPLGNBQWMsTUFBTSxVQUFVLENBQUM7QUFFdEMsT0FBTyxtQkFBbUIsTUFBTSxNQUFNLENBQUM7QUFDdkMsT0FBTyxFQUFFLGNBQWMsRUFBRSxXQUFXLEVBQXFCLE1BQU0sU0FBUyxDQUFDO0FBQ3pFLE9BQU8sZUFBZSxNQUFNLFdBQVcsQ0FBQztBQUN4QyxPQUFPLG1CQUFtQixNQUFNLFdBQVcsQ0FBQztBQUM1QyxPQUFPLGVBQWUsTUFBTSxPQUFPLENBQUM7QUFDcEMsT0FBTyxxQkFBcUIsTUFBTSxhQUFhLENBQUM7QUFDaEQsT0FBTyxFQUFFLGVBQWUsRUFBRSxjQUFjLEVBQUUsY0FBYyxFQUFFLE1BQU0sTUFBTSxDQUFDO0FBa0N2RSxNQUFNLGtCQUFtQixTQUFRLEtBQUssQ0FBQyxTQUFpQztJQUN2RSxZQUFZLEtBQWlCO1FBQzVCLEtBQUssQ0FBQyxLQUFLLENBQUMsQ0FBQztRQUNiLElBQUksQ0FBQyxLQUFLLEdBQUc7WUFDWixjQUFjLEVBQUUsQ0FBQztZQUNqQixNQUFNLEVBQUUsS0FBSyxDQUFDLE1BQU07U0FDcEIsQ0FBQztJQUNILENBQUM7SUFFZ0Isa0JBQWtCLEdBQUcsQ0FBQyxDQUF1QyxFQUFFLEVBQUU7UUFDakYsTUFBTSxLQUFLLEdBQUcsQ0FBQyxDQUFDLGFBQWEsQ0FBQyxLQUFLLENBQUM7UUFDcEMsQ0FBQyxDQUFDLGNBQWMsRUFBRSxDQUFDO1FBQ25CLElBQUksS0FBSyxDQUFDLFVBQVUsQ0FBQyxTQUFTLENB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