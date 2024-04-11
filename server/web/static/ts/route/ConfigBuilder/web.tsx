import React from 'react';
import { WebConfig } from "../../config";
import { Binding } from './bound';
import Collapsible from '../../components/Collapsible';

interface WebConfigEditorProps {
	config?: WebConfig;
	onChange?(nt: WebConfig): void;
}

export default function WebConfigEditor(props: WebConfigEditorProps) {
	const config = props.config ?? {};

	const Bound = Binding(config, props.onChange);
	return (
		<Collapsible legend='Web Server'>
			<Bound.Checkbox name='enabled' label='Enabled' defaultValue={true} />
			<Bound.Text name='host' label='Host' placeholder='localhost' />
			<Bound.Number name='port' label='Port' defaultValue={8080} min={1} max={65536} />
		</Collapsible>
	);
}