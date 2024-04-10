import React from 'react';
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
export function bindChangeHandler(value, key, onChange, nullable) {
    if (!onChange)
        return React.useCallback(undefined, [onChange, value]);
    return React.useCallback((e) => {
        let kv = e;
        if (e.currentTarget) {
            const ct = e.currentTarget;
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
        onChange({
            ...value,
            [key]: kv,
        });
    }, [onChange, value]);
}
export function BoundSelect(props) {
    const id = React.useId();
    const disabled = (!props.onChange) || props.disabled;
    return (React.createElement("div", null,
        React.createElement("label", { htmlFor: id },
            props.label,
            "\u00A0"),
        React.createElement("select", { id: id, value: props.value[props.name] ?? '', disabled: disabled, onChange: bindChangeHandler(props.value, props.name, props.onChange) }, props.children)));
}
function Tooltip(props) {
    if (props.help) {
        return (React.createElement("span", { className: 'tooltip' },
            props.children,
            React.createElement("div", { className: 'tooltiptext' }, props.help)));
    }
    else {
        return props.children;
    }
}
export function BoundNumericInput(props) {
    const id = React.useId();
    const disabled = (!props.onChange) || props.disabled;
    {
        const { label, value, name, disabled, defaultValue, onChange, help, nullable, ...extraProps1 } = props;
        var extraProps = extraProps1;
    }
    const changeHandler = bindChangeHandler(props.value, props.name, props.onChange, props.nullable);
    return (React.createElement("div", null,
        React.createElement(Tooltip, { help: props.help },
            React.createElement("label", { htmlFor: id },
                props.label,
                "\u00A0"),
            React.createElement("input", { id: id, type: 'number', inputMode: 'numeric', value: props.value[props.name] ?? '', placeholder: props.defaultValue ? `${props.defaultValue}` : undefined, disabled: disabled, onChange: changeHandler, ...extraProps }))));
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
            React.createElement("input", { id: id, type: 'text', value: props.value[props.name] ?? '', placeholder: props.placeholder, disabled: disabled, onChange: bindChangeHandler(props.value, props.name, props.onChange, props.nullable), ...extraProps }))));
}
export function Collapsible(props) {
    const [expanded, setExpanded] = React.useState(true);
    let legend = (React.createElement("legend", { onClick: () => setExpanded(!expanded) },
        React.createElement("span", null, props.legend)));
    return (React.createElement("fieldset", { className: expanded ? 'toggleAble expanded' : 'toggleAble' },
        legend,
        props.children));
}
export function BoundCheckbox(props) {
    const id = React.useId();
    const disabled = (!props.onChange) || props.disabled;
    return (React.createElement("div", null,
        React.createElement(Tooltip, { help: props.help },
            React.createElement("label", { htmlFor: id },
                props.label,
                "\u00A0"),
            React.createElement("input", { type: 'checkbox', id: id, checked: props.value[props.name] ?? props.defaultValue ?? false, disabled: disabled, onChange: bindChangeHandler(props.value, props.name, props.onChange) }))));
}
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiYm91bmQuanMiLCJzb3VyY2VSb290IjoiIiwic291cmNlcyI6WyIuLi8uLi8uLi90cy9yb3V0ZS9Db25maWdCdWlsZGVyL2JvdW5kLnRzeCJdLCJuYW1lcyI6W10sIm1hcHBpbmdzIjoiQUFBQSxPQUFPLEtBQXNCLE1BQU0sT0FBTyxDQUFDO0FBRTNDLE1BQU0sVUFBVSxPQUFPLENBQUksS0FBUSxFQUFFLFFBQTRCO0lBQ2hFLDBFQUEwRTtJQUMxRSxNQUFNLElBQUksR0FBRyxLQUFLLENBQUMsTUFBTSxDQUFDLEVBQUMsS0FBSyxFQUFFLFFBQVEsRUFBQyxDQUFDLENBQUM7SUFDN0MsSUFBSSxDQUFDLE9BQU8sR0FBRyxFQUFDLEtBQUssRUFBRSxRQUFRLEVBQUMsQ0FBQztJQUVqQyxPQUFPLEtBQUssQ0FBQyxPQUFPLENBQUMsR0FBRyxFQUFFO1FBQ3pCLFNBQVMsUUFBUSxDQUFvQixLQUEyRDtZQUMvRixPQUFPLGFBQWEsQ0FBQztnQkFDcEIsR0FBRyxLQUFLO2dCQUNSLEdBQUcsSUFBSSxDQUFDLE9BQU87YUFDZixDQUFDLENBQUM7UUFDSixDQUFDO1FBQ0QsU0FBUyxNQUFNLENBQW9CLEtBQXlEO1lBQzNGLE9BQU8sV0FBVyxDQUFDO2dCQUNsQixHQUFHLEtBQUs7Z0JBQ1IsR0FBRyxJQUFJLENBQUMsT0FBTzthQUNmLENBQUMsQ0FBQztRQUNKLENBQUM7UUFDRCxTQUFTLE1BQU0sQ0FBb0IsS0FBK0Q7WUFDakcsT0FBTyxpQkFBaUIsQ0FBQztnQkFDeEIsR0FBRyxLQUFLO2dCQUNSLEdBQUcsSUFBSSxDQUFDLE9BQU87YUFDZixDQUFDLENBQUM7UUFDSixDQUFDO1FBQ0QsU0FBUyxJQUFJLENBQW9CLEtBQTREO1lBQzVGLE9BQU8sY0FBYyxDQUFDO2dCQUNyQixHQUFHLEtBQUs7Z0JBQ1IsR0FBRyxJQUFJLENBQUMsT0FBTzthQUNmLENBQUMsQ0FBQTtRQUNILENBQUM7UUFDRCxPQUFPO1lBQ04sUUFBUTtZQUNSLE1BQU07WUFDTixNQUFNO1lBQ04sSUFB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