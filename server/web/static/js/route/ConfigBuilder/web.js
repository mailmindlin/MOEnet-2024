import React from 'react';
import { Binding } from './bound';
import Collapsible from '../../components/Collapsible';
export default function WebConfigEditor(props) {
    const config = props.config ?? {};
    const Bound = Binding(config, props.onChange);
    return (React.createElement(Collapsible, { legend: 'Web Server' },
        React.createElement(Bound.Checkbox, { name: 'enabled', label: 'Enabled', defaultValue: true }),
        React.createElement(Bound.Text, { name: 'host', label: 'Host', placeholder: 'localhost' }),
        React.createElement(Bound.Number, { name: 'port', label: 'Port', defaultValue: 8080, min: 1, max: 65536 })));
}
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoid2ViLmpzIiwic291cmNlUm9vdCI6IiIsInNvdXJjZXMiOlsiLi4vLi4vLi4vdHMvcm91dGUvQ29uZmlnQnVpbGRlci93ZWIudHN4Il0sIm5hbWVzIjpbXSwibWFwcGluZ3MiOiJBQUFBLE9BQU8sS0FBSyxNQUFNLE9BQU8sQ0FBQztBQUUxQixPQUFPLEVBQUUsT0FBTyxFQUFFLE1BQU0sU0FBUyxDQUFDO0FBQ2xDLE9BQU8sV0FBVyxNQUFNLDhCQUE4QixDQUFDO0FBT3ZELE1BQU0sQ0FBQyxPQUFPLFVBQVUsZUFBZSxDQUFDLEtBQTJCO0lBQ2xFLE1BQU0sTUFBTSxHQUFHLEtBQUssQ0FBQyxNQUFNLElBQUksRUFBRSxDQUFDO0lBRWxDLE1BQU0sS0FBSyxHQUFHLE9BQU8sQ0FBQyxNQUFNLEVBQUUsS0FBSyxDQUFDLFFBQVEsQ0FBQyxDQUFDO0lBQzlDLE9BQU8sQ0FDTixvQkFBQyxXQUFXLElBQUMsTUFBTSxFQUFDLFlBQVk7UUFDL0Isb0JBQUMsS0FBSyxDQUFDLFFBQVEsSUFBQyxJQUFJLEVBQUMsU0FBUyxFQUFDLEtBQUssRUFBQyxTQUFTLEVBQUMsWUFBWSxFQUFFLElBQUksR0FBSTtRQUNyRSxvQkFBQyxLQUFLLENBQUMsSUFBSSxJQUFDLElBQUksRUFBQyxNQUFNLEVBQUMsS0FBSyxFQUFDLE1BQU0sRUFBQyxXQUFXLEVBQUMsV0FBVyxHQUFHO1FBQy9ELG9CQUFDLEtBQUssQ0FBQyxNQUFNLElBQUMsSUFBSSxFQUFDLE1BQU0sRUFBQyxLQUFLLEVBQUMsTUFBTSxFQUFDLFlBQVksRUFBRSxJQUFJLEVBQUUsR0FBRyxFQUFFLENBQUMsRUFBRSxHQUFHLEVBQUUsS0FBSyxHQUFJLENBQ3BFLENBQ2QsQ0FBQztBQUNILENBQUMifQ==