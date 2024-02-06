import React from 'react';
import Loading from '../components/Loading';
export default class ConfigBuilder extends React.Component {
    static pattern = new URLPattern({ pathname: '/config' });
    static title = 'Config';
    static base = '/config';
    constructor(props) {
        super(props);
        this.state = {
            cameras: null,
            selectedCamera: 0,
            pipeline: [],
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
            selectedCamera: 0,
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
    handleCameraChange = (e) => {
        const value = e.currentTarget.value;
        if (value.startsWith('camera-')) {
            this.setState({
                selectedCamera: parseInt(value.substring('camera-'.length))
            });
        }
        else {
            this.setState(({ config }) => ({
                selectedCamera: (config?.cameras.length ?? -1) + 1,
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
    render() {
        if (this.state.config === null || this.state.cameras === null)
            return React.createElement(Loading, null);
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
            React.createElement("fieldset", null,
                React.createElement("legend", null, "Camera Selector"),
                React.createElement("fieldset", null,
                    React.createElement("legend", null, "Ordinal"),
                    React.createElement("div", null,
                        React.createElement("label", { htmlFor: "camera_ordinal_enable" }, "Enabled"),
                        React.createElement("input", { id: "camera_ordinal_enable", type: "checkbox", checked: !!currentSelector.ordinal })),
                    React.createElement("div", null,
                        React.createElement("label", { htmlFor: 'camera_ordinal' }, "Ordinal"),
                        React.createElement("input", { id: "camera_ordinal", type: "number", min: 0, value: currentSelector.ordinal }))),
                React.createElement("label", { htmlFor: "camera_mxid_enable" }, "mxid"),
                React.createElement("input", { id: "camera_mxid_enable", type: "checkbox", checked: !!currentSelector.mxid }),
                React.createElement("input", { id: "camera_mxid_enable", type: "text", disabled: !!currentSelector.mxid, value: currentSelector.mxid }),
                React.createElement("label", { htmlFor: "camera_name_enable" }, "name"),
                React.createElement("input", { id: "camera_name_enable", type: "checkbox", checked: !!currentSelector.mxid })),
            React.createElement("button", null, "Save")));
    }
}
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiQ29uZmlnQnVpbGRlci5qcyIsInNvdXJjZVJvb3QiOiIiLCJzb3VyY2VzIjpbIi4uLy4uL3RzL3JvdXRlL0NvbmZpZ0J1aWxkZXIudHN4Il0sIm5hbWVzIjpbXSwibWFwcGluZ3MiOiJBQUFBLE9BQU8sS0FBaUMsTUFBTSxPQUFPLENBQUM7QUFHdEQsT0FBTyxPQUFPLE1BQU0sdUJBQXVCLENBQUM7QUFvQjVDLE1BQU0sQ0FBQyxPQUFPLE9BQU8sYUFBYyxTQUFRLEtBQUssQ0FBQyxTQUF1QjtJQUNwRSxNQUFNLENBQVUsT0FBTyxHQUFlLElBQUksVUFBVSxDQUFDLEVBQUUsUUFBUSxFQUFFLFNBQVMsRUFBRSxDQUFDLENBQUM7SUFDOUUsTUFBTSxDQUFVLEtBQUssR0FBVyxRQUFRLENBQUM7SUFDekMsTUFBTSxDQUFVLElBQUksR0FBVyxTQUFTLENBQUM7SUFDekMsWUFBWSxLQUFZO1FBQ3BCLEtBQUssQ0FBQyxLQUFLLENBQUMsQ0FBQztRQUViLElBQUksQ0FBQyxLQUFLLEdBQUc7WUFDVCxPQUFPLEVBQUUsSUFBSTtZQUNiLGNBQWMsRUFBRSxDQUFDO1lBQ2pCLFFBQVEsRUFBRSxFQUFFO1lBQ1osTUFBTSxFQUFFLElBQUk7WUFDWixNQUFNLEVBQUUsSUFBSSxlQUFlLEVBQUU7U0FDaEMsQ0FBQTtJQUNMLENBQUM7SUFFRCxpQkFBaUI7UUFDYixJQUFJLENBQUMsV0FBVyxFQUFFLENBQUM7UUFDbkIsSUFBSSxDQUFDLFlBQVksRUFBRSxDQUFDO0lBQ3hCLENBQUM7SUFFRCxvQkFBb0I7UUFDaEIsSUFBSSxDQUFDLEtBQUssQ0FBQyxNQUFNLENBQUMsS0FBSyxFQUFFLENBQUM7SUFDOUIsQ0FBQztJQUVELEtBQUssQ0FBQyxZQUFZO1FBQ2QsSUFBSTtZQUNBLE1BQU0sR0FBRyxHQUFHLE1BQU0sS0FBSyxDQUFDLGNBQWMsRUFBRTtnQkFDcEMsTUFBTSxFQUFFLElBQUksQ0FBQyxLQUFLLENBQUMsTUFBTSxDQUFDLE1BQU07Z0JBQ2hDLE9BQU8sRUFBRSxFQUFF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