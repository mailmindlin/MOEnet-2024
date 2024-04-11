import React, { ChangeEvent } from 'react';
import Tooltip from '../../components/Tooltip';

type FilterKeys<V extends object, T> = Exclude<{ [k in keyof V]: V[k] extends T | null | undefined ? k : never }[keyof V], undefined>;

export interface Binding<V extends object> {
	Checkbox<K extends FilterKeys<V, boolean>>(props: Omit<BoundCheckboxProps<V, K>, 'value' | 'onChange'>): JSX.Element;
	Select<K extends FilterKeys<V, string>>(props: Omit<BoundSelectProps<V, K>, 'value' | 'onChange'>): JSX.Element;
	Number<K extends FilterKeys<V, number>>(props: Omit<BoundNumericInputProps<V, K>, 'value' | 'onChange'>): JSX.Element;
	Text<K extends FilterKeys<V, string>>(props: Omit<BoundTextInputProps<V, K>, 'value' | 'onChange'>): JSX.Element;
}

export function Binding<V extends object>(value: V, onChange?: (next: V) => void): Binding<V> {
	// This is a pain, but we need to do this to keep the return type constant
	const vRef = React.useRef({value, onChange});
	vRef.current = {value, onChange};

	return React.useMemo(() => {
		function Checkbox<K extends FilterKeys<V, boolean>>(props: Omit<BoundCheckboxProps<V, K>, 'value' | 'onChange'>) {
			return BoundCheckbox({
				...props,
				...vRef.current,
			});
		}
		function Select<K extends FilterKeys<V, string>>(props: Omit<BoundSelectProps<V, K>, 'value' | 'onChange'>) {
			return BoundSelect({
				...props,
				...vRef.current,
			});
		}
		function Number<K extends FilterKeys<V, number>>(props: Omit<BoundNumericInputProps<V, K>, 'value' | 'onChange'>) {
			return BoundNumericInput({
				...props,
				...vRef.current,
			});
		}
		function Text<K extends FilterKeys<V, string>>(props: Omit<BoundTextInputProps<V, K>, 'value' | 'onChange'>) {
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

export function bindChangeHandler<V extends object, T, E, A extends any[]>(value: V, key: FilterKeys<V, T>, onChange: UpdateCallback<V> | undefined, mapper: (raw: E, ...arg1: A) => T, ...mapperArgs: A): ((next: E) => void) | undefined {
	if (!onChange)
		return React.useCallback(undefined as any, [onChange, value]);
	
	return React.useCallback((e: E) => {
		let kv;
		try {
			kv = mapper(e, ...mapperArgs);
		} catch (e) {
			if (e instanceof RangeError)
				return;
			throw e;
		}

		onChange!({
			...value,
			[key]: kv,
		});
	}, [onChange, value]);
}

interface BoundSelectProps<V extends object, K extends FilterKeys<V, string>> {
	label: React.ReactNode;
	/** Current (parent) value */
	value: V;
	/** Key in parent */
	name: K;
	disabled?: boolean;
	defaultValue?: string;
	onChange?(value: V): void;
	children: React.ReactNode;
	nullable?: boolean;
}

function handleSelectChange<T>(e: ChangeEvent<HTMLSelectElement>, nullable: boolean | undefined): T {
	const ct = e.currentTarget;
	if (!ct.checkValidity()) {
		ct.reportValidity();
		throw new RangeError();
	}

	nullable ??= false;
	let value: string | null = ct.value;
	if (nullable) {
		switch (value) {
			case '$null':
			case '$undefined':
				value = null;
				break;
		}
	}
	return value as T;
}

export function BoundSelect<V extends object, K extends FilterKeys<V, string>>(props: BoundSelectProps<V, K>) {
	const id = React.useId();

	const disabled = (!props.onChange) || props.disabled;

	return (<div>
		<label htmlFor={id}>{props.label}&nbsp;</label>
		<select
			id={id}
			value={props.value[props.name] as string ?? ''}
			disabled={disabled}
			onChange={bindChangeHandler(props.value, props.name, props.onChange, handleSelectChange, props.nullable)}
		>
			{props.children}
		</select>
	</div>);
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

function handleNumericChange<T>(e: ChangeEvent<HTMLInputElement>, nullable: boolean): T {
	const ct = e.currentTarget;
	if (!ct.checkValidity()) {
		ct.reportValidity();
		throw new RangeError();
	}

	nullable ??= false;
	if ((nullable ?? false) && ct.value === '')
		return (null as any);

	const value = ct.valueAsNumber;
	return value as T;
}

export function BoundNumericInput<V extends object, K extends FilterKeys<V, number>>(props: BoundNumericInputProps<V, K>) {
	const id = React.useId()

	const disabled = (!props.onChange) || props.disabled;

	{
		const {
			label, value, name, disabled, defaultValue, onChange, help, nullable,
			...extraProps1
		} = props;
		var extraProps = extraProps1;
	}

	const changeHandler = bindChangeHandler(props.value, props.name, props.onChange, handleNumericChange, props.nullable ?? false);

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

interface BoundTextInputProps<V extends object, K extends FilterKeys<V, string>> {
	label: string;
	value: V;
	name: K;
	disabled?: boolean;
	placeholder?: string;
	help?: React.ReactNode;
	nullable?: boolean;
	onChange?: UpdateCallback<V>;
}

function handleTextChange<T>(e: ChangeEvent<HTMLInputElement>, nullable: boolean): T {
	const ct = e.currentTarget;
	if (!ct.checkValidity()) {
		ct.reportValidity();
		throw new RangeError();
	}

	if (nullable && ct.value === '')
		return (null as any);

	return (ct.value) as T;
}

export function BoundTextInput<V extends object, K extends FilterKeys<V, string>>(props: BoundTextInputProps<V, K>) {
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
				onChange={bindChangeHandler(props.value, props.name, props.onChange, handleTextChange, props.nullable ?? false)}
				{...extraProps}
			/>
		</Tooltip>
	</div>);
}

interface BoundCheckboxProps<V extends object, K extends FilterKeys<V, boolean>> {
	label: string;
	value: V;
	name: K;
	disabled?: boolean;
	help?: string | React.ReactNode;
	defaultValue?: boolean;
	onChange?(value: V): void;
}

function handleCheckboxChange(e: ChangeEvent<HTMLInputElement>): any {
	const ct = e.currentTarget;
	return ct.checked;
}

export function BoundCheckbox<V extends object, K extends FilterKeys<V, boolean>>(props: BoundCheckboxProps<V, K>) {
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
				onChange={bindChangeHandler(props.value, props.name, props.onChange, handleCheckboxChange)}
			/>
		</Tooltip>
	</div>);
}

export interface BoundListRenderItemProps<E> {
	index: number;
	item: E;
	onChange?(next: E): void;
	onDelete?(): void
}

interface BoundListItemProps<E> {
	disabled?: boolean;
	index: number;

	value: E;
	renderItem(props: BoundListRenderItemProps<E>): JSX.Element;
	onChange?(index: number, value: E): void;
	onDelete?(index: number): void;
}

function BoundListItem<E>(props: BoundListItemProps<E>) {
	const { onChange, onDelete, index, value } = props;
	const _onChange = React.useCallback((next: E) => onChange?.(index, next), [onChange, value]);
	const _onDelete = React.useCallback(() => onDelete?.(index), [onDelete, index]);

	return props.renderItem({
		item: value,
		index: index,
		onChange: onChange ? _onChange : undefined,
		onDelete: onDelete ? _onDelete : undefined,
	})
}
interface BoundListProps<E> {
	value: E[];
	disabled?: boolean;
	canDelete?: boolean;

	renderItem(props: BoundListRenderItemProps<E>): JSX.Element;
	onChange?(value: E[]): void;
}

export function BoundList<E>(props: BoundListProps<E>) {

	const {
		onChange,
		value,
	} = props;

	const canChange = (!onChange) || props.disabled;
	const canDelete = !!(props.canDelete && onChange);
	const _onChange = React.useCallback((index: number, item: E) => {
		onChange?.([
			...value.slice(0, index),
			item,
			...value.slice(index + 1),
		])
	}, [onChange, value, canChange]);

	const _onDelete = React.useCallback((index: number) => {
		onChange?.([
			...value.slice(0, index),
			...value.slice(index + 1),
		])
	}, [props.onChange, props.canDelete]);
	// const onChange = boundUpdateIdx(idx, boundUpdateKey('camera_selectors', updateConfig, []));

	const children = props.value.map((value, index) => {
		return <BoundListItem
			key={index}
			value={value}
			index={index}
			renderItem={props.renderItem}
			onChange={canChange ? _onChange : undefined}
			onDelete={canDelete ? _onDelete : undefined}
		/>
	});

	return (<>{...children}</>)
}