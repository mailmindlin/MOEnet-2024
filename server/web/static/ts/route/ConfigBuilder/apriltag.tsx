import React, { ChangeEvent } from 'react';
import { AprilTagFieldInlineWpi, AprilTagFieldRefWpi, Apriltags, FieldLayout } from '../../config';
import { BoundNumericInput, BoundSelect, BoundTextInput } from './bound';
import { boundReplaceKey } from './ds';

interface Props {
	value: Apriltags,
	onChange?(value: Apriltags): void;
}

function FieldDimsEditor(props: { value: FieldLayout, onChange?(value: FieldLayout): void}) {
	return (
		<fieldset>
			<legend>Field Dimensions</legend>
			<BoundNumericInput
				value={props.value}
				onChange={props.onChange}
				name='length'
				label='Length (meters)'
				min={0}
				step='any'
			/>
			<BoundNumericInput
				value={props.value}
				onChange={props.onChange}
				name='width'
				label='Width (meters)'
				min={0}
				step='any'
			/>
		</fieldset>
	)
}

export function AprilTagFieldSelector(props: Props) {
	const { onChange } = props;
	const handleFormatChange = React.useCallback(onChange ? (e: ChangeEvent<HTMLSelectElement>) => {
		switch (e.currentTarget.value) {
			case 'wpi_int':
				onChange({
					format: 'wpi',
					field: {
						length: 0,
						width: 0,
					},
					tags: [],
					tagFamily: 'tag16h5',
					tagSize: 1.0
				});
				break;
			case 'sai_int':
				onChange({
					format: 'sai',
					field: {
						length: 0,
						width: 0,
					},
					tags: [],
				});
				break;
			case 'wpi_ext':
				onChange({
					format: 'wpi',
					path: '',
					tagFamily: 'tag16h5',
					tagSize: 1.0
				});
				break;
			case 'sai_ext':
				onChange({
					format: 'sai',
					field: {
						length: 0,
						width: 0,
					},
					path: '',
				});
				break;
			case '2024Crescendo':
			case '2023ChargedUp':
			case '2022RapidReact':
				onChange(e.currentTarget.value);
				break;
		}
	} : (undefined as any), [onChange]);
	const format = typeof props.value === 'string' ? props.value : `${props.value.format}_${'path' in props.value ? 'ext' : 'int'}`;

	const inner = [];
	const { value } = props;
	if (typeof value === 'string') {
		// Skip
	} else {
		// const internal = 'path' in value;
		if (value.format === 'wpi') {
			const c: ((value: AprilTagFieldInlineWpi | AprilTagFieldRefWpi) => void) | undefined = onChange;
			inner.push(
				<BoundNumericInput value={value} name='tagSize' onChange={c} label='Tag Size (meters)' min={0} step='any' />,
				<BoundSelect
					value={value} onChange={c}
					name='tagFamily'
					label='AprilTag family'
				>
					<option value="tag16h5">tag16h5</option>
					<option value="tag25h9">tag25h9</option>
					<option value="tag36h10">tag36h10</option>
					<option value="tag36h11">tag36h11</option>
					<option value="tagCircle21h7">tagCircle21h7</option>
					<option value="tagStandard41h12">tagStandard41h12</option>
				</BoundSelect>
			);
			if ('path' in value) {
				inner.push(<BoundTextInput value={value} name='path' onChange={onChange} label='Path' />)
			} else {
				inner.push(<FieldDimsEditor value={value.field} onChange={boundReplaceKey('field', value, onChange)} />);
				//TODO: tag editor
			}
		} else if (value.format === 'sai') {
			if ('path' in value) {
				inner.push(<BoundTextInput value={value} name='path' onChange={onChange} label='Path' />)
			} else {
				//TODO: tag editor
			}
			inner.push(<FieldDimsEditor value={value.field} onChange={boundReplaceKey('field', value, onChange)} />);
		}
	}

	const atId = React.useId()

	return (
		<fieldset>
			<legend>AprilTags</legend>
			<label htmlFor={atId}>Format</label>
			<select
				id={atId}
				value={format}
				onChange={handleFormatChange}
			>
				<optgroup label='WPIlib Internal'>
					<option value="2024Crescendo">Crescendo (2024)</option>
					<option value="2023ChargedUp">Charged Up (2023)</option>
					<option value="2022RapidReact">Rapid React (2022)</option>
				</optgroup>
				<optgroup label="Inline">
					<option value="wpi_int">WPI (inline)</option>
					<option value="sai_int">SpectacularAI (inline)</option>
				</optgroup>
				<optgroup label="External File">
					<option value="wpi_ext">WPI (external)</option>
					<option value="sai_ext">SpectacularAI (external)</option>
				</optgroup>
			</select>
			{...inner}
		</fieldset>
	)
}