import React from 'react';
import { DataLogConfig, NetworkTablesConfig } from "../../config";
import { BoundCheckbox, BoundSelect, Binding } from './bound';

interface DatalogConfigEdtiorProps {
	config?: DataLogConfig;
	onChange?(nt: DataLogConfig): void;
}

export default function DatalogConfigEdtior(props: DatalogConfigEdtiorProps) {
	const config = props.config ?? {};

	const Bound = Binding(config, props.onChange);
	return (
		<fieldset>
			<legend>Datalog</legend>
			<Bound.Checkbox name='enabled' label='Enabled' defaultValue={true} />
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
		</fieldset>
	);
}