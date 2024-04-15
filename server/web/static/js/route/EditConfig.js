import React from 'react';
export default class EditConfig extends React.Component {
    static pattern = new URLPattern({ pathname: '/configraw' });
    static title = 'Raw Config';
    static base = '/configraw';
    suffix;
    constructor(props) {
        super(props);
        this.suffix = `${Math.floor(Math.random() * 1e6)}`;
        this.state = {
            schema: {},
            value: '{}',
            valueRaw: '{}',
            editingRaw: true,
            isValid: true,
            cancel: new AbortController(),
        };
    }
    uniqueId(name) {
        return `${name}${this.suffix}`;
    }
    componentDidMount() {
        this.fetchConfig();
        this.fetchSchema();
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
            value: JSON.stringify(data),
            valueRaw: JSON.stringify(data, undefined, '  '),
        });
    }
    handleValueChange = (e) => {
        const valueRaw = e.currentTarget.innerText;
        try {
            var parsed = JSON.parse(valueRaw);
        }
        catch {
            this.setState({ valueRaw, isValid: false });
            return;
        }
        var value = JSON.stringify(parsed);
        var valueRaw2 = JSON.stringify(parsed, undefined, '  ');
        this.setState(({ value: valueOld }) => (value == valueOld ? { valueRaw: valueRaw, value: valueOld, isValid: true } : { value, valueRaw: valueRaw2, isValid: true }));
    };
    handleEditingRawChange = (e) => {
        this.setState({ editingRaw: e.currentTarget.checked });
    };
    render() {
        return (React.createElement("div", null,
            React.createElement("label", { htmlFor: this.uniqueId('editingRaw') }, "Edit raw?"),
            React.createElement("input", { id: this.uniqueId('editingRaw'), type: 'checkbox', checked: this.state.editingRaw, onChange: this.handleEditingRawChange }),
            this.state.editingRaw && (React.createElement("pre", { style: { width: "100%", display: "block" }, contentEditable: true, onInput: this.handleValueChange }, this.state.valueRaw)),
            this.state.editingRaw || (React.createElement(React.Fragment, null)),
            React.createElement("button", { disabled: !this.state.isValid }, "Save")));
    }
}
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiRWRpdENvbmZpZy5qcyIsInNvdXJjZVJvb3QiOiIiLCJzb3VyY2VzIjpbIi4uLy4uL3RzL3JvdXRlL0VkaXRDb25maWcudHN4Il0sIm5hbWVzIjpbXSwibWFwcGluZ3MiOiJBQUFBLE9BQU8sS0FBaUMsTUFBTSxPQUFPLENBQUM7QUFrQnRELE1BQU0sQ0FBQyxPQUFPLE9BQU8sVUFBVyxTQUFRLEtBQUssQ0FBQyxTQUF1QjtJQUNqRSxNQUFNLENBQVUsT0FBTyxHQUFlLElBQUksVUFBVSxDQUFDLEVBQUUsUUFBUSxFQUFFLFlBQVksRUFBRSxDQUFDLENBQUM7SUFDakYsTUFBTSxDQUFVLEtBQUssR0FBVyxZQUFZLENBQUM7SUFDN0MsTUFBTSxDQUFVLElBQUksR0FBVyxZQUFZLENBQUM7SUFDM0IsTUFBTSxDQUFTO0lBRWhDLFlBQVksS0FBWTtRQUNwQixLQUFLLENBQUMsS0FBSyxDQUFDLENBQUM7UUFDYixJQUFJLENBQUMsTUFBTSxHQUFHLEdBQUcsSUFBSSxDQUFDLEtBQUssQ0FBQyxJQUFJLENBQUMsTUFBTSxFQUFFLEdBQUcsR0FBRyxDQUFDLEVBQUUsQ0FBQztRQUNuRCxJQUFJLENBQUMsS0FBSyxHQUFHO1lBQ1QsTUFBTSxFQUFFLEVBQUU7WUFDVixLQUFLLEVBQUUsSUFBSTtZQUNYLFFBQVEsRUFBRSxJQUFJO1lBQ2QsVUFBVSxFQUFFLElBQUk7WUFDaEIsT0FBTyxFQUFFLElBQUk7WUFDYixNQUFNLEVBQUUsSUFBSSxlQUFlLEVBQUU7U0FDaEMsQ0FBQTtJQUNMLENBQUM7SUFFTyxRQUFRLENBQUMsSUFBWTtRQUN6QixPQUFPLEdBQUcsSUFBSSxHQUFHLElBQUksQ0FBQyxNQUFNLEVBQUUsQ0FBQztJQUNuQyxDQUFDO0lBRVEsaUJBQWlCO1FBQ3RCLElBQUksQ0FBQyxXQUFXLEVBQUUsQ0FBQztRQUNuQixJQUFJLENBQUMsV0FBVyxFQUFFLENBQUM7SUFDdkIsQ0FBQztJQUVELEtBQUssQ0FBQyxXQUFXO1FBQ2IsSUFBSSxDQUFDO1lBQ0QsTUFBTSxH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