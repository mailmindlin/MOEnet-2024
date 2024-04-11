import React from 'react';
import { EstimatorConfig } from "../../config";
import { Binding } from './bound';
import Collapsible from '../../components/Collapsible';

interface EstimatorConfigEditorProps {
	config?: EstimatorConfig;
	onChange?(config: EstimatorConfig): void;
}

export default function EstimatorConfigEditor(props: EstimatorConfigEditorProps) {
	const config = props.config ?? {};

	const ObjectDetection = Binding(config?.detections ?? {}, props.onChange ? detections => props.onChange!({...config, detections }) : undefined);
	const PoseEstimator = Binding(config?.pose ?? {}, props.onChange ? pose => props.onChange!({...config, pose }) : undefined);
	return (
		<Collapsible legend='Data Fusion'>
			<fieldset>
				<legend>Object Detections</legend>
				<ObjectDetection.Number
					name='min_detections'
					label='Minimum Detections'
					defaultValue={0}
					min={0}
					help="Minimum times to detect an object before 'seeing' it"
				/>
				<ObjectDetection.Number
					name='clustering_distance'
					label='Clustering Distance'
					min={0}
					defaultValue={0.1}
					step='any'
					help=""
				/>
				<ObjectDetection.Number
					name='min_depth'
					label='Min Depth'
					defaultValue={0}
					min={0}
					step='any'
				/>
				<ObjectDetection.Number
					name='alpha'
					label='Alpha'
					defaultValue={0.2}
					step='any'
					min={0}
					max={1}
				/>
			</fieldset>
			<fieldset>
				<legend>Pose Estimation</legend>
				<PoseEstimator.Select name='apriltagStrategy' label='Algorithm' defaultValue=''>
					<option>Simple 2d</option>
					<option>Simple 2d</option>
					<option disabled>GTSAM</option>
				</PoseEstimator.Select>
				<PoseEstimator.Checkbox name='force2d' label='Force 2d' defaultValue={true} help="Should we force the pose to fit on the field?"/>
				{config?.pose?.force2d && <>
					
				</>}
				<PoseEstimator.Select name='apriltagStrategy' label='AprilTag strategy' defaultValue='LOWEST_AMBIGUITY'>
					<option value="LOWEST_AMBIGUITY">Lowest ambiguity</option>
					<option value="CLOSEST_TO_LAST_POSE">Closest to last pose</option>
					<option value="AVERAGE_BEST_TARGETS">Average best targets</option>
				</PoseEstimator.Select>
			</fieldset>
		</Collapsible>
	);
}