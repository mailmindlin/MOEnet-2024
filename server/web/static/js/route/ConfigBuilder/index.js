import React from 'react';
import Loading from '../../components/Loading';
import SelectorForm, { CameraFilterEditor, PoseEditor } from './camera';
import PipelineStages from './stages';
import NetworkTablesEditor from './nt';
import { BoundList, BoundTextInput } from './bound';
import LogConfigEditor from './logging';
import DatalogConfigEdtior from './datalog';
import WebConfigEditor from './web';
import EstimatorConfigEditor from './estimator';
import { boundReplaceKey, boundUpdateKey } from './ds';
import Collapsible from '../../components/Collapsible';
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
    setCameraSelectors = (selectors) => {
        this.setState(({ config }) => ({
            config: {
                ...config,
                camera_selectors: selectors
            }
        }));
    };
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
    renderCameraTemplate = ({ item, onChange, onDelete }) => (React.createElement(CameraFilterEditor, { legend: React.createElement(BoundTextInput, { value: item, name: 'id', label: 'Selector', onChange: onChange, placeholder: 'Selector name' }), templates: this.props.camera_templates, selector: item, definitions: [] /* This could get recursive */, onChange: onChange, onDelete: onDelete }));
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
                React.createElement(BoundList, { value: this.state.config.camera_selectors ?? [], onChange: this.setCameraSelectors, canDelete: true, renderItem: this.renderCameraTemplate }),
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
                    React.createElement(SelectorForm, { templates: this.props.camera_templates, definitions: this.state.config.camera_selectors, selector: selector, onChange: this.handleSelectorChange }),
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
        return (React.createElement(ConfigBuilderInner, { camera_templates: this.state.cameras, schema: this.state.schema, config: this.state.config }));
    }
}
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiaW5kZXguanMiLCJzb3VyY2VSb290IjoiIiwic291cmNlcyI6WyIuLi8uLi8uLi90cy9yb3V0ZS9Db25maWdCdWlsZGVyL2luZGV4LnRzeCJdLCJuYW1lcyI6W10sIm1hcHBpbmdzIjoiQUFBQSxPQUFPLEtBQXNCLE1BQU0sT0FBTyxDQUFDO0FBRzNDLE9BQU8sT0FBTyxNQUFNLDBCQUEwQixDQUFDO0FBQy9DLE9BQU8sWUFBWSxFQUFFLEVBQUUsa0JBQWtCLEVBQUUsVUFBVSxFQUFFLE1BQU0sVUFBVSxDQUFDO0FBQ3hFLE9BQU8sY0FBYyxNQUFNLFVBQVUsQ0FBQztBQUV0QyxPQUFPLG1CQUFtQixNQUFNLE1BQU0sQ0FBQztBQUN2QyxPQUFPLEVBQUUsU0FBUyxFQUE0QixjQUFjLEVBQUUsTUFBTSxTQUFTLENBQUM7QUFDOUUsT0FBTyxlQUFlLE1BQU0sV0FBVyxDQUFDO0FBQ3hDLE9BQU8sbUJBQW1CLE1BQU0sV0FBVyxDQUFDO0FBQzVDLE9BQU8sZUFBZSxNQUFNLE9BQU8sQ0FBQztBQUNwQyxPQUFPLHFCQUFxQixNQUFNLGFBQWEsQ0FBQztBQUNoRCxPQUFPLEVBQUUsZUFBZSxFQUFFLGNBQWMsRUFBRSxNQUFNLE1BQU0sQ0FBQztBQUN2RCxPQUFPLFdBQVcsTUFBTSw4QkFBOEIsQ0FBQztBQWtDdkQsTUFBTSxrQkFBbUIsU0FBUSxLQUFLLENBQUMsU0FBaUM7SUFDdkUsWUFBWSxLQUFpQjtRQUM1QixLQUFLLENBQUMsS0FBSyxDQUFDLENBQUM7UUFDYixJQUFJLENBQUMsS0FBSyxHQUFHO1lBQ1osY0FBYyxFQUFFLENBQUM7WUFDakIsTUFBTSxFQUFFLEtBQUssQ0FBQyxNQUFNO1NBQ3BCLENBQUM7SUFDSCxDQUFDO0lBRWdCLGtCQUFrQixHQUFHLENBQUMsQ0FBdUMsRUFBRSxFQUFFO1FBQ2pGLE1BQU0sS0FBSyxHQUFHLENBQUMsQ0FBQyxhQUFhLENBQUMsS0FBSyxDQUFDO1FBQ3BDLENBQUMsQ0FBQyxjQUFjLEVBQUUsQ0FBQztRQUNuQixJQUFJLEtB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