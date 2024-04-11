import React from 'react';
import { DataLogConfig } from "../../config";
import { BoundCheckbox, BoundSelect, Binding } from './bound';
import Collapsible from '../../components/Collapsible';

interface DatalogConfigEdtiorProps {
	config?: DataLogConfig;
	onChange?(nt: DataLogConfig): void;
}

export default function DatalogConfigEdtior(props: DatalogConfigEdtiorProps) {
	const config = props.config ?? {};
	
	const Bound = Binding(config, props.onChange);
	return (
		<Collapsible legend='Datalog'>
			<Bound.Checkbox
				name='enabled'
				label='Enabled'
				help='Enable data logs'
				defaultValue={true}
			/>
			<Bound.Text
				name='folder'
				label='Folder'
				help='Folder to save data logs in'
			/>
			<Bound.Number
				name='free_space'
				label='Free space'
				help='Minimum free space'
			/>
			<Bound.Checkbox
				name='mkdir'
				label='mkdir'
				defaultValue={false}
				help="Make log folder if it doesn't exist?"
			/>
			<Bound.Checkbox
				name='cleanup'
				label='Cleanup'
				defaultValue={false}
				help="Should we clean up old log files? (see free_space and max_logs)"
			/>
		</Collapsible>
	);
}