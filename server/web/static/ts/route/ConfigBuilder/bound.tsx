import React, { ChangeEvent } from 'react';

export function Binding<V>(value: V, onChange?: (next: V) => void) {
	// This is a pain, but we need to do this to keep the return type constant
	const vRef = React.useRef({value, onChange});
	vRef.current = {value, onChange};

	return React.useMemo(() => {
		function Checkbox<K extends keyof V>(props: Omit<BoundCheckboxProps<V, K>, 'value' | 'onChange'>) {
			return BoundCheckbox({
				...props,
				...vRef.current,
			});
		}
		function Select<K extends keyof V>(props: Omit<BoundSelectProps<V, K>, 'value' | 'onChange'>) {
			return BoundSelect({
				...props,
				...vRef.current,
			});
		}
		function Number<K extends keyof V>(props: Omit<BoundNumericInputProps<V, K>, 'value' | 'onChange'>) {
			return BoundNumericInput({
				...props,
				...vRef.current,
			});
		}
		function Text<K extends keyof V>(props: Omit<BoundTextInputProps<V, K>, 'value' | 'onChange'>) {
			return BoundTextInput({
				...props,
				...vRef.current,
			})
		}
		return {
			Checkbox,
			Select,
			Number,
			Text,
		};
	}, [vRef]);
}


type UpdateCallback<V> = ((next: V) => void) | ((cb: ((next: V) => V) | V) => void);
export function bindChangeHandler<V, K extends keyof V>(value: V, key: K, onChange?: UpdateCallback<V>, nullable?: boolean): ((next: ChangeEvent<any> | V[K]) => void) | undefined {
	if (!onChange)
		return React.useCallback(undefined as any, [onChange, value]);
	
	return React.useCallback((e: ChangeEvent<HTMLInputElement> | V[K]) => {
		let kv: any = e;
		if ((e as ChangeEvent).currentTarget) {
			const ct = (e as ChangeEvent<HTMLInputElement>).currentTarget;
			if (!ct.checkValidity()) {
				ct.reportValidity();
			}
			switch (ct.type) {
				case 'number':
					kv = ct.valueAsNumber;
					if (Number.isNaN(kv))
						kv = null;
					break;
				case 'checkbox':
					kv = ct.checked;
					break;
				default:
					kv = ct.value;
			}
			if (kv === '$null' || (nullable && kv == ''))
				kv = null;
			console.log(kv);
		}
		console.log('onChange', onChange, key, value, kv);
		onChange!({
			...value,
			[key]: kv,
		});
	}, [onChange, value]);
}

interface BoundSelectProps<V, K extends keyof V> {
	label: string;
	value: V;
	name: K;
	disabled?: boolean;
	defaultValue?: string;
	onChange?(value: V): void;
	children: React.ReactNode;
	nullable?: boolean;
}

export function BoundSelect<V, K extends keyof V>(props: BoundSelectProps<V, K>) {
	const id = React.useId();

	const disabled = (!props.onChange) || props.disabled;

	return (<div>
		<label htmlFor={id}>{props.label}&nbsp;</label>
		<select
			id={id}
			value={props.value[props.name] as string ?? ''}
			disabled={disabled}
			onChange={bindChangeHandler(props.value, props.name, props.onChange)}
		>
			{props.children}
		</select>
	</div>);
}

function Tooltip(props: { help?: React.ReactNode; children: React.ReactNode }) {
	if (props.help) {
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

interface BoundNumericInputProps<V, K extends keyof V> {
	label: string;
	value: V;
	name: K;
	disabled?: boolean;
	defaultValue?: number;
	help?: React.ReactNode;
	onChange?(value: V): void;
	step?: number | 'any';
	min?: number;
	max?: number;
	nullable?: boolean;
}

export function BoundNumericInput<V, K extends keyof V>(props: BoundNumericInputProps<V, K>) {
	const id = React.useId()

	const disabled = (!props.onChange) || props.disabled;

	{
		const {
			label, value, name, disabled, defaultValue, onChange, help, nullable,
			...extraProps1
		} = props;
		var extraProps = extraProps1;
	}

	const changeHandler = bindChangeHandler(props.value, props.name, props.onChange, props.nullable);

	return (<div>
		<Tooltip help={props.help}>
			<label htmlFor={id}>{props.label}&nbsp;</label>
			<input
				id={id}
				type='number'
				inputMode='numeric'
				value={props.value[props.name] as number | undefined ?? ''}
				placeholder={props.defaultValue ? `${props.defaultValue}` : undefined}
				disabled={disabled}
				onChange={changeHandler}
				{...extraProps}
			/>
		</Tooltip>
	</div>);
}

interface BoundTextInputProps<V, K extends keyof V> {
	label: string;
	value: V;
	name: K;
	disabled?: boolean;
	placeholder?: string;
	help?: React.ReactNode;
	nullable?: boolean;
	onChange?: UpdateCallback<V>;
}

export function BoundTextInput<V, K extends keyof V>(props: BoundTextInputProps<V, K>) {
	const id = React.useId();

	const disabled = (!props.onChange) || props.disabled;

	{
		const {
			label, value, name, disabled, placeholder: defaultValue, onChange, help, nullable,
			...extraProps1
		} = props;
		var extraProps = extraProps1;
	}

	return (<div>
		<Tooltip help={props.help}>
			<label htmlFor={id}>{props.label}&nbsp;</label>
			<input
				id={id}
				type='text'
				value={props.value[props.name] as string | undefined ?? ''}
				placeholder={props.placeholder}
				disabled={disabled}
				onChange={bindChangeHandler(props.value, props.name, props.onChange, props.nullable)}
				{...extraProps}
			/>
		</Tooltip>
	</div>);
}

export function Collapsible(props: { children: React.ReactNode, legend?: React.ReactNode }) {
	const [expanded, setExpanded] = React.useState(true);

	let legend = (<legend onClick={() => setExpanded(!expanded)}>
		<span>{props.legend}</span>
	</legend>)

	return (
		<fieldset className={expanded ? 'toggleAble expanded' : 'toggleAble'}>
			{ legend }
			{ props.children }
		</fieldset>
	)
}

interface BoundCheckboxProps<V, K extends keyof V> {
	label: string;
	value: V;
	name: K;
	disabled?: boolean;
	help?: string | React.ReactNode;
	defaultValue?: boolean;
	onChange?(value: V): void;
}
export function BoundCheckbox<V, K extends keyof V>(props: BoundCheckboxProps<V, K>) {
	const id = React.useId()

	const disabled = (!props.onChange) || props.disabled;

	return (<div>
		<Tooltip help={props.help}>
			<label htmlFor={id}>{props.label}&nbsp;</label>
			<input
				type='checkbox'
				id={id}
				checked={props.value[props.name] as boolean ?? props.defaultValue ?? false}
				disabled={disabled}
				onChange={bindChangeHandler(props.value, props.name, props.onChange)}
			/>
		</Tooltip>
	</div>);
}