import React from 'react';
export default function Tooltip(props) {
    const disabled = props.disabled ?? false;
    if (props.help && !disabled) {
        return (React.createElement("span", { className: 'tooltip' },
            props.children,
            React.createElement("div", { className: 'tooltiptext' }, props.help)));
    }
    else {
        return props.children;
    }
}
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiVG9vbHRpcC5qcyIsInNvdXJjZVJvb3QiOiIiLCJzb3VyY2VzIjpbIi4uLy4uL3RzL2NvbXBvbmVudHMvVG9vbHRpcC50c3giXSwibmFtZXMiOltdLCJtYXBwaW5ncyI6IkFBQUEsT0FBTyxLQUFLLE1BQU0sT0FBTyxDQUFDO0FBUTFCLE1BQU0sQ0FBQyxPQUFPLFVBQVUsT0FBTyxDQUFDLEtBQVk7SUFDeEMsTUFBTSxRQUFRLEdBQUcsS0FBSyxDQUFDLFFBQVEsSUFBSSxLQUFLLENBQUM7SUFFNUMsSUFBSSxLQUFLLENBQUMsSUFBSSxJQUFJLENBQUMsUUFBUSxFQUFFLENBQUM7UUFDN0IsT0FBTyxDQUNOLDhCQUFNLFNBQVMsRUFBQyxTQUFTO1lBQ3ZCLEtBQUssQ0FBQyxRQUFRO1lBQ2YsNkJBQUssU0FBUyxFQUFDLGFBQWEsSUFBRSxLQUFLLENBQUMsSUFBSSxDQUFPLENBQ3pDLENBQ1AsQ0FBQTtJQUNGLENBQUM7U0FBTSxDQUFDO1FBQ1AsT0FBTyxLQUFLLENBQUMsUUFBUSxDQUFDO0lBQ3ZCLENBQUM7QUFDRixDQUFDIn0=