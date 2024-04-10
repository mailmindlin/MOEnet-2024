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
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiRWRpdENvbmZpZy5qcyIsInNvdXJjZVJvb3QiOiIiLCJzb3VyY2VzIjpbIi4uLy4uL3RzL3JvdXRlL0VkaXRDb25maWcudHN4Il0sIm5hbWVzIjpbXSwibWFwcGluZ3MiOiJBQUFBLE9BQU8sS0FBaUMsTUFBTSxPQUFPLENBQUM7QUFrQnRELE1BQU0sQ0FBQyxPQUFPLE9BQU8sVUFBVyxTQUFRLEtBQUssQ0FBQyxTQUF1QjtJQUNqRSxNQUFNLENBQVUsT0FBTyxHQUFlLElBQUksVUFBVSxDQUFDLEVBQUUsUUFBUSxFQUFFLFlBQVksRUFBRSxDQUFDLENBQUM7SUFDakYsTUFBTSxDQUFVLEtBQUssR0FBVyxZQUFZLENBQUM7SUFDN0MsTUFBTSxDQUFVLElBQUksR0FBVyxZQUFZLENBQUM7SUFDM0IsTUFBTSxDQUFTO0lBRWhDLFlBQVksS0FBWTtRQUNwQixLQUFLLENBQUMsS0FBSyxDQUFDLENBQUM7UUFDYixJQUFJLENBQUMsTUFBTSxHQUFHLEdBQUcsSUFBSSxDQUFDLEtBQUssQ0FBQyxJQUFJLENBQUMsTUFBTSxFQUFFLEdBQUcsR0FBRyxDQUFDLEVBQUUsQ0FBQztRQUNuRCxJQUFJLENBQUMsS0FBSyxHQUFHO1lBQ1QsTUFBTSxFQUFFLEVBQUU7WUFDVixLQUFLLEVBQUUsSUFBSTtZQUNYLFFBQVEsRUFBRSxJQUFJO1lBQ2QsVUFBVSxFQUFFLElBQUk7WUFDaEIsT0FBTyxFQUFFLElBQUk7WUFDYixNQUFNLEVBQUUsSUFBSSxlQUFlLEVBQUU7U0FDaEMsQ0FBQTtJQUNMLENBQUM7SUFFTyxRQUFRLENBQUMsSUFBWTtRQUN6QixPQUFPLEdBQUcsSUFBSSxHQUFHLElBQUksQ0FBQyxNQUFNLEVBQUUsQ0FBQztJQUNuQyxDQUFDO0lBRUQsaUJBQWlCO1FBQ2IsSUFBSSxDQUFDLFdBQVcsRUFBRSxDQUFDO1FBQ25CLElBQUksQ0FBQyxXQUFXLEVBQUUsQ0FBQztJQUN2QixDQUFDO0lBRUQsS0FBSyxDQUFDLFdBQVc7UUFDYixJQUFJLENBQUM7WUFDRCxNQUFNLEdBQUcsR0FBRyxNQUFNLEtBQUssQ0FBQyxhQUFhLEVBQUU7Z0JBQ25DLE1BQU0sRUFBRSxJQUFJLENBQUMsS0FBSyxDQUFDLE1BQU0sQ0FBQyxNQUFNO2dCQUNoQyxPQUFPLEVBQUUsRUFBRSxjQUFjLEVBQUUsa0JBQWtCLEVBQUU7YUFDbEQsQ0FBQyxDQUFDO1lBQ0gsSUFBSSxJQUFJLEdBQUcsTUFBTSxHQUFHLENBQUMsSUFBSSxFQUFFLENBQUM7UUFDaEMsQ0FBQztRQUFDLE1BQU0sQ0FBQztZQUNMLE9BQU8sQ0FBQyxLQUFLLENBQUMsV0FBVyxDQUFDLENBQUM7WUFDM0IsT0FBTztRQUNYLENBQUM7UUFDRCxJQUFJLENBQUMsUUFBUSxDQUFDO1lBQ1YsTUFBTSxFQUFFLElBQUk7U0FDZixDQUFDLENBQUE7SUFDTixDQUFDO0lBRUQsS0FBSyxDQUFDLFdBQVc7UUFDYixJQUFJLENBQUM7WUFDRCxNQUFNLEdBQUcsR0FBRyxNQUFNLEtBQUssQ0FBQyxhQUFhLEVBQUU7Z0JBQ25DLE1BQU0sRUFBRSxJQUFJLENBQUMsS0FBSyxDQUFDLE1BQU0sQ0FBQyxNQUFNO2dCQUNoQyxPQUFPLEVBQUUsRUFBRSxjQUFjLEVBQUUsa0JBQWtCLEVBQUU7YUFDbEQsQ0FBQyxDQUFDO1lBQ0gsSUFBSSxJQUFJLEdBQUcsTUFBTSxHQUFHLENBQUMsSUFBSSxFQUFFLENBQUM7UUFDaEMsQ0FBQztRQUFDLE1BQU0sQ0FBQztZQUNMLE9BQU8sQ0FBQyxLQUFLLENBQUMsV0FBVyxDQUFDLENBQUM7WUFDM0IsT0FBTztRQUNYLENBQUM7UUFDRCxJQUFJLENBQUMsUUFBUSxDQUFDO1lBQ1YsS0FBSyxFQUFFLElBQUksQ0FBQyxTQUFTLENBQUMsSUFBSSxDQUFDO1lBQzNCLFFBQVEsRUFBRSxJQUFJLENBQUMsU0FBUyxDQUFDLElBQUksRUFBRSxTQUFTLEVBQUUsSUFBSSxDQUFDO1NBQ2xELENBQUMsQ0FBQTtJQUNOLENBQUM7SUFHRCxpQkFBaUIsR0FBRyxDQUFDLENBQTRCLEVBQUUsRUFBRTtRQUNqRCxNQUFNLFFBQVEsR0FBRyxDQUFDLENBQUMsYUFBYSxDQUFDLFNBQVMsQ0FBQztRQUMzQyxJQUFJLENBQUM7WUFDRCxJQUFJLE1BQU0sR0FBRyxJQUFJLENBQUMsS0FBSyxDQUFDLFFBQVEsQ0FBQyxDQUFDO1FBQ3RDLENBQUM7UUFBQyxNQUFNLENBQUM7WUFDTCxJQUFJLENBQUMsUUFBUSxDQUFDLEVBQUUsUUFBUSxFQUFFLE9BQU8sRUFBRSxLQUFLLEVBQUUsQ0FBQyxDQUFDO1lBQzVDLE9BQU87UUFDWCxDQUFDO1FBQ0QsSUFBSSxLQUFLLEdBQUcsSUFBSSxDQUFDLFNBQVMsQ0FBQyxNQUFNLENBQUMsQ0FBQztRQUNuQyxJQUFJLFNBQVMsR0FBRyxJQUFJLENBQUMsU0FBUyxDQUFDLE1BQU0sRUFBQyxTQUFTLEVBQUMsSUFBSSxDQUFDLENBQUM7UUFDdEQsSUFBSSxDQUFDLFFBQVEsQ0FBQyxDQUFDLEVBQUUsS0FBSyxFQUFFLFFBQVEsRUFBRSxFQUFFLEVBQUUsQ0FBQyxDQUFDLEtBQUssSUFBSSxRQUFRLENBQUMsQ0FBQyxDQUFDLEVBQUUsUUFBUSxFQUFFLFFBQVEsRUFBRSxLQUFLLEVBQUUsUUFBUSxFQUFFLE9BQU8sRUFBRSxJQUFJLEVBQUUsQ0FBQyxDQUFDLENBQUMsRUFBRSxLQUFLLEVBQUUsUUFBUSxFQUFFLFNBQVMsRUFBRSxPQUFPLEVBQUUsSUFBSSxFQUFFLENBQUMsQ0FBQyxDQUFDO0lBQ3pLLENBQUMsQ0FBQTtJQUVELHNCQUFzQixHQUFHLENBQUMsQ0FBZ0MsRUFBRSxFQUFFO1FBQzFELElBQUksQ0FBQyxRQUFRLENBQUMsRUFBRSxVQUFVLEVBQUUsQ0FBQyxDQUFDLGFBQWEsQ0FBQyxPQUFPLEVBQUUsQ0FBQyxDQUFDO0lBQzNELENBQUMsQ0FBQTtJQUVELE1BQU07UUFDRixPQUFPLENBQ0g7WUFDSSwrQkFDSSxPQUFPLEVBQUUsSUFBSSxDQUFDLFFBQVEsQ0FBQyxZQUFZLENBQUMsZ0JBR2hDO1lBQ1IsK0JBQ0ksRUFBRSxFQUFFLElBQUksQ0FBQyxRQUFRLENBQUMsWUFBWSxDQUFDLEVBQy9CLElBQUksRUFBQyxVQUFVLEVBQ2YsT0FBTyxFQUFFLElBQUksQ0FBQyxLQUFLLENBQUMsVUFBVSxFQUM5QixRQUFRLEVBQUUsSUFBSSxDQUFDLHNCQUFzQixHQUN2QztZQUNBLElBQUksQ0FBQyxLQUFLLENBQUMsVUFBVSxJQUFJLENBQ3ZCLDZCQUNJLEtBQUssRUFBRSxFQUFDLEtBQUssRUFBRSxNQUFNLEVBQUUsT0FBTyxFQUFFLE9BQU8sRUFBQyxFQUN4QyxlQUFlLFFBQ2YsT0FBTyxFQUFFLElBQUksQ0FBQyxpQkFBaUIsSUFFOUIsSUFBSSxDQUFDLEtBQUssQ0FBQyxRQUFRLENBQ2xCLENBQ1Q7WUFDQyxJQUFJLENBQUMsS0FBSyxDQUFDLFVBQVUsSUFBSSxDQUFDLHlDQUFLLENBQ2hDO1lBQ0QsZ0NBQ0ksUUFBUSxFQUFFLENBQUMsSUFBSSxDQUFDLEtBQUssQ0FBQyxPQUFPLFdBR3hCLENBQ1AsQ0FDVCxDQUFBO0lBQ0wsQ0FBQyJ9