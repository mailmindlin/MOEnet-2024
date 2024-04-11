import React from 'react';

interface Props {
    disabled?: boolean;
    help?: React.ReactNode;
    children: React.ReactNode;
}

export default function Tooltip(props: Props) {
    const disabled = props.disabled ?? false;

	if (props.help && !disabled) {
		return (
			<span className='tooltip'>
				{props.children}
				<div className='tooltiptext'>{props.help}</div>
			</span>
		)
	} else {
		return props.children;
	}
}