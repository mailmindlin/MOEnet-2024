import React from 'react';
import { LogConfig } from "../../config";
import { Binding } from './bound';
import Collapsible from '../../components/Collapsible';

interface LogConfigEditorProps {
	config?: LogConfig;
	onChange?(nt: LogConfig): void;
}

export default function LogConfigEditor(props: LogConfigEditorProps) {
	const config = props.config ?? {};

	const Bound = Binding(config, props.onChange);
	return (
		<Collapsible legend='Logging'>
			<Bound.Select name='level' label='Log Level' defaultValue='ERROR'>
				<option value="DEBUG">Debug</option>
				<option value="INFO">Info</option>
				<option value="WARN">Warning</option>
				<option value="ERROR">Error</option>
				<option value="FATAL">Fatal</option>
			</Bound.Select>
			
		</Collapsible>
	);
}