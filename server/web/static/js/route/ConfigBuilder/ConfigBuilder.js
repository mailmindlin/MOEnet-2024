import React from 'react';
import Loading from '../../components/Loading';
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
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiQ29uZmlnQnVpbGRlci5qcyIsInNvdXJjZVJvb3QiOiIiLCJzb3VyY2VzIjpbIi4uLy4uLy4uL3RzL3JvdXRlL0NvbmZpZ0J1aWxkZXIvQ29uZmlnQnVpbGRlci50c3giXSwibmFtZXMiOltdLCJtYXBwaW5ncyI6IkFBQUEsT0FBTyxLQUFpQyxNQUFNLE9BQU8sQ0FBQztBQUd0RCxPQUFPLE9BQU8sTUFBTSwwQkFBMEIsQ0FBQztBQW9CL0MsTUFBTSxDQUFDLE9BQU8sT0FBTyxhQUFjLFNBQVEsS0FBSyxDQUFDLFNBQXVCO0lBQ3BFLE1BQU0sQ0FBVSxPQUFPLEdBQWUsSUFBSSxVQUFVLENBQUMsRUFBRSxRQUFRLEVBQUUsU0FBUyxFQUFFLENBQUMsQ0FBQztJQUM5RSxNQUFNLENBQVUsS0FBSyxHQUFXLFFBQVEsQ0FBQztJQUN6QyxNQUFNLENBQVUsSUFBSSxHQUFXLFNBQVMsQ0FBQztJQUN6QyxZQUFZLEtBQVk7UUFDcEIsS0FBSyxDQUFDLEtBQUssQ0FBQyxDQUFDO1FBRWIsSUFBSSxDQUFDLEtBQUssR0FBRztZQUNULE9BQU8sRUFBRSxJQUFJO1lBQ2IsY0FBYyxFQUFFLENBQUM7WUFDakIsUUFBUSxFQUFFLEVBQUU7WUFDWixNQUFNLEVBQUUsSUFBSTtZQUNaLE1BQU0sRUFBRSxJQUFJLGVBQWUsRUFBRTtTQUNoQyxDQUFBO0lBQ0wsQ0FBQztJQUVELGlCQUFpQjtRQUNiLElBQUksQ0FBQyxXQUFXLEVBQUUsQ0FBQztRQUNuQixJQUFJLENBQUMsWUFBWSxFQUFFLENBQUM7SUFDeEIsQ0FBQztJQUVELG9CQUFvQjtRQUNoQixJQUFJLENBQUMsS0FBSyxDQUFDLE1BQU0sQ0FBQyxLQUFLLEVBQUUsQ0FBQztJQUM5QixDQUFDO0lBRUQsS0FBSyxDQUFDLFlBQVk7UUFDZCxJQUFJO1lBQ0EsTUFBTSxHQUFHLEdBQUcsTUFBTSxLQUFLLENBQUMsY0FBYyxFQUFFO2dCQUNwQyxNQUFNLEVBQUUsSUFBSSxDQUFDLEtBQUssQ0FBQyxNQUFNLENBQUMsTUFBTTtnQkFD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