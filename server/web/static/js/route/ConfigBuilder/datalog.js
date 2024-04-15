import React from 'react';
import { Binding } from './bound';
import Collapsible from '../../components/Collapsible';
export default function DatalogConfigEdtior(props) {
    const config = props.config ?? {};
    const Bound = Binding(config, props.onChange);
    return (React.createElement(Collapsible, { legend: 'Datalog' },
        React.createElement(Bound.Checkbox, { name: 'enabled', label: 'Enabled', help: 'Enable data logs', defaultValue: true }),
        React.createElement(Bound.Text, { name: 'folder', label: 'Folder', help: 'Folder to save data logs in' }),
        React.createElement(Bound.Number, { name: 'free_space', label: 'Free space', help: 'Minimum free space' }),
        React.createElement(Bound.Checkbox, { name: 'mkdir', label: 'mkdir', defaultValue: false, help: "Make log folder if it doesn't exist?" }),
        React.createElement(Bound.Checkbox, { name: 'cleanup', label: 'Cleanup', defaultValue: false, help: "Should we clean up old log files? (see free_space and max_logs)" })));
}
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiZGF0YWxvZy5qcyIsInNvdXJjZVJvb3QiOiIiLCJzb3VyY2VzIjpbIi4uLy4uLy4uL3RzL3JvdXRlL0NvbmZpZ0J1aWxkZXIvZGF0YWxvZy50c3giXSwibmFtZXMiOltdLCJtYXBwaW5ncyI6IkFBQUEsT0FBTyxLQUFLLE1BQU0sT0FBTyxDQUFDO0FBRTFCLE9BQU8sRUFBRSxPQUFPLEVBQUUsTUFBTSxTQUFTLENBQUM7QUFDbEMsT0FBTyxXQUFXLE1BQU0sOEJBQThCLENBQUM7QUFPdkQsTUFBTSxDQUFDLE9BQU8sVUFBVSxtQkFBbUIsQ0FBQyxLQUErQjtJQUMxRSxNQUFNLE1BQU0sR0FBRyxLQUFLLENBQUMsTUFBTSxJQUFJLEVBQUUsQ0FBQztJQUVsQyxNQUFNLEtBQUssR0FBRyxPQUFPLENBQUMsTUFBTSxFQUFFLEtBQUssQ0FBQyxRQUFRLENBQUMsQ0FBQztJQUM5QyxPQUFPLENBQ04sb0JBQUMsV0FBVyxJQUFDLE1BQU0sRUFBQyxTQUFTO1FBQzVCLG9CQUFDLEtBQUssQ0FBQyxRQUFRLElBQ2QsSUFBSSxFQUFDLFNBQVMsRUFDZCxLQUFLLEVBQUMsU0FBUyxFQUNmLElBQUksRUFBQyxrQkFBa0IsRUFDdkIsWUFBWSxFQUFFLElBQUksR0FDakI7UUFDRixvQkFBQyxLQUFLLENBQUMsSUFBSSxJQUNWLElBQUksRUFBQyxRQUFRLEVBQ2IsS0FBSyxFQUFDLFFBQVEsRUFDZCxJQUFJLEVBQUMsNkJBQTZCLEdBQ2pDO1FBQ0Ysb0JBQUMsS0FBSyxDQUFDLE1BQU0sSUFDWixJQUFJLEVBQUMsWUFBWSxFQUNqQixLQUFLLEVBQUMsWUFBWSxFQUNsQixJQUFJLEVBQUMsb0JBQW9CLEdBQ3hCO1FBQ0Ysb0JBQUMsS0FBSyxDQUFDLFFBQVEsSUFDZCxJQUFJLEVBQUMsT0FBTyxFQUNaLEtBQUssRUFBQyxPQUFPLEVBQ2IsWUFBWSxFQUFFLEtBQUssRUFDbkIsSUFBSSxFQUFDLHNDQUFzQyxHQUMxQztRQUNGLG9CQUFDLEtBQUssQ0FBQyxRQUFRLElBQ2QsSUFBSSxFQUFDLFNBQVMsRUFDZCxLQUFLLEVBQUMsU0FBUyxFQUNmLFlBQVksRUFBRSxLQUFLLEVBQ25CLElBQUksRUFBQyxpRUFBaUUsR0FDckUsQ0FDVyxDQUNkLENBQUM7QUFDSCxDQUFDIn0=