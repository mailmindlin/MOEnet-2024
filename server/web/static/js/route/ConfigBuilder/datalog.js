import React from 'react';
import { Binding } from './bound';
export default function DatalogConfigEdtior(props) {
    const config = props.config ?? {};
    const Bound = Binding(config, props.onChange);
    return (React.createElement("fieldset", null,
        React.createElement("legend", null, "Datalog"),
        React.createElement(Bound.Checkbox, { name: 'enabled', label: 'Enabled', defaultValue: true }),
        React.createElement(Bound.Checkbox, { name: 'mkdir', label: 'mkdir', defaultValue: false, help: "Make log folder if it doesn't exist?" }),
        React.createElement(Bound.Checkbox, { name: 'cleanup', label: 'Cleanup', defaultValue: false, help: "Should we clean up old log files? (see free_space and max_logs)" })));
}
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiZGF0YWxvZy5qcyIsInNvdXJjZVJvb3QiOiIiLCJzb3VyY2VzIjpbIi4uLy4uLy4uL3RzL3JvdXRlL0NvbmZpZ0J1aWxkZXIvZGF0YWxvZy50c3giXSwibmFtZXMiOltdLCJtYXBwaW5ncyI6IkFBQUEsT0FBTyxLQUFLLE1BQU0sT0FBTyxDQUFDO0FBRTFCLE9BQU8sRUFBOEIsT0FBTyxFQUFFLE1BQU0sU0FBUyxDQUFDO0FBTzlELE1BQU0sQ0FBQyxPQUFPLFVBQVUsbUJBQW1CLENBQUMsS0FBK0I7SUFDMUUsTUFBTSxNQUFNLEdBQUcsS0FBSyxDQUFDLE1BQU0sSUFBSSxFQUFFLENBQUM7SUFFbEMsTUFBTSxLQUFLLEdBQUcsT0FBTyxDQUFDLE1BQU0sRUFBRSxLQUFLLENBQUMsUUFBUSxDQUFDLENBQUM7SUFDOUMsT0FBTyxDQUNOO1FBQ0MsOENBQXdCO1FBQ3hCLG9CQUFDLEtBQUssQ0FBQyxRQUFRLElBQUMsSUFBSSxFQUFDLFNBQVMsRUFBQyxLQUFLLEVBQUMsU0FBUyxFQUFDLFlBQVksRUFBRSxJQUFJLEdBQUk7UUFDckUsb0JBQUMsS0FBSyxDQUFDLFFBQVEsSUFDZCxJQUFJLEVBQUMsT0FBTyxFQUNaLEtBQUssRUFBQyxPQUFPLEVBQ2IsWUFBWSxFQUFFLEtBQUssRUFDbkIsSUFBSSxFQUFDLHNDQUFzQyxHQUMxQztRQUNGLG9CQUFDLEtBQUssQ0FBQyxRQUFRLElBQ2QsSUFBSSxFQUFDLFNBQVMsRUFDZCxLQUFLLEVBQUMsU0FBUyxFQUNmLFlBQVksRUFBRSxLQUFLLEVBQ25CLElBQUksRUFBQyxpRUFBaUUsR0FDckUsQ0FDUSxDQUNYLENBQUM7QUFDSCxDQUFDIn0=