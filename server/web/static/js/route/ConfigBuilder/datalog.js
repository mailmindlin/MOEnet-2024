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
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiZGF0YWxvZy5qcyIsInNvdXJjZVJvb3QiOiIiLCJzb3VyY2VzIjpbIi4uLy4uLy4uL3RzL3JvdXRlL0NvbmZpZ0J1aWxkZXIvZGF0YWxvZy50c3giXSwibmFtZXMiOltdLCJtYXBwaW5ncyI6IkFBQUEsT0FBTyxLQUFLLE1BQU0sT0FBTyxDQUFDO0FBRTFCLE9BQU8sRUFBOEIsT0FBTyxFQUFFLE1BQU0sU0FBUyxDQUFDO0FBQzlELE9BQU8sV0FBVyxNQUFNLDhCQUE4QixDQUFDO0FBT3ZELE1BQU0sQ0FBQyxPQUFPLFVBQVUsbUJBQW1CLENBQUMsS0FBK0I7SUFDMUUsTUFBTSxNQUFNLEdBQUcsS0FBSyxDQUFDLE1BQU0sSUFBSSxFQUFFLENBQUM7SUFFbEMsTUFBTSxLQUFLLEdBQUcsT0FBTyxDQUFDLE1BQU0sRUFBRSxLQUFLLENBQUMsUUFBUSxDQUFDLENBQUM7SUFDOUMsT0FBTyxDQUNOLG9CQUFDLFdBQVcsSUFBQyxNQUFNLEVBQUMsU0FBUztRQUM1QixvQkFBQyxLQUFLLENBQUMsUUFBUSxJQUNkLElBQUksRUFBQyxTQUFTLEVBQ2QsS0FBSyxFQUFDLFNBQVMsRUFDZixJQUFJLEVBQUMsa0JBQWtCLEVBQ3ZCLFlBQVksRUFBRSxJQUFJLEdBQ2pCO1FBQ0Ysb0JBQUMsS0FBSyxDQUFDLElBQUksSUFDVixJQUFJLEVBQUMsUUFBUSxFQUNiLEtBQUssRUFBQyxRQUFRLEVBQ2QsSUFBSSxFQUFDLDZCQUE2QixHQUNqQztRQUNGLG9CQUFDLEtBQUssQ0FBQyxNQUFNLElBQ1osSUFBSSxFQUFDLFlBQVksRUFDakIsS0FBSyxFQUFDLFlBQVksRUFDbEIsSUFBSSxFQUFDLG9CQUFvQixHQUN4QjtRQUNGLG9CQUFDLEtBQUssQ0FBQyxRQUFRLElBQ2QsSUFBSSxFQUFDLE9BQU8sRUFDWixLQUFLLEVBQUMsT0FBTyxFQUNiLFlBQVksRUFBRSxLQUFLLEVBQ25CLElBQUksRUFBQyxzQ0FBc0MsR0FDMUM7UUFDRixvQkFBQyxLQUFLLENBQUMsUUFBUSxJQUNkLElBQUksRUFBQyxTQUFTLEVBQ2QsS0FBSyxFQUFDLFNBQVMsRUFDZixZQUFZLEVBQUUsS0FBSyxFQUNuQixJQUFJLEVBQUMsaUVBQWlFLEdBQ3JFLENBQ1csQ0FDZCxDQUFDO0FBQ0gsQ0FBQyJ9