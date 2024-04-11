import React from 'react';
import { NetworkTablesConfig } from "../../config";
import { Binding } from './bound';
import Collapsible from '../../components/Collapsible';

interface NetworkTablesEditorProps {
	nt?: NetworkTablesConfig;
	onChange?(nt: NetworkTablesConfig): void;
}

export default function NetworkTablesEditor(props: NetworkTablesEditorProps) {
	const nt = props.nt ?? {};

	const Bound = Binding(nt, props.onChange);
	return (
		<Collapsible legend='NetworkTables'>
			<Bound.Checkbox name='enabled' label='Enabled' defaultValue={true} />
			<Bound.Number
				name='team'
				label='Team'
				min={1}
				max={9999}
				defaultValue={365}
				help='Team number'
			/>
			<Bound.Number
				name='port'
				label='Port'
				min={1}
				defaultValue={5810}
				help='NetworkTables port number (default NT4: 5810)'
			/>
			<Bound.Text
				name='host'
				label='Host'
				placeholder='(Autodetect)'
				help="NetworkTables host address"
			/>
			<Bound.Text
				name='client_id'
				label='Client Id'
				placeholder='moenet'
				help='ID to connect to NetworkTables with'
			/>
			<Bound.Select name='log_level' label='Log Level' defaultValue='error'>
				<option value="debug">Debug</option>
				<option value="info">Info</option>
				<option value="warning">Warning</option>
				<option value="error">Error</option>
				<option value="fatal">Fatal</option>
			</Bound.Select>
			<fieldset>
				<legend>Subscriptions</legend>
				<Bound.Checkbox
					name='subscribeSleep' label='Sleep'
					defaultValue={true}
					help={<>Should we listen for sleep control at <code>/moenet/rio_request_sleep</code>?</>}
				/>
				<Bound.Checkbox
					name='subscribePoseOverride' label='Pose Override'
					defaultValue={true}
					help='Allow the Rio to override poses'
				/>
				<Bound.Checkbox
					name='subscribeConfig'
					label='Config'
					defaultValue={true}
					help={<>Should we listen for config updates at <code>/moenet/rio_dynamic_config</code>?</>}
				/>
			</fieldset>
			<fieldset>
				<legend>Publications</legend>
				<Bound.Checkbox name='publishLog' label='Log' defaultValue={true}/>
				<Bound.Checkbox name='publishPing' label='Ping' defaultValue={true}/>
				<Bound.Checkbox name='publishErrors' label='Errors' defaultValue={true}/>
				<Bound.Checkbox name='publishStatus' label='Status' defaultValue={true}/>
				<Bound.Checkbox name='publishConfig' label='Config' defaultValue={true}/>
				<Bound.Checkbox name='publishSystemInfo' label='System Info' defaultValue={true}/>
				<Bound.Checkbox name='publishDetections' label='Object Detections' defaultValue={true}/>
			</fieldset>
			<fieldset>
				<legend>Transforms</legend>
				<Bound.Select name='tfFieldToOdom' label='Field &rarr; Odometry'>
					<option value="$false">Disabled</option>
					<option value="sub">Subscrbibe</option>
					<option value="pub">Publish</option>
				</Bound.Select>
				<Bound.Select name='tfFieldToRobot' label='Field&rarr;Robot'>
					<option value="$false">Disabled</option>
					<option value="sub">Subscrbibe</option>
					<option value="pub">Publish</option>
				</Bound.Select>
				<Bound.Select name='tfOdomToRobot' label='Odometry&rarr;Robot'>
					<option value="$false">Disabled</option>
					<option value="sub">Subscrbibe</option>
					<option value="pub">Publish</option>
				</Bound.Select>
			</fieldset>
			<fieldset>
				<legend>Field2d</legend>
				<Bound.Checkbox name='publishField2dF2O' label='Field&rarr;Odometry' defaultValue={false}/>
				<Bound.Checkbox name='publishField2dF2R' label='Field&rarr;Robot' defaultValue={false}/>
				<Bound.Checkbox name='publishField2dDets' label='Field&rarr;Detections' defaultValue={false}/>
			</fieldset>
		</Collapsible>
	);
}