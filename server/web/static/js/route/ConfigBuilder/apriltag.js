import React from 'react';
import { BoundNumericInput, BoundSelect, BoundTextInput } from './bound';
import { boundReplaceKey } from './ds';
function FieldDimsEditor(props) {
    return (React.createElement("fieldset", null,
        React.createElement("legend", null, "Field Dimensions"),
        React.createElement(BoundNumericInput, { value: props.value, onChange: props.onChange, name: 'length', label: 'Length (meters)', min: 0, step: 'any' }),
        React.createElement(BoundNumericInput, { value: props.value, onChange: props.onChange, name: 'width', label: 'Width (meters)', min: 0, step: 'any' })));
}
export function AprilTagFieldSelector(props) {
    const { onChange } = props;
    const handleFormatChange = React.useCallback(onChange ? (e) => {
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
    } : undefined, [onChange]);
    const format = typeof props.value === 'string' ? props.value : `${props.value.format}_${'path' in props.value ? 'ext' : 'int'}`;
    const inner = [];
    const { value } = props;
    if (typeof value === 'string') {
        // Skip
    }
    else {
        const internal = 'path' in value;
        if (value.format === 'wpi') {
            const c = onChange;
            inner.push(React.createElement(BoundNumericInput, { value: value, name: 'tagSize', onChange: c, label: 'Tag Size (meters)', min: 0, step: 'any' }), React.createElement(BoundSelect, { value: value, onChange: c, name: 'tagFamily', label: 'AprilTag family' },
                React.createElement("option", { value: "tag16h5" }, "tag16h5"),
                React.createElement("option", { value: "tag25h9" }, "tag25h9"),
                React.createElement("option", { value: "tag36h10" }, "tag36h10"),
                React.createElement("option", { value: "tag36h11" }, "tag36h11"),
                React.createElement("option", { value: "tagCircle21h7" }, "tagCircle21h7"),
                React.createElement("option", { value: "tagStandard41h12" }, "tagStandard41h12")));
            if ('path' in value) {
                inner.push(React.createElement(BoundTextInput, { value: value, name: 'path', onChange: onChange, label: 'Path' }));
            }
            else {
                inner.push(React.createElement(FieldDimsEditor, { value: value.field, onChange: boundReplaceKey('field', value, onChange) }));
                //TODO: tag editor
            }
        }
        else if (value.format === 'sai') {
            if ('path' in value) {
                inner.push(React.createElement(BoundTextInput, { value: value, name: 'path', onChange: onChange, label: 'Path' }));
            }
            else {
                //TODO: tag editor
            }
            inner.push(React.createElement(FieldDimsEditor, { value: value.field, onChange: boundReplaceKey('field', value, onChange) }));
        }
    }
    const atId = React.useId();
    return (React.createElement("fieldset", null,
        React.createElement("legend", null, "AprilTags"),
        React.createElement("label", { htmlFor: atId }, "Format"),
        React.createElement("select", { id: atId, value: format, onChange: handleFormatChange },
            React.createElement("optgroup", { label: 'WPIlib Internal' },
                React.createElement("option", { value: "2024Crescendo" }, "Crescendo (2024)"),
                React.createElement("option", { value: "2023ChargedUp" }, "Charged Up (2023)"),
                React.createElement("option", { value: "2022RapidReact" }, "Rapid React (2022)")),
            React.createElement("optgroup", { label: "Inline" },
                React.createElement("option", { value: "wpi_int" }, "WPI (inline)"),
                React.createElement("option", { value: "sai_int" }, "SpectacularAI (inline)")),
            React.createElement("optgroup", { label: "External File" },
                React.createElement("option", { value: "wpi_ext" }, "WPI (external)"),
                React.createElement("option", { value: "sai_ext" }, "SpectacularAI (external)"))),
        ...inner));
}
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiYXByaWx0YWcuanMiLCJzb3VyY2VSb290IjoiIiwic291cmNlcyI6WyIuLi8uLi8uLi90cy9yb3V0ZS9Db25maWdCdWlsZGVyL2FwcmlsdGFnLnRzeCJdLCJuYW1lcyI6W10sIm1hcHBpbmdzIjoiQUFBQSxPQUFPLEtBQXNCLE1BQU0sT0FBTyxDQUFDO0FBRTNDLE9BQU8sRUFBRSxpQkFBaUIsRUFBRSxXQUFXLEVBQUUsY0FBYyxFQUFFLE1BQU0sU0FBUyxDQUFDO0FBQ3pFLE9BQU8sRUFBRSxlQUFlLEVBQWtCLE1BQU0sTUFBTSxDQUFDO0FBT3ZELFNBQVMsZUFBZSxDQUFDLEtBQWlFO0lBQ3pGLE9BQU8sQ0FDTjtRQUNDLHVEQUFpQztRQUNqQyxvQkFBQyxpQkFBaUIsSUFDakIsS0FBSyxFQUFFLEtBQUssQ0FBQyxLQUFLLEVBQ2xCLFFBQVEsRUFBRSxLQUFLLENBQUMsUUFBUSxFQUN4QixJQUFJLEVBQUMsUUFBUSxFQUNiLEtBQUssRUFBQyxpQkFBaUIsRUFDdkIsR0FBRyxFQUFFLENBQUMsRUFDTixJQUFJLEVBQUMsS0FBSyxHQUNUO1FBQ0Ysb0JBQUMsaUJBQWlCLElBQ2pCLEtBQUssRUFBRSxLQUFLLENBQUMsS0FBSyxFQUNsQixRQUFRLEVBQUUsS0FBSyxDQUFDLFFBQVEsRUFDeEIsSUFBSSxFQUFDLE9BQU8sRUFDWixLQUFLLEVBQUMsZ0JBQWdCLEVBQ3RCLEdBQUcsRUFBRSxDQUFDLEVBQ04sSUFBSSxFQUFDLEtBQUssR0FDVCxDQUNRLENBQ1gsQ0FBQTtBQUNGLENBQUM7QUFFRCxNQUFNLFVBQVUscUJBQXFCLENBQUMsS0FBWTtJQUNqRCxNQUFNLEVBQUUsUUFBUSxFQUFFLEdBQUcsS0FBSyxDQUFDO0lBQzNCLE1BQU0sa0JBQWtCLEdBQUcsS0FBSyxDQUFDLFdBQVcsQ0FBQyxRQUFRLENBQUMsQ0FBQyxDQUFDLENBQUMsQ0FBaUMsRUFBRSxFQUFFO1FBQzdGLFFBQVEsQ0FBQyxDQUFDLGFBQWEsQ0FBQyxLQUFLLEVBQUUsQ0FBQztZQUMvQixLQUFL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