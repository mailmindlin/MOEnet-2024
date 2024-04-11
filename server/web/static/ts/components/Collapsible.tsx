import React from 'react';

interface Props {
    initialExpanded?: boolean;
    expanded?: boolean;
    legend?: React.ReactNode;
    children: React.ReactNode;
}

export default function Collapsible(props: Props) {
    var expanded: boolean;
    var toggleExpanded: (() => void) | undefined;
    if (typeof props.expanded === 'boolean') {
        expanded = props.expanded;
    } else {
        var [_expanded, setExpanded] = React.useState(props.initialExpanded ?? true);
        expanded = _expanded;
        toggleExpanded = React.useCallback(() => setExpanded(!expanded), [expanded, setExpanded]);
    }

	return (
		<fieldset className={expanded ? 'toggleAble expanded' : 'toggleAble'}>
			<legend onClick={toggleExpanded}>
                <span>{props.legend}</span>
            </legend>
			{ props.children }
		</fieldset>
	);
}