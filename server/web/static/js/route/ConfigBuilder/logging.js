import React from 'react';
import { Binding } from './bound';
import Collapsible from '../../components/Collapsible';
export default function LogConfigEditor(props) {
    const config = props.config ?? {};
    const Bound = Binding(config, props.onChange);
    return (React.createElement(Collapsible, { legend: 'Logging' },
        React.createElement(Bound.Select, { name: 'level', label: 'Log Level', defaultValue: 'ERROR' },
            React.createElement("option", { value: "DEBUG" }, "Debug"),
            React.createElement("option", { value: "INFO" }, "Info"),
            React.createElement("option", { value: "WARN" }, "Warning"),
            React.createElement("option", { value: "ERROR" }, "Error"),
            React.createElement("option", { value: "FATAL" }, "Fatal"))));
}
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoibG9nZ2luZy5qcyIsInNvdXJjZVJvb3QiOiIiLCJzb3VyY2VzIjpbIi4uLy4uLy4uL3RzL3JvdXRlL0NvbmZpZ0J1aWxkZXIvbG9nZ2luZy50c3giXSwibmFtZXMiOltdLCJtYXBwaW5ncyI6IkFBQUEsT0FBTyxLQUFLLE1BQU0sT0FBTyxDQUFDO0FBRTFCLE9BQU8sRUFBRSxPQUFPLEVBQUUsTUFBTSxTQUFTLENBQUM7QUFDbEMsT0FBTyxXQUFXLE1BQU0sOEJBQThCLENBQUM7QUFPdkQsTUFBTSxDQUFDLE9BQU8sVUFBVSxlQUFlLENBQUMsS0FBMkI7SUFDbEUsTUFBTSxNQUFNLEdBQUcsS0FBSyxDQUFDLE1BQU0sSUFBSSxFQUFFLENBQUM7SUFFbEMsTUFBTSxLQUFLLEdBQUcsT0FBTyxDQUFDLE1BQU0sRUFBRSxLQUFLLENBQUMsUUFBUSxDQUFDLENBQUM7SUFDOUMsT0FBTyxDQUNOLG9CQUFDLFdBQVcsSUFBQyxNQUFNLEVBQUMsU0FBUztRQUM1QixvQkFBQyxLQUFLLENBQUMsTUFBTSxJQUFDLElBQUksRUFBQyxPQUFPLEVBQUMsS0FBSyxFQUFDLFdBQVcsRUFBQyxZQUFZLEVBQUMsT0FBTztZQUNoRSxnQ0FBUSxLQUFLLEVBQUMsT0FBTyxZQUFlO1lBQ3BDLGdDQUFRLEtBQUssRUFBQyxNQUFNLFdBQWM7WUFDbEMsZ0NBQVEsS0FBSyxFQUFDLE1BQU0sY0FBaUI7WUFDckMsZ0NBQVEsS0FBSyxFQUFDLE9BQU8sWUFBZTtZQUNwQyxnQ0FBUSxLQUFLLEVBQUMsT0FBTyxZQUFlLENBQ3RCLENBRUYsQ0FDZCxDQUFDO0FBQ0gsQ0FBQyJ9