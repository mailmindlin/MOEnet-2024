import React from 'react';
export default class EditConfig extends React.Component {
    static pattern = new URLPattern({ pathname: '/configraw' });
    static title = 'Raw Config';
    static base = '/configraw';
    constructor(props) {
        super(props);
        this.state = {
            schema: {},
            value: '{}',
            valueRaw: '{}',
            isValid: true,
            cancel: new AbortController(),
        };
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
    render() {
        return (React.createElement("div", null,
            React.createElement("pre", { style: { width: "100%", display: "block" }, contentEditable: true, onInput: this.handleValueChange }, this.state.valueRaw),
            React.createElement("button", { disabled: !this.state.isValid }, "Save")));
    }
}
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiRWRpdENvbmZpZy5qcyIsInNvdXJjZVJvb3QiOiIiLCJzb3VyY2VzIjpbIi4uLy4uL3RzL3JvdXRlL0VkaXRDb25maWcudHN4Il0sIm5hbWVzIjpbXSwibWFwcGluZ3MiOiJBQUFBLE9BQU8sS0FBaUMsTUFBTSxPQUFPLENBQUM7QUFnQnRELE1BQU0sQ0FBQyxPQUFPLE9BQU8sVUFBVyxTQUFRLEtBQUssQ0FBQyxTQUF1QjtJQUNqRSxNQUFNLENBQVUsT0FBTyxHQUFlLElBQUksVUFBVSxDQUFDLEVBQUUsUUFBUSxFQUFFLFlBQVksRUFBRSxDQUFDLENBQUM7SUFDakYsTUFBTSxDQUFVLEtBQUssR0FBVyxZQUFZLENBQUM7SUFDN0MsTUFBTSxDQUFVLElBQUksR0FBVyxZQUFZLENBQUM7SUFDNUMsWUFBWSxLQUFZO1FBQ3BCLEtBQUssQ0FBQyxLQUFLLENBQUMsQ0FBQztRQUViLElBQUksQ0FBQyxLQUFLLEdBQUc7WUFDVCxNQUFNLEVBQUUsRUFBRTtZQUNWLEtBQUssRUFBRSxJQUFJO1lBQ1gsUUFBUSxFQUFFLElBQUk7WUFDZCxPQUFPLEVBQUUsSUFBSTtZQUNiLE1BQU0sRUFBRSxJQUFJLGVBQWUsRUFBRTtTQUNoQyxDQUFBO0lBQ0wsQ0FBQztJQUVELGlCQUFpQjtRQUNiLElBQUksQ0FBQyxXQUFXLEVBQUUsQ0FBQztRQUNuQixJQUFJLENBQUMsV0FBVyxFQUFFLENBQUM7SUFDdkIsQ0FBQztJQUVELEtBQUssQ0FBQyxXQUFXO1FBQ2IsSUFBSTtZQUNBLE1BQU0sR0FBRyxHQUFHLE1BQU0sS0FBSyxDQUFDLGFBQWEsRUFBRTtnQkFDbkMsTUFBTSxFQUFFLElBQUksQ0FBQyxLQUFLLENBQUMsTUFBTSxDQUFDLE1BQU07Z0JBQ2hDLE9BQU8sRUFBRSxFQUFFLGNBQWMsRUFBRSxrQkFBa0IsRUFBRTthQUNsRCxDQUFDLENBQUM7WUFDSCxJQUFJLElBQUksR0FBRyxNQUFNLEdBQUcsQ0FBQyxJQUFJLEVBQUUsQ0FBQztTQUMvQjtRQUFDLE1BQU07WUFDSixPQUFP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