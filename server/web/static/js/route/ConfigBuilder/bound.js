import React from 'react';
import Tooltip from '../../components/Tooltip';
export function Binding(value, onChange) {
    // This is a pain, but we need to do this to keep the return type constant
    const vRef = React.useRef({ value, onChange });
    vRef.current = { value, onChange };
    return React.useMemo(() => {
        function Checkbox(props) {
            return BoundCheckbox({
                ...props,
                ...vRef.current,
            });
        }
        function Select(props) {
            return BoundSelect({
                ...props,
                ...vRef.current,
            });
        }
        function Number(props) {
            return BoundNumericInput({
                ...props,
                ...vRef.current,
            });
        }
        function Text(props) {
            return BoundTextInput({
                ...props,
                ...vRef.current,
            });
        }
        return {
            Checkbox,
            Select,
            Number,
            Text,
        };
    }, [vRef]);
}
export function bindChangeHandler(value, key, onChange, mapper, ...mapperArgs) {
    if (!onChange)
        return React.useCallback(undefined, [onChange, value]);
    return React.useCallback((e) => {
        let kv;
        try {
            kv = mapper(e, ...mapperArgs);
        }
        catch (e) {
            if (e instanceof RangeError)
                return;
            throw e;
        }
        onChange({
            ...value,
            [key]: kv,
        });
    }, [onChange, value]);
}
function handleSelectChange(e, nullable) {
    const ct = e.currentTarget;
    if (!ct.checkValidity()) {
        ct.reportValidity();
        throw new RangeError();
    }
    nullable ??= false;
    let value = ct.value;
    if (nullable) {
        switch (value) {
            case '$null':
            case '$undefined':
                value = null;
                break;
        }
    }
    return value;
}
export function BoundSelect(props) {
    const id = React.useId();
    const disabled = (!props.onChange) || props.disabled;
    return (React.createElement("div", null,
        React.createElement("label", { htmlFor: id },
            props.label,
            "\u00A0"),
        React.createElement("select", { id: id, value: props.value[props.name] ?? '', disabled: disabled, onChange: bindChangeHandler(props.value, props.name, props.onChange, handleSelectChange, props.nullable) }, props.children)));
}
function handleNumericChange(e, nullable) {
    const ct = e.currentTarget;
    if (!ct.checkValidity()) {
        ct.reportValidity();
        throw new RangeError();
    }
    nullable ??= false;
    if ((nullable ?? false) && ct.value === '')
        return null;
    const value = ct.valueAsNumber;
    return value;
}
export function BoundNumericInput(props) {
    const id = React.useId();
    const disabled = (!props.onChange) || props.disabled;
    {
        const { label, value, name, disabled, defaultValue, onChange, help, nullable, ...extraProps1 } = props;
        var extraProps = extraProps1;
    }
    const changeHandler = bindChangeHandler(props.value, props.name, props.onChange, handleNumericChange, props.nullable ?? false);
    return (React.createElement("div", null,
        React.createElement(Tooltip, { help: props.help },
            React.createElement("label", { htmlFor: id },
                props.label,
                "\u00A0"),
            React.createElement("input", { id: id, type: 'number', inputMode: 'numeric', value: props.value[props.name] ?? '', placeholder: props.defaultValue ? `${props.defaultValue}` : undefined, disabled: disabled, onChange: changeHandler, ...extraProps }))));
}
function handleTextChange(e, nullable) {
    const ct = e.currentTarget;
    if (!ct.checkValidity()) {
        ct.reportValidity();
        throw new RangeError();
    }
    if (nullable && ct.value === '')
        return null;
    return (ct.value);
}
export function BoundTextInput(props) {
    const id = React.useId();
    const disabled = (!props.onChange) || props.disabled;
    {
        const { label, value, name, disabled, placeholder: defaultValue, onChange, help, nullable, ...extraProps1 } = props;
        var extraProps = extraProps1;
    }
    return (React.createElement("div", null,
        React.createElement(Tooltip, { help: props.help },
            React.createElement("label", { htmlFor: id },
                props.label,
                "\u00A0"),
            React.createElement("input", { id: id, type: 'text', value: props.value[props.name] ?? '', placeholder: props.placeholder, disabled: disabled, onChange: bindChangeHandler(props.value, props.name, props.onChange, handleTextChange, props.nullable ?? false), ...extraProps }))));
}
function handleCheckboxChange(e) {
    const ct = e.currentTarget;
    return ct.checked;
}
export function BoundCheckbox(props) {
    const id = React.useId();
    const disabled = (!props.onChange) || props.disabled;
    return (React.createElement("div", null,
        React.createElement(Tooltip, { help: props.help },
            React.createElement("label", { htmlFor: id },
                props.label,
                "\u00A0"),
            React.createElement("input", { type: 'checkbox', id: id, checked: props.value[props.name] ?? props.defaultValue ?? false, disabled: disabled, onChange: bindChangeHandler(props.value, props.name, props.onChange, handleCheckboxChange) }))));
}
function BoundListItem(props) {
    const { onChange, onDelete, index, value } = props;
    const _onChange = React.useCallback((next) => onChange?.(index, next), [onChange, value]);
    const _onDelete = React.useCallback(() => onDelete?.(index), [onDelete, index]);
    return props.renderItem({
        item: value,
        index: index,
        onChange: onChange ? _onChange : undefined,
        onDelete: onDelete ? _onDelete : undefined,
    });
}
export function BoundList(props) {
    const { onChange, value, } = props;
    const canChange = (!onChange) || props.disabled;
    const canDelete = !!(props.canDelete && onChange);
    const _onChange = React.useCallback((index, item) => {
        onChange?.([
            ...value.slice(0, index),
            item,
            ...value.slice(index + 1),
        ]);
    }, [onChange, value, canChange]);
    const _onDelete = React.useCallback((index) => {
        onChange?.([
            ...value.slice(0, index),
            ...value.slice(index + 1),
        ]);
    }, [props.onChange, props.canDelete]);
    // const onChange = boundUpdateIdx(idx, boundUpdateKey('camera_selectors', updateConfig, []));
    const children = props.value.map((value, index) => {
        return React.createElement(BoundListItem, { key: index, value: value, index: index, renderItem: props.renderItem, onChange: canChange ? _onChange : undefined, onDelete: canDelete ? _onDelete : undefined });
    });
    return (React.createElement(React.Fragment, null, ...children));
}
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiYm91bmQuanMiLCJzb3VyY2VSb290IjoiIiwic291cmNlcyI6WyIuLi8uLi8uLi90cy9yb3V0ZS9Db25maWdCdWlsZGVyL2JvdW5kLnRzeCJdLCJuYW1lcyI6W10sIm1hcHBpbmdzIjoiQUFBQSxPQUFPLEtBQXNCLE1BQU0sT0FBTyxDQUFDO0FBQzNDLE9BQU8sT0FBTyxNQUFNLDBCQUEwQixDQUFDO0FBVy9DLE1BQU0sVUFBVSxPQUFPLENBQW1CLEtBQVEsRUFBRSxRQUE0QjtJQUMvRSwwRUFBMEU7SUFDMUUsTUFBTSxJQUFJLEdBQUcsS0FBSyxDQUFDLE1BQU0sQ0FBQyxFQUFDLEtBQUssRUFBRSxRQUFRLEVBQUMsQ0FBQyxDQUFDO0lBQzdDLElBQUksQ0FBQyxPQUFPLEdBQUcsRUFBQyxLQUFLLEVBQUUsUUFBUSxFQUFDLENBQUM7SUFFakMsT0FBTyxLQUFLLENBQUMsT0FBTyxDQUFDLEdBQUcsRUFBRTtRQUN6QixTQUFTLFFBQVEsQ0FBbUMsS0FBMkQ7WUFDOUcsT0FBTyxhQUFhLENBQUM7Z0JBQ3BCLEdBQUcsS0FBSztnQkFDUixHQUFHLElBQUksQ0FBQyxPQUFPO2FBQ2YsQ0FBQyxDQUFDO1FBQ0osQ0FBQztRQUNELFNBQVMsTUFBTSxDQUFrQyxLQUF5RDtZQUN6RyxPQUFPLFdBQVcsQ0FBQztnQkFDbEIsR0FBRyxLQUFLO2dCQUNSLEdBQUcsSUFBSSxDQUFDLE9BQU87YUFDZixDQUFDLENBQUM7UUFDSixDQUFDO1FBQ0QsU0FBUyxNQUFNLENBQWtDLEtBQStEO1lBQy9HLE9BQU8saUJBQWlCLENBQUM7Z0JBQ3hCLEdBQUcsS0FBSztnQkFDUixHQUFHLElBQUksQ0FBQyxPQUFPO2FBQ2YsQ0FBQyxDQUFDO1FBQ0osQ0FBQztRQUNELFNBQVMsSUFBSSxDQUFrQyxLQUE0RDtZQUMxRyxPQUFPLGNBQWMsQ0FBQztnQkFDckIsR0FBRyxLQUFLO2dCQUNSLEdBQUcsSUFBSSxDQUFDLE9BQU87YUFDZixDQUFDLENBQUE7UUFDSCxDQUFDO1FBQ0QsT0FBTztZQUNO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