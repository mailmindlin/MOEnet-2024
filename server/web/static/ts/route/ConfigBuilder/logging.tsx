import React from 'react';
import { LogConfig, NetworkTablesConfig } from "../../config";
import { BoundCheckbox, BoundSelect, Binding } from './bound';

interface LogConfigEditorProps {
	config?: LogConfig;
	onChange?(nt: LogConfig): void;
}

export default function LogConfigEditor(props: LogConfigEditorProps) {
	const config = props.config ?? {};

	const Bound = Binding(config, props.onChange);
	return (
		<fieldset>
			<legend>Logging</legend>
			<Bound.Select name='level' label='Log Level' defaultValue='ERROR'>
				<option value="DEBUG">Debug</option>
				<option value="INFO">Info</option>
				<option value="WARN">Warning</option>
				<option value="ERROR">Error</option>
				<option value="FATAL">Fatal</option>
			</Bound.Select>
		</fieldset>
	);
}