import React from 'react';
import { Binding, Collapsible } from './bound';
export default function WebConfigEditor(props) {
    const config = props.config ?? {};
    const Bound = Binding(config, props.onChange);
    return (React.createElement(Collapsible, { legend: 'Webserver' },
        React.createElement(Bound.Checkbox, { name: 'enabled', label: 'Enabled', defaultValue: true }),
        React.createElement(Bound.Text, { name: 'host', label: 'Host', placeholder: 'localhost' }),
        React.createElement(Bound.Number, { name: 'port', label: 'Port', defaultValue: 8080, min: 1, max: 65536 })));
}
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoid2ViLmpzIiwic291cmNlUm9vdCI6IiIsInNvdXJjZXMiOlsiLi4vLi4vLi4vdHMvcm91dGUvQ29uZmlnQnVpbGRlci93ZWIudHN4Il0sIm5hbWVzIjpbXSwibWFwcGluZ3MiOiJBQUFBLE9BQU8sS0FBSyxNQUFNLE9BQU8sQ0FBQztBQUUxQixPQUFPLEVBQUUsT0FBTyxFQUFFLFdBQVcsRUFBRSxNQUFNLFNBQVMsQ0FBQztBQU8vQyxNQUFNLENBQUMsT0FBTyxVQUFVLGVBQWUsQ0FBQyxLQUEyQjtJQUNsRSxNQUFNLE1BQU0sR0FBRyxLQUFLLENBQUMsTUFBTSxJQUFJLEVBQUUsQ0FBQztJQUVsQyxNQUFNLEtBQUssR0FBRyxPQUFPLENBQUMsTUFBTSxFQUFFLEtBQUssQ0FBQyxRQUFRLENBQUMsQ0FBQztJQUM5QyxPQUFPLENBQ04sb0JBQUMsV0FBVyxJQUFDLE1BQU0sRUFBQyxXQUFXO1FBQzlCLG9CQUFDLEtBQUssQ0FBQyxRQUFRLElBQUMsSUFBSSxFQUFDLFNBQVMsRUFBQyxLQUFLLEVBQUMsU0FBUyxFQUFDLFlBQVksRUFBRSxJQUFJLEdBQUk7UUFDckUsb0JBQUMsS0FBSyxDQUFDLElBQUksSUFBQyxJQUFJLEVBQUMsTUFBTSxFQUFDLEtBQUssRUFBQyxNQUFNLEVBQUMsV0FBVyxFQUFDLFdBQVcsR0FBRztRQUMvRCxvQkFBQyxLQUFLLENBQUMsTUFBTSxJQUFDLElBQUksRUFBQyxNQUFNLEVBQUMsS0FBSyxFQUFDLE1BQU0sRUFBQyxZQUFZLEVBQUUsSUFBSSxFQUFFLEdBQUcsRUFBRSxDQUFDLEVBQUUsR0FBRyxFQUFFLEtBQUssR0FBSSxDQUNwRSxDQUNkLENBQUM7QUFDSCxDQUFDIn0=