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
import { boundReplaceKey } from './ds';
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
                        cameras.map((_camera, i) => (React.createElement("option", { key: i, value: `camera-${i}` },
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
                        React.createElement(PoseEditor, { value: currentCameraConfig?.pose, onChange: boundReplaceKey('pose', currentCameraConfig, s => this.updateCurrent(_ => s)) }))))));
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
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiaW5kZXguanMiLCJzb3VyY2VSb290IjoiIiwic291cmNlcyI6WyIuLi8uLi8uLi90cy9yb3V0ZS9Db25maWdCdWlsZGVyL2luZGV4LnRzeCJdLCJuYW1lcyI6W10sIm1hcHBpbmdzIjoiQUFBQSxPQUFPLEtBQUssTUFBTSxPQUFPLENBQUM7QUFHMUIsT0FBTyxPQUFPLE1BQU0sMEJBQTBCLENBQUM7QUFDL0MsT0FBTyxZQUFZLEVBQUUsRUFBRSxrQkFBa0IsRUFBRSxVQUFVLEVBQUUsTUFBTSxVQUFVLENBQUM7QUFDeEUsT0FBTyxjQUFjLE1BQU0sVUFBVSxDQUFDO0FBRXRDLE9BQU8sbUJBQW1CLE1BQU0sTUFBTSxDQUFDO0FBQ3ZDLE9BQU8sRUFBRSxTQUFTLEVBQTRCLGNBQWMsRUFBRSxNQUFNLFNBQVMsQ0FBQztBQUM5RSxPQUFPLGVBQWUsTUFBTSxXQUFXLENBQUM7QUFDeEMsT0FBTyxtQkFBbUIsTUFBTSxXQUFXLENBQUM7QUFDNUMsT0FBTyxlQUFlLE1BQU0sT0FBTyxDQUFDO0FBQ3BDLE9BQU8scUJBQXFCLE1BQU0sYUFBYSxDQUFDO0FBQ2hELE9BQU8sRUFBRSxlQUFlLEVBQUUsTUFBTSxNQUFNLENBQUM7QUFDdkMsT0FBTyxXQUFXLE1BQU0sOEJBQThCLENBQUM7QUFrQ3ZELE1BQU0sa0JBQW1CLFNBQVEsS0FBSyxDQUFDLFNBQWlDO0lBQ3ZFLFlBQVksS0FBaUI7UUFDNUIsS0FBSyxDQUFDLEtBQUssQ0FBQyxDQUFDO1FBQ2IsSUFBSSxDQUFDLEtBQUssR0FBRztZQUNaLGNBQWMsRUFBRSxDQUFDO1lBQ2pCLE1BQU0sRUFBRSxLQUFLLENBQUMsTUFBTTtTQUNwQixDQUFDO0lBQ0gsQ0FBQztJQUVnQixrQkFBa0IsR0FBRyxDQUFDLENBQXVDLEVBQUUsRUFBRTtRQUNqRixNQUFNLEtBQUssR0FBRyxDQUFDLENBQUMsYUFBYSxDQUFDLEtBQUssQ0FBQztRQUNwQyxDQUFDLENBQUMsY0FBYyxFQUFFLENBQUM7UUFDbkIsSUFBSSxLQUFLLENBQUMsVUFBVSxDQUFDLFNBQVMsQ0FBQyxFQUFFLENBQUM7WUFDakMsSUFBSSxDQUFDLFFBQVEsQ0FBQztnQkFDYixjQUFjLEVBQUUsUUFBUSxDQUFDLEtBQUssQ0FBQyxTQUFTLENBQUMsU0FBUyxDQUFDLE1BQU0sQ0FBQyxDQUFDO2FBQzNELENBQUMsQ0FBQTtRQUNILENBQUM7YUFBTSxDQUFDO1lBQ1AsYUFBYTtZQUNiLElBQUksQ0FBQyxRQUFRLENBQUMsQ0FBQyxFQUFFLE1BQU0sRUFBRSxFQUFFLEVBQUUsQ0FBQyxDQUFDO2dCQUM5QixjQUFjLEVBQUUsQ0FBQyxNQUFNLEVBQUUsT0FBTyxFQUFFLE1BQU0sSUFBSSxDQUFDLENBQUM7Z0JBQzlDLE1BQU0sRUFBRTtvQkFDUCxHQUFHLENBQUMsTUFBTyxDQUFDO29CQUNaLE9BQU8sRUFBRTt3QkFDUixHQUFHLENBQUMsTUFBTyxDQUFDLE9BQU8sSUFBSSxFQUFFLENBQUM7d0JBQzFCOzRCQUNDLFFBQVEsRUFBRSxFQUFFOzRCQUNaLElBQUksRUFBRTtnQ0FDTCxVQUFVLEVBQUU7b0NBQ1gsWUFBWSxFQUFFO3dDQUNiLEdBQUcsRUFBRSxDQUFDLEVBQUUsR0FBRyxFQUFFLENBQUMsRUFBRSxHQUFHLEVBQUUsQ0FBQyxFQUFFLEdBQUcsRUFBRSxDQUFDO3FDQUM5QjtpQ0FDRDtnQ0FDRCxhQUFhLEVBQUU7b0NBQ2QsR0FBRyxFQUFFLENBQUM7b0NBQ04sR0FBRyxFQUFFLENBQUM7b0NBQ04sR0FBRyxFQUFFLENBQUM7aUNBQ047NkJBQ0Q7eUJBQ0Q7cUJBQ0Q7aUJBQ0Q7YUFDRCxDQUFDLENBQUMsQ0FBQztRQUNMLENBQUM7SUFDRixDQUFDLENBQUE7SUFFZ0IsaUJBQWlCLEdBQUcsR0FBRyxFQUFFO1FBQ3pDLElBQUksQ0FBQyxRQUFRLENBQUMsQ0FBQyxFQUFFLE1BQU0sRUFBRSxFQUFFLEVBQUUsQ0FBQyxDQUFDO1lBQzlCLE1BQU0sRUFBRTtnQkFDUCxHQUFHLE1BQU07Z0JBQ1QsZ0JBQWdCLEVBQUU7b0JBQ2pCLEdBQUcsQ0FBQyxNQUFNLENBQUMsZ0JBQWdCLElBQUksRUFBRSxDQUFDO29CQUNsQzt3QkFDQyxFQUFFLEVBQUUsRUFBRTtxQkFDTjtpQkFDRDthQUNEO1NBQ0QsQ0FBQyxDQUFDLENBQUE7SUFDSixDQUFDLENBQUE7SUFFZ0Isa0JBQWtCLEdBQUcsQ0FBQyxTQUFxQyxFQUFFLEVBQUU7UUFDL0UsSUFBSSxDQUFDLFFBQVEsQ0FBQyxDQUFDLEVBQUUsTUFBTSxFQUFFLEVBQUUsRUFBRSxDQUFDLENBQUM7WUFDOUIsTUFBTSxFQUFFO2dCQUNQLEdBQUcsTUFBTTtnQkFDVCxnQkFBZ0IsRUFBRSxTQUFTO2FBQzNCO1NBQ0QsQ0FBQyxDQUFDLENBQUE7SUFDSixDQUFDLENBQUE7SUFFZ0IsbUJBQW1CLEdBQUcsR0FBRyxFQUFFO1FBQzNDLElBQUksQ0FBQyxRQUFRLENBQUMsQ0FBQyxFQUFFLE1BQU0sRUFBRSxFQUFFLEVBQUUsQ0FBQyxDQUFDO1lBQzlCLE1BQU0sRUFBRTtnQkFDUCxHQUFHLE1BQU07Z0JBQ1QsU0FBUyxFQUFFO29CQUNWLEdBQUcsQ0FBQyxNQUFNLENBQUMsU0FBUyxJQUFJLEVBQUUsQ0FBQztvQkFDM0I7d0JBQ0MsRUFBRSxFQUFFLEVBQUU7d0JBQ04sTUFBTSxFQUFFLEVBQUU7cUJBQ1Y7aUJBQ0Q7YUFDRDtTQUNELENBQUMsQ0FBQyxDQUFBO0lBQ0osQ0FBQyxDQUFBO0lBR08sc0JBQXNCLENBQUMsS0FBYSxFQUFFLE1BQTBCO1FBQ3ZFLElBQUksQ0FBQyxRQUFRLENBQUMsQ0FBQyxFQUFFLE1BQU0sRUFBRSxFQUFFLEVBQUU7WUFDNUIsTUFBTSxNQUFNLEdBQUc7Z0JBQ2QsR0FBRyxNQUFNO2dCQUNULFNBQVMsRUFBRTtvQkFDVixHQUFHLENBQUMsTUFBTSxDQUFDLFNBQVMsSUFBSSxFQUFFLENBQUM7aUJBQzNCO2FBQ0QsQ0FBQTtZQUVELElBQUksTUFBTSxDQUFDLFNBQVMsQ0FBQyxLQUFLLENBQUMsQ0FBQyxFQUFFLEtBQUssTUFBTSxDQUFDLEVBQUUsRUFBRSxDQUFDO2dCQUM5QyxzQkFBc0I7Z0JBQ3RCLE1BQU0sTUFBTSxHQUFHLE1BQU0sQ0FBQyxTQUFTLENBQUMsS0FBSyxDQUFDLENBQUMsRUFBRSxDQUFDO2dCQUUxQyxTQUFTLFlBQVksQ0FBQyxNQUFzQjtvQkFDM0MsT0FBTyxNQUFNLENBQUMsR0FBRyxDQUFDLEtBQUssQ0FBQyxFQUFFO3dCQUN6QixJQUFJLEtBQUssQ0FBQyxLQUFLLEtBQUssU0FBUyxJQUFJLEtBQUssQ0FBQyxFQUFFLEtBQUssTUFBTSxFQUFFLENBQUM7NEJBQ3RELE9BQU87Z0NBQ04sR0FBRyxLQUFLO2dDQUNSLEVBQUUsRUFBRSxNQUFNLENBQUMsRUFBRTs2QkFDYixDQUFBO3dCQUNGLENBQUM7d0JBQ0QsT0FBTyxLQUFLLENBQUM7b0JBQ2QsQ0FBQyxDQUFDLENBQUE7Z0JBQ0gsQ0FBQztnQkFFRCxTQUFTLFlBQVksQ0FBQyxNQUFvQjtvQkFDekMsSUFBSSxNQUFNLENBQUMsUUFBUSxLQUFLLE1BQU0sRUFBRSxDQUFDO3dCQUNoQyxPQUFPOzRCQUNOLEdBQUcsTUFBTTs0QkFDVCxRQUFRLEVBQUUsTUFBTSxDQUFDLEVBQUU7eUJBQ25CLENBQUE7b0JBQ0YsQ0FBQzt5QkFBTSxJQUFJLE9BQU8sTUFBTSxDQUFDLFFBQVEsS0FBSyxRQUFRLElBQUksTUFBTSxDQUFDLFFBQVEsRUFBRSxDQUFDO3dCQUNuRSxPQUFPOzRCQUNOLEdBQUcsTUFBTTs0QkFDVCxRQUFRLEVBQUUsWUFBWSxDQUFDLE1BQU0sQ0FBQyxRQUFRLENBQUM7eUJBQ3ZDLENBQUE7b0JBQ0YsQ0FBQzt5QkFBTSxDQUFDO3dCQUNQLE9BQU8sTUFBTSxDQUFDO29CQUNmLENBQUM7Z0JBQ0YsQ0FBQztnQkFDRCxNQUFNLENBQUMsU0FBUyxHQUFHLE1BQU0sQ0FBQyxTQUFTLENBQUMsR0FBRyxDQUFDLENBQUMsRUFBRSxFQUFFLEVBQUUsTUFBTSxFQUFFLEVBQUUsRUFBRSxDQUFDLENBQUM7b0JBQzVELEVBQUU7b0JBQ0YsTUFBTSxFQUFFLFlBQVksQ0FBQyxNQUFNLENBQUM7aUJBQzVCLENBQUMsQ0FBQyxDQUFDO2dCQUNKLElBQUksTUFBTSxDQUFDLE9BQU87b0JBQ2pCLE1BQU0sQ0FBQyxPQUFPLEdBQUcsTUFBTSxDQUFDLE9BQU8sQ0FBQyxHQUFHLENBQUMsWUFBWSxDQUFDLENBQUM7WUFDcEQsQ0FBQztZQUNELE1BQU0sQ0FBQyxTQUFTLENBQUMsS0FBSyxDQUFDLEdBQUcsTUFBTSxDQUFDO1lBQ2pDLE9BQU8sRUFBRSxNQUFNLEVBQUUsTUFBTSxFQUFFLENBQUE7UUFDMUIsQ0FBQyxDQUFDLENBQUE7SUFDSCxDQUFDO0lBRU8sc0JBQXNCLENBQUMsS0FBYTtRQUMzQyxJQUFJLENBQUMsUUFBUSxDQUFDLENBQUMsRUFBRSxNQUFNLEVBQUUsRUFBRSxFQUFFLENBQUMsQ0FBQztZQUM5QixNQUFNLEVBQUU7Z0JBQ1AsR0FBRyxNQUFNO2dCQUNULFNBQVMsRUFBRTtvQkFDVixHQUFHLENBQUMsTUFBTSxDQUFDLFNBQVMsSUFBSSxFQUFFLENBQUMsQ0FBQyxLQUFLLENBQUMsQ0FBQyxFQUFFLEtBQUssQ0FBQztvQkFDM0MsR0FBRyxDQUFDLE1BQU0sQ0FBQyxTQUFTLElBQUksRUFBRSxDQUFDLENBQUMsS0FBSyxDQUFDLEtBQUssR0FBRyxDQUFDLENBQUM7aUJBQzVDO2FBQ0Q7U0FDRCxDQUFDLENBQUMsQ0FBQTtJQUNKLENBQUM7SUFFTyxhQUFhLENBQUMsRUFBMkM7UUFDaEUsSUFBSSxDQUFDLFFBQVEsQ0FBQyxDQUFDLEVBQUMsTUFBTSxFQUFFLGNBQWMsRUFBRSxFQUFFLEVBQUUsQ0FBQyxDQUFDO1lBQzdDLE1BQU0sRUFBRTtnQkFDUCxHQUFHLE1BQU07Z0JBQ1QsT0FBTyxFQUFFLENBQUMsTUFBTSxDQUFDLE9BQU8sRUFBRSxNQUFNLElBQUksQ0FBQyxJQUFJLGNBQWMsQ0FBQztvQkFDdkQsQ0FBQyxDQUFDLENBQUMsTUFBTSxDQUFDLE9BQU8sSUFBSSxFQUFFLENBQUMsQ0FBQyxHQUFHLENBQUMsQ0FBQyxNQUFNLEVBQUUsQ0FBQyxFQUFFLEVBQUUsQ0FBQyxDQUFDLENBQUMsSUFBSSxjQUFjLENBQUMsQ0FBQyxDQUFDLENBQUMsRUFBRSxDQUFDLE1BQU0sQ0FBQyxDQUFDLENBQUMsQ0FBQyxNQUFNLENBQUM7b0JBQ3hGLENBQUMsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxNQUFNLENBQUMsT0FBTyxJQUFJLEVBQUUsQ0FBQyxFQUFFLEVBQUUsQ0FBQyxFQUFTLENBQUMsQ0FBQzthQUM3QztTQUNELENBQUMsRUFBRSxHQUFHLEVBQUUsQ0FBQyxPQUFPLENBQUMsR0FBRyxDQUFDLElBQUksQ0FBQyxLQUFLLENBQUMsQ0FBQyxDQUFDO0lBQ3BDLENBQUM7SUFFZ0Isb0JBQW9CLEdBQUcsQ0FBQyxLQUFrQixFQUFFLEVBQUU7UUFDOUQsT0FBTyxDQUFDLEdBQUcsQ0FBQyxpQkFBaUIsRUFBRSxLQUFLLENBQUMsQ0FBQztRQUN0QyxJQUFJLENBQUMsYUFBYSxDQUFDLE1BQU0sQ0FBQyxFQUFFLENBQUMsQ0FBQztZQUM3QixHQUFHLE1BQU07WUFDVCxRQUFRLEVBQUUsS0FBSztTQUNmLENBQUMsQ0FBQyxDQUFDO0lBQ0wsQ0FBQyxDQUFBO0lBRWdCLG9CQUFvQixHQUFHLENBQUMsS0FBOEIsRUFBRSxFQUFFO1FBQzFFLElBQUksQ0FBQyxhQUFhLENBQUMsTUFBTSxDQUFDLEVBQUUsQ0FBQyxDQUFDO1lBQzdCLEdBQUcsTUFBTTtZQUNULFFBQVEsRUFBRSxLQUFLO1NBQ2YsQ0FBQyxDQUFDLENBQUE7SUFDSixDQUFDLENBQUE7SUFFTyxrQkFBa0I7UUFDekIsTUFBTSxtQkFBbUIsR0FBRyxJQUFJLENBQUMsS0FBSyxDQUFDLE1BQU0sQ0FBQyxPQUFPLEVBQUUsQ0FBQyxJQUFJLENBQUMsS0FBSyxDQUFDLGNBQWMsQ0FBQyxDQUFDO1FBQ25GLElBQUksQ0FBQyxtQkFBbUI7WUFDdkIsT0FBTyxDQUFDLFNBQVMsRUFBRSxTQUFTLEVBQUUsU0FBUyxDQUFDLENBQUM7UUFFMUMsSUFBSSxRQUFRLEdBQUcsbUJBQW1CLENBQUMsUUFBUSxDQUFDO1FBRTVDLHNDQUFzQztRQUN0Qyx5REFBeUQ7UUFDekQsa0JBQWtCO1FBQ2xCLDhGQUE4RjtRQUM5RixRQUFRO1FBQ1IseUNBQXlDO1FBQ3pDLElBQUk7UUFFSixJQUFJLFFBQXdCLENBQUM7UUFDN0IsSUFBSSxPQUFPLG1CQUFtQixDQUFDLFFBQVEsSUFBSSxRQUFRLEVBQUUsQ0FBQztZQUNyRCxNQUFNLFNBQVMsR0FBRyxJQUFJLENBQUMsS0FBSyxDQUFDLE1BQU0sQ0FBQyxTQUFTLENBQUM7WUFDOUMsSUFBSSxTQUFTO2dCQUNaLFFBQVEsR0FBRyxTQUFTLENBQUMsSUFBSSxDQUFDLEVBQUUsQ0FBQyxFQUFFLENBQUMsRUFBRSxDQUFDLEVBQUUsSUFBSSxtQkFBbUIsQ0FBQyxRQUFRLENBQUMsRUFBRSxNQUFNLElBQUksRUFBRSxDQUFDOztnQkFFckYsUUFBUSxHQUFHLEVBQUUsQ0FBQztRQUNoQixDQUFDO2FBQU0sQ0FBQztZQUNQLFFBQVEsR0FBRyxtQkFBbUIsQ0FBQyxRQUFRLElBQUksRUFBRSxDQUFDO1FBQy9DLENBQUM7UUFDRCxPQUFPLENBQUMsbUJBQW1CLEVBQUUsUUFBUSxFQUFFLFFBQVEsQ0FBQyxDQUFDO0lBQ2xELENBQUM7SUFFTyxtQkFBbUIsQ0FBOEIsR0FBTTtRQUM5RCxPQUFPLENBQUMsS0FBcUIsRUFBRSxFQUFFO1lBQ2hDLElBQUksQ0FBQyxRQUFRLENBQUMsQ0FBQyxFQUFFLE1BQU0sRUFBRSxFQUFFLEVBQUUsQ0FBQyxDQUFDO2dCQUM5QixNQUFNLEVBQUU7b0JBQ1AsR0FBRyxNQUFNO29CQUNULENBQUMsR0FBRyxDQUFDLEVBQUUsS0FBSztpQkFDWjthQUNELENBQUMsQ0FBQyxDQUFDO1FBQ0wsQ0FBQyxDQUFBO0lBQ0YsQ0FBQztJQUVPLGNBQWMsR0FBRyxJQUFJLENBQUMsbUJBQW1CLENBQUMsSUFBSSxDQUFDLENBQUM7SUFDaEQsZUFBZSxHQUFHLElBQUksQ0FBQyxtQkFBbUIsQ0FBQyxLQUFLLENBQUMsQ0FBQztJQUNsRCxtQkFBbUIsR0FBRyxJQUFJLENBQUMsbUJBQW1CLENBQUMsU0FBUyxDQUFDLENBQUM7SUFDMUQscUJBQXFCLEdBQUcsSUFBSSxDQUFDLG1CQUFtQixDQUFDLFdBQVcsQ0FBQyxDQUFDO0lBQzlELGVBQWUsR0FBRyxJQUFJLENBQUMsbUJBQW1CLENBQUMsS0FBSyxDQUFDLENBQUM7SUFFekMsb0JBQW9CLEdBQUcsQ0FBQyxFQUFFLElBQUksRUFBRSxRQUFRLEVBQUUsUUFBUSxFQUFzRCxFQUFFLEVBQUUsQ0FBQyxDQUM3SCxvQkFBQyxrQkFBa0IsSUFDbEIsTUFBTSxFQUFFLG9CQUFDLGNBQWMsSUFBQyxLQUFLLEVBQUUsSUFBSSxFQUFFLElBQUksRUFBQyxJQUFJLEVBQUMsS0FBSyxFQUFDLFVBQVUsRUFBQyxRQUFRLEVBQUUsUUFBUSxFQUFFLFdBQVcsRUFBQyxlQUFlLEdBQUcsRUFDbEgsU0FBUyxFQUFFLElBQUksQ0FBQyxLQUFLLENBQUMsZ0JBQWdCLEVBQ3RDLFFBQVEsRUFBRSxJQUFJLEVBQ2QsV0FBVyxFQUFFLEVBQUUsQ0FBQyw4QkFBOEIsRUFDOUMsUUFBUSxFQUFFLFFBQVEsRUFDbEIsUUFBUSxFQUFFLFFBQVEsR0FDakIsQ0FDRixDQUFDO0lBRU0sWUFBWSxHQUFHLEtBQUssSUFBSSxFQUFFO1FBQ2pDLE1BQU0sSUFBSSxHQUFHLElBQUksQ0FBQyxTQUFTLENBQUMsSUFBSSxDQUFDLEtBQUssQ0FBQyxNQUFNLEVBQUMsU0FBUyxFQUFFLElBQUksQ0FBQyxDQUFDO1FBQy9ELElBQUksQ0FBQztZQUNKLE1BQU0sTUFBTSxHQUFHLE1BQU8sTUFBYyxDQUFDLGtCQUFrQixDQUFDO2dCQUN2RCxPQUFPLEVBQUUsV0FBVztnQkFDcEIsYUFBYSxFQUFFLG9CQUFvQjtnQkFDbkMsS0FBSyxFQUFFO29CQUNOO3dCQUNDLGFBQWEsRUFBRSxzQkFBc0I7d0JBQ3JDLFFBQVEsRUFBRTs0QkFDVCxrQkFBa0IsRUFBRSxDQUFDLE9BQU8sQ0FBQzt5QkFDN0I7cUJBQ0Q7aUJBQ0Q7YUFDRCxDQUFDLENBQUM7WUFDSCxNQUFNLFFBQVEsR0FBRyxNQUFNLE1BQU0sQ0FBQyxjQUFjLEVBQUUsQ0FBQztZQUMvQyxNQUFNLFFBQVEsQ0FBQyxLQUFLLENBQUMsSUFBSSxDQUFDLENBQUM7WUFDM0IsTUFBTSxRQUFRLENBQUMsS0FBSyxFQUFFLENBQUM7UUFDeEIsQ0FBQztRQUFDLE9BQU8sQ0FBQyxFQUFFLENBQUM7WUFDWixPQUFPLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxDQUFDO1lBQ2YsSUFBSSxPQUFPLEdBQUcsUUFBUSxDQUFDLGFBQWEsQ0FBQyxHQUFHLENBQUMsQ0FBQztZQUMxQyxPQUFPLENBQUMsWUFBWSxDQUFDLE1BQU0sRUFBRSxnQ0FBZ0MsR0FBRyxrQkFBa0IsQ0FBQyxJQUFJLENBQUMsQ0FBQyxDQUFDO1lBQzFGLE9BQU8sQ0FBQyxZQUFZLENBQUMsVUFBVSxFQUFFLG9CQUFvQixDQUFDLENBQUM7WUFFdkQsT0FBTyxDQUFDLEtBQUssQ0FBQyxPQUFPLEdBQUcsTUFBTSxDQUFDO1lBQy9CLFFBQVEsQ0FBQyxJQUFJLENBQUMsV0FBVyxDQUFDLE9BQU8sQ0FBQyxDQUFDO1lBRW5DLE9BQU8sQ0FBQyxLQUFLLEVBQUUsQ0FBQztZQUVoQixRQUFRLENBQUMsSUFBSSxDQUFDLFdBQVcsQ0FBQyxPQUFPLENBQUMsQ0FBQztRQUNwQyxDQUFDO0lBQ0YsQ0FBQyxDQUFBO0lBRVEsTUFBTTtRQUNkLE1BQU0sQ0FBQyxtQkFBbUIsRUFBRSxRQUFRLEVBQUUsUUFBUSxDQUFDLEdBQUcsSUFBSSxDQUFDLGtCQUFrQixFQUFFLENBQUE7UUFDM0UsTUFBTSxPQUFPLEdBQUcsSUFBSSxDQUFDLEtBQUssQ0FBQyxNQUFNLENBQUMsT0FBTyxJQUFJLEVBQUUsQ0FBQztRQUVoRCxPQUFPLENBQUMsR0FBRyxDQUFDLElBQUksQ0FBQyxLQUFLLEVBQUUsUUFBUSxDQUFDLENBQUM7UUFFbEMsT0FBTyxDQUFDLDZCQUFLLEtBQUssRUFBRSxFQUFDLFNBQVMsRUFBRSxFQUFFLEVBQUM7WUFDbEMsZ0NBQVEsT0FBTyxFQUFFLElBQUksQ0FBQyxZQUFZLG9CQUV6QjtZQUNULG9CQUFDLG1CQUFtQixJQUNuQixFQUFFLEVBQUUsSUFBSSxDQUFDLEtBQUssQ0FBQyxNQUFNLENBQUMsRUFBRSxFQUN4QixRQUFRLEVBQUUsSUFBSSxDQUFDLGNBQWMsR0FDNUI7WUFDRixvQkFBQyxlQUFlLElBQ2YsTUFBTSxFQUFFLElBQUksQ0FBQyxLQUFLLENBQUMsTUFBTSxDQUFDLEdBQUcsRUFDN0IsUUFBUSxFQUFFLElBQUksQ0FBQyxlQUFlLEdBQzdCO1lBQ0Ysb0JBQUMsbUJBQW1CLElBQ25CLE1BQU0sRUFBRSxJQUFJLENBQUMsS0FBSyxDQUFDLE1BQU0sQ0FBQyxPQUFPLEVBQ2pDLFFBQVEsRUFBRSxJQUFJLENBQUMsbUJBQW1CLEdBQ2pDO1lBQ0Ysb0JBQUMscUJBQXFCLElBQ3JCLE1BQU0sRUFBRSxJQUFJLENBQUMsS0FBSyxDQUFDLE1BQU0sQ0FBQyxTQUFTLEVBQ25DLFFBQVEsRUFBRSxJQUFJLENBQUMscUJBQXFCLEdBQ25DO1lBQ0Ysb0JBQUMsZUFBZSxJQUNmLE1BQU0sRUFBRSxJQUFJLENBQUMsS0FBSyxDQUFDLE1BQU0sQ0FBQyxHQUFHLEVBQzdCLFFBQVEsRUFBRSxJQUFJLENBQUMsZUFBZSxHQUM3QjtZQUNGLG9CQUFDLFdBQVcsSUFBQyxNQUFNLEVBQUMsa0JBQWtCO2dCQUNyQyxvQkFBQyxTQUFTLElBQ1QsS0FBSyxFQUFFLElBQUksQ0FBQyxLQUFLLENBQUMsTUFBTSxDQUFDLGdCQUFnQixJQUFJLEVBQUUsRUFDL0MsUUFBUSxFQUFFLElBQUksQ0FBQyxrQkFBa0IsRUFDakMsU0FBUyxRQUNULFVBQVUsRUFBRSxJQUFJLENBQUMsb0JBQW9CLEdBQ3BDO2dCQUNGLGdDQUFRLE9BQU8sRUFBRSxJQUFJLENBQUMsaUJBQWlCLGNBQWtCLENBQzVDO1lBQ2Qsb0JBQUMsV0FBVyxJQUFDLE1BQU0sRUFBQyxvQkFBb0I7Z0JBQ3RDLENBQUMsSUFBSSxDQUFDLEtBQUssQ0FBQyxNQUFNLENBQUMsU0FBUyxJQUFJLEVBQUUsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxDQUFDLFFBQVEsRUFBRSxHQUFHLEVBQUUsRUFBRTtvQkFDMUQsTUFBTSxRQUFRLEdBQUcsSUFBSSxDQUFDLHNCQUFzQixDQUFDLElBQUksQ0FBQyxJQUFJLEVBQUUsR0FBRyxDQUFDLENBQUM7b0JBQzdELE1BQU0sYUFBYSxHQUFHLENBQUMsTUFBc0IsRUFBRSxFQUFFLENBQUMsUUFBUSxDQUFDLEVBQUUsRUFBRSxFQUFFLFFBQVEsQ0FBQyxFQUFFLEVBQUUsTUFBTSxFQUFFLENBQUMsQ0FBQztvQkFDeEYsT0FBTyxvQkFBQyxjQUFjLElBQ3JCLEdBQUcsRUFBRSxHQUFHLEVBQ1IsTUFBTSxFQUFFLG9CQUFDLGNBQWMsSUFBQyxLQUFLLEVBQUUsUUFBUSxFQUFFLElBQUksRUFBQyxJQUFJLEVBQUMsS0FBSyxFQUFDLFVBQVUsRUFBQyxRQUFRLEVBQUUsUUFBUSxFQUFFLFdBQVcsRUFBQyxlQUFlLEdBQUcsRUFDdEgsTUFBTSxFQUFFLElBQUksQ0FBQyxLQUFLLENBQUMsTUFBTSxFQUN6QixNQUFNLEVBQUUsUUFBUSxDQUFDLE1BQU0sRUFDdkIsUUFBUSxFQUFFLGFBQWEsRUFDdkIsUUFBUSxFQUFFLElBQUksQ0FBQyxzQkFBc0IsQ0FBQyxJQUFJLENBQUMsSUFBSSxFQUFFLEdBQUcsQ0FBQyxHQUNwRCxDQUFDO2dCQUNKLENBQUMsQ0FBQztnQkFDRixnQ0FBUSxPQUFPLEVBQUUsSUFBSSxDQUFDLG1CQUFtQixjQUFrQixDQUM5QztZQUNkO2dCQUNDO29CQUNDLCtCQUFPLE9BQU8sRUFBQyxTQUFTLG1CQUFxQjtvQkFDN0MsZ0NBQVEsRUFBRSxFQUFDLFNBQVMsRUFBQyxRQUFRLEVBQUUsSUFBSSxDQUFDLGtCQUFrQixFQUFFLEtBQUssRUFBRSxVQUFVLElBQUksQ0FBQyxLQUFLLENBQUMsY0FBYyxFQUFFO3dCQUNsRyxPQUFPLENBQUMsTUFBTSxJQUFJLENBQUMsSUFBSSxnQ0FBUSxHQUFHLEVBQUMsR0FBRyxvQkFBdUI7d0JBRTdELE9BQU8sQ0FBQyxHQUFHLENBQUMsQ0FBQyxPQUFPLEVBQUUsQ0FBQyxFQUFFLEVBQUUsQ0FBQyxDQUM1QixnQ0FBUSxHQUFHLEVBQUUsQ0FBQyxFQUFFLEtBQUssRUFBRSxVQUFVLENBQUMsRUFBRTs7NEJBQVUsQ0FBQyxDQUFVLENBQ3pELENBQUM7d0JBQ0YsZ0NBQVEsR0FBRyxFQUFDLEtBQUssRUFBQyxLQUFLLEVBQUMsS0FBSyxvQkFBdUIsQ0FDNUMsQ0FDRDtnQkFDUCxRQUFRLElBQUk7b0JBQ2Isb0JBQUMsWUFBWSxJQUNaLFNBQVMsRUFBRSxJQUFJLENBQUMsS0FBSyxDQUFDLGdCQUFnQixFQUN0QyxXQUFXLEVBQUUsSUFBSSxDQUFDLEtBQUssQ0FBQyxNQUFNLENBQUMsZ0JBQWdCLEVBQy9DLFFBQVEsRUFBRSxRQUFRLEVBQ2xCLFFBQVEsRUFBRSxJQUFJLENBQUMsb0JBQW9CLEdBQ2xDO29CQUNGLG9CQUFDLGNBQWMsSUFDZCxNQUFNLEVBQ0wsZ0NBQ0MsS0FBSyxFQUFFLE9BQU8sbUJBQW9CLENBQUMsUUFBUSxLQUFLLFFBQVEsQ0FBQyxDQUFDLENBQUMsbUJBQW9CLENBQUMsUUFBUSxDQUFDLENBQUMsQ0FBQyxTQUFTLEVBQ3BHLFFBQVEsRUFBRSxDQUFDLENBQUMsRUFBRSxDQUFDLElBQUksQ0FBQyxvQkFBb0IsQ0FBQyxDQUFDLENBQUMsYUFBYSxDQUFDLGFBQWEsS0FBSyxDQUFDLENBQUMsQ0FBQyxDQUFDLEVBQUUsQ0FBQyxDQUFDLENBQUMsQ0FBQyxDQUFDLGFBQWEsQ0FBQyxLQUFLLENBQUM7NEJBRTFHLGdDQUFRLEtBQUssRUFBQyxTQUFTLGFBQWdCOzRCQUN0QyxDQUFDLElBQUksQ0FBQyxLQUFLLENBQUMsTUFBTSxDQUFDLFNBQVMsSUFBSSxFQUFFLENBQUMsQ0FBQyxHQUFHLENBQUMsVUFBVSxDQUFDLEVBQUUsQ0FDckQsZ0NBQVEsRUFBRSxFQUFFLFVBQVUsQ0FBQyxFQUFFLEVBQUUsS0FBSyxFQUFFLFVBQVUsQ0FBQyxFQUFFOztnQ0FBWSxVQUFVLENBQUMsRUFBRSxDQUFVLENBQ2xGLENBQ08sRUFFVixNQUFNLEVBQUUsSUFBSSxDQUFDLEtBQUssQ0FBQyxNQUFNLEVBQ3pCLE1BQU0sRUFBRSxRQUFRLElBQUksRUFBRSxFQUN0QixRQUFRLEVBQUUsT0FBTyxtQkFBbUIsRUFBRSxRQUFRLEtBQUssUUFBUSxDQUFDLENBQUMsQ0FBQyxTQUFTLENBQUMsQ0FBQyxDQUFDLElBQUksQ0FBQyxvQkFBb0IsR0FDbEc7b0JBQ0Y7d0JBQ0MsNkNBQXVCO3dCQUN2QixvQkFBQyxVQUFVLElBQ1YsS0FBSyxFQUFFLG1CQUFtQixFQUFFLElBQUssRUFDakMsUUFBUSxFQUFFLGVBQWUsQ0FBQyxNQUFNLEVBQUUsbUJBQW9CLEVBQUUsQ0FBQyxDQUFDLEVBQUUsQ0FBQyxJQUFJLENBQUMsYUFBYSxDQUFDLENBQUMsQ0FBQyxFQUFFLENBQUMsQ0FBQyxDQUFDLENBQUMsR0FDdkYsQ0FDUSxDQUNULENBQ08sQ0FDTixDQUFDLENBQUM7SUFDVCxDQUFDO0NBRUQ7QUFDRCxNQUFNLENBQUMsT0FBTyxPQUFPLGFBQWMsU0FBUSxLQUFLLENBQUMsU0FBdUI7SUFDdkUsTUFBTSxDQUFVLE9BQU8sR0FBZSxJQUFJLFVBQVUsQ0FBQyxFQUFFLFFBQVEsRUFBRSxTQUFTLEVBQUUsQ0FBQyxDQUFDO0lBQzlFLE1BQU0sQ0FBVSxLQUFLLEdBQVcsUUFBUSxDQUFDO0lBQ3pDLE1BQU0sQ0FBVSxJQUFJLEdBQVcsU0FBUyxDQUFDO0lBQ3pDLFlBQVksS0FBWTtRQUN2QixLQUFLLENBQUMsS0FBSyxDQUFDLENBQUM7UUFDYixJQUFJLENBQUMsS0FBSyxHQUFHO1lBQ1osT0FBTyxFQUFFLElBQUk7WUFDYixNQUFNLEVBQUUsSUFBSTtZQUNaLE1BQU0sRUFBRSxJQUFJO1lBQ1osTUFBTSxFQUFFLElBQUksZUFBZSxFQUFFO1NBQzdCLENBQUE7SUFDRixDQUFDO0lBRVEsaUJBQWlCO1FBQ3pCLElBQUksQ0FBQyxXQUFXLEVBQUUsQ0FBQztRQUNuQixJQUFJLENBQUMsWUFBWSxFQUFFLENBQUM7UUFDcEIsSUFBSSxDQUFDLFdBQVcsRUFBRSxDQUFDO0lBQ3BCLENBQUM7SUFFUSxvQkFBb0I7UUFDNUIsSUFBSSxDQUFDLEtBQUssQ0FBQyxNQUFNLENBQUMsS0FBSyxFQUFFLENBQUM7SUFDM0IsQ0FBQztJQUVELEtBQUssQ0FBQyxZQUFZO1FBQ2pCLElBQUksQ0FBQztZQUNKLE1BQU0sR0FBRyxHQUFHLE1BQU0sS0FBSyxDQUFDLGNBQWMsRUFBRTtnQkFDdkMsTUFBTSxFQUFFLElBQUksQ0FBQyxLQUFLLENBQUMsTUFBTSxDQUFDLE1BQU07Z0JBQ2hDLE9BQU8sRUFBRSxFQUFFLGNBQWMsRUFBRSxrQkFBa0IsRUFBRTthQUMvQyxDQUFDLENBQUM7WUFDSCxJQUFJLElBQUksR0FBRyxNQUFNLEdBQUcsQ0FBQyxJQUFJLEVBQUUsQ0FBQztRQUM3QixDQUFDO1FBQUMsTUFBTSxDQUFDO1lBQ1IsT0FBTyxDQUFDLEtBQUssQ0FBQyxXQUFXLENBQUMsQ0FBQztZQUMzQixPQUFPO1FBQ1IsQ0FBQztRQUNELElBQUksQ0FBQyxRQUFRLENBQUM7WUFDYixPQUFPLEVBQUUsSUFBSTtTQUNiLENBQUMsQ0FBQztJQUNKLENBQUM7SUFFRCxLQUFLLENBQUMsV0FBVztRQUNoQixPQUFPLENBQUMsR0FBRyxDQUFDLGNBQWMsQ0FBQyxDQUFDO1FBQzVCLElBQUksQ0FBQztZQUNKLE1BQU0sR0FBRyxHQUFHLE1BQU0sS0FBSyxDQUFDLGFBQWEsRUFBRTtnQkFDdEMsTUFBTSxFQUFFLElBQUksQ0FBQyxLQUFLLENBQUMsTUFBTSxDQUFDLE1BQU07Z0JBQ2hDLE9BQU8sRUFBRSxFQUFFLGNBQWMsRUFBRSxrQkFBa0IsRUFBRTthQUMvQyxDQUFDLENBQUM7WUFDSCxJQUFJLElBQUksR0FBRyxNQUFNLEdBQUcsQ0FBQyxJQUFJLEVBQUUsQ0FBQztRQUM3QixDQUFDO1FBQUMsTUFBTSxDQUFDO1lBQ1IsT0FBTyxDQUFDLEtBQUssQ0FBQyxXQUFXLENBQUMsQ0FBQztZQUMzQixPQUFPO1FBQ1IsQ0FBQztRQUNELElBQUksQ0FBQyxRQUFRLENBQUM7WUFDYixNQUFNLEVBQUUsSUFBSTtTQUNaLENBQUMsQ0FBQTtJQUNILENBQUM7SUFFRCxLQUFLLENBQUMsV0FBVztRQUNWLElBQUksQ0FBQztZQUNELE1BQU0sR0FBRyxHQUFHLE1BQU0sS0FBSyxDQUFDLGFBQWEsRUFBRTtnQkFDbkMsTUFBTSxFQUFFLElBQUksQ0FBQyxLQUFLLENBQUMsTUFBTSxDQUFDLE1BQU07Z0JBQ2hDLE9BQU8sRUFBRSxFQUFFLGNBQWMsRUFBRSxrQkFBa0IsRUFBRTthQUNsRCxDQUFDLENBQUM7WUFDSCxJQUFJLElBQUksR0FBRyxNQUFNLEdBQUcsQ0FBQyxJQUFJLEVBQUUsQ0FBQztRQUNoQyxDQUFDO1FBQUMsTUFBTSxDQUFDO1lBQ0wsT0FBTyxDQUFDLEtBQUssQ0FBQyxXQUFXLENBQUMsQ0FBQztZQUMzQixPQUFPO1FBQ1gsQ0FBQztRQUNELElBQUksQ0FBQyxRQUFRLENBQUM7WUFDVixNQUFNLEVBQUUsSUFBSTtTQUNmLENBQUMsQ0FBQTtJQUNOLENBQUM7SUFFSyxNQUFNO1FBQ2QsSUFBSSxJQUFJLENBQUMsS0FBSyxDQUFDLE1BQU0sS0FBSyxJQUFJLElBQUksSUFBSSxDQUFDLEtBQUssQ0FBQyxPQUFPLEtBQUssSUFBSSxJQUFJLElBQUksQ0FBQyxLQUFLLENBQUMsTUFBTSxLQUFLLElBQUk7WUFDMUYsT0FBTyxvQkFBQyxPQUFPLE9BQUcsQ0FBQztRQUVwQixPQUFPLENBQ04sb0JBQUMsa0JBQWtCLElBQ2xCLGdCQUFnQixFQUFFLElBQUksQ0FBQyxLQUFLLENBQUMsT0FBTyxFQUNwQyxNQUFNLEVBQUUsSUFBSSxDQUFDLEtBQUssQ0FBQyxNQUFNLEVBQ3pCLE1BQU0sRUFBRSxJQUFJLENBQUMsS0FBSyxDQUFDLE1BQU0sR0FDeEIsQ0FDRixDQUFDO0lBQ0gsQ0FBQyJ9