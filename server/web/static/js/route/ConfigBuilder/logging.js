import React from 'react';
import { Binding } from './bound';
export default function LogConfigEditor(props) {
    const config = props.config ?? {};
    const Bound = Binding(config, props.onChange);
    return (React.createElement("fieldset", null,
        React.createElement("legend", null, "Logging"),
        React.createElement(Bound.Select, { name: 'level', label: 'Log Level', defaultValue: 'ERROR' },
            React.createElement("option", { value: "DEBUG" }, "Debug"),
            React.createElement("option", { value: "INFO" }, "Info"),
            React.createElement("option", { value: "WARN" }, "Warning"),
            React.createElement("option", { value: "ERROR" }, "Error"),
            React.createElement("option", { value: "FATAL" }, "Fatal"))));
}
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoibG9nZ2luZy5qcyIsInNvdXJjZVJvb3QiOiIiLCJzb3VyY2VzIjpbIi4uLy4uLy4uL3RzL3JvdXRlL0NvbmZpZ0J1aWxkZXIvbG9nZ2luZy50c3giXSwibmFtZXMiOltdLCJtYXBwaW5ncyI6IkFBQUEsT0FBTyxLQUFLLE1BQU0sT0FBTyxDQUFDO0FBRTFCLE9BQU8sRUFBOEIsT0FBTyxFQUFFLE1BQU0sU0FBUyxDQUFDO0FBTzlELE1BQU0sQ0FBQyxPQUFPLFVBQVUsZUFBZSxDQUFDLEtBQTJCO0lBQ2xFLE1BQU0sTUFBTSxHQUFHLEtBQUssQ0FBQyxNQUFNLElBQUksRUFBRSxDQUFDO0lBRWxDLE1BQU0sS0FBSyxHQUFHLE9BQU8sQ0FBQyxNQUFNLEVBQUUsS0FBSyxDQUFDLFFBQVEsQ0FBQyxDQUFDO0lBQzlDLE9BQU8sQ0FDTjtRQUNDLDhDQUF3QjtRQUN4QixvQkFBQyxLQUFLLENBQUMsTUFBTSxJQUFDLElBQUksRUFBQyxPQUFPLEVBQUMsS0FBSyxFQUFDLFdBQVcsRUFBQyxZQUFZLEVBQUMsT0FBTztZQUNoRSxnQ0FBUSxLQUFLLEVBQUMsT0FBTyxZQUFlO1lBQ3BDLGdDQUFRLEtBQUssRUFBQyxNQUFNLFdBQWM7WUFDbEMsZ0NBQVEsS0FBSyxFQUFDLE1BQU0sY0FBaUI7WUFDckMsZ0NBQVEsS0FBSyxFQUFDLE9BQU8sWUFBZTtZQUNwQyxnQ0FBUSxLQUFLLEVBQUMsT0FBTyxZQUFlLENBQ3RCLENBQ0wsQ0FDWCxDQUFDO0FBQ0gsQ0FBQyJ9