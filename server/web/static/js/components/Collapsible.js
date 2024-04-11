import React from 'react';
export default function Collapsible(props) {
    var expanded;
    var toggleExpanded;
    if (typeof props.expanded === 'boolean') {
        expanded = props.expanded;
    }
    else {
        var [_expanded, setExpanded] = React.useState(props.initialExpanded ?? true);
        expanded = _expanded;
        toggleExpanded = React.useCallback(() => setExpanded(!expanded), [expanded, setExpanded]);
    }
    return (React.createElement("fieldset", { className: expanded ? 'toggleAble expanded' : 'toggleAble' },
        React.createElement("legend", { onClick: toggleExpanded },
            React.createElement("span", null, props.legend)),
        props.children));
}
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiQ29sbGFwc2libGUuanMiLCJzb3VyY2VSb290IjoiIiwic291cmNlcyI6WyIuLi8uLi90cy9jb21wb25lbnRzL0NvbGxhcHNpYmxlLnRzeCJdLCJuYW1lcyI6W10sIm1hcHBpbmdzIjoiQUFBQSxPQUFPLEtBQUssTUFBTSxPQUFPLENBQUM7QUFTMUIsTUFBTSxDQUFDLE9BQU8sVUFBVSxXQUFXLENBQUMsS0FBWTtJQUM1QyxJQUFJLFFBQWlCLENBQUM7SUFDdEIsSUFBSSxjQUF3QyxDQUFDO0lBQzdDLElBQUksT0FBTyxLQUFLLENBQUMsUUFBUSxLQUFLLFNBQVMsRUFBRSxDQUFDO1FBQ3RDLFFBQVEsR0FBRyxLQUFLLENBQUMsUUFBUSxDQUFDO0lBQzlCLENBQUM7U0FBTSxDQUFDO1FBQ0osSUFBSSxDQUFDLFNBQVMsRUFBRSxXQUFXLENBQUMsR0FBRyxLQUFLLENBQUMsUUFBUSxDQUFDLEtBQUssQ0FBQyxlQUFlLElBQUksSUFBSSxDQUFDLENBQUM7UUFDN0UsUUFBUSxHQUFHLFNBQVMsQ0FBQztRQUNyQixjQUFjLEdBQUcsS0FBSyxDQUFDLFdBQVcsQ0FBQyxHQUFHLEVBQUUsQ0FBQyxXQUFXLENBQUMsQ0FBQyxRQUFRLENBQUMsRUFBRSxDQUFDLFFBQVEsRUFBRSxXQUFXLENBQUMsQ0FBQyxDQUFDO0lBQzlGLENBQUM7SUFFSixPQUFPLENBQ04sa0NBQVUsU0FBUyxFQUFFLFFBQVEsQ0FBQyxDQUFDLENBQUMscUJBQXFCLENBQUMsQ0FBQyxDQUFDLFlBQVk7UUFDbkUsZ0NBQVEsT0FBTyxFQUFFLGNBQWM7WUFDbEIsa0NBQU8sS0FBSyxDQUFDLE1BQU0sQ0FBUSxDQUN0QjtRQUNoQixLQUFLLENBQUMsUUFBUSxDQUNOLENBQ1gsQ0FBQztBQUNILENBQUMifQ==