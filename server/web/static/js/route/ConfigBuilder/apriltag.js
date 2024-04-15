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
        // const internal = 'path' in value;
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
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiYXByaWx0YWcuanMiLCJzb3VyY2VSb290IjoiIiwic291cmNlcyI6WyIuLi8uLi8uLi90cy9yb3V0ZS9Db25maWdCdWlsZGVyL2FwcmlsdGFnLnRzeCJdLCJuYW1lcyI6W10sIm1hcHBpbmdzIjoiQUFBQSxPQUFPLEtBQXNCLE1BQU0sT0FBTyxDQUFDO0FBRTNDLE9BQU8sRUFBRSxpQkFBaUIsRUFBRSxXQUFXLEVBQUUsY0FBYyxFQUFFLE1BQU0sU0FBUyxDQUFDO0FBQ3pFLE9BQU8sRUFBRSxlQUFlLEVBQUUsTUFBTSxNQUFNLENBQUM7QUFPdkMsU0FBUyxlQUFlLENBQUMsS0FBaUU7SUFDekYsT0FBTyxDQUNOO1FBQ0MsdURBQWlDO1FBQ2pDLG9CQUFDLGlCQUFpQixJQUNqQixLQUFLLEVBQUUsS0FBSyxDQUFDLEtBQUssRUFDbEIsUUFBUSxFQUFFLEtBQUssQ0FBQyxRQUFRLEVBQ3hCLElBQUksRUFBQyxRQUFRLEVBQ2IsS0FBSyxFQUFDLGlCQUFpQixFQUN2QixHQUFHLEVBQUUsQ0FBQyxFQUNOLElBQUksRUFBQyxLQUFLLEdBQ1Q7UUFDRixvQkFBQyxpQkFBaUIsSUFDakIsS0FBSyxFQUFFLEtBQUssQ0FBQyxLQUFLLEVBQ2xCLFFBQVEsRUFBRSxLQUFLLENBQUMsUUFBUSxFQUN4QixJQUFJLEVBQUMsT0FBTyxFQUNaLEtBQUssRUFBQyxnQkFBZ0IsRUFDdEIsR0FBRyxFQUFFLENBQUMsRUFDTixJQUFJLEVBQUMsS0FBSyxHQUNULENBQ1EsQ0FDWCxDQUFBO0FBQ0YsQ0FBQztBQUVELE1BQU0sVUFBVSxxQkFBcUIsQ0FBQyxLQUFZO0lBQ2pELE1BQU0sRUFBRSxRQUFRLEVBQUUsR0FBRyxLQUFLLENBQUM7SUFDM0IsTUFBTSxrQkFBa0IsR0FBRyxLQUFLLENBQUMsV0FBVyxDQUFDLFFBQVEsQ0FBQyxDQUFDLENBQUMsQ0FBQyxDQUFpQyxFQUFFLEVBQUU7UUFDN0YsUUFBUSxDQUFDLENBQUMsYUFBYSxDQUFDLEtBQUssRUFBRSxDQUFDO1lBQy9CLEtBQUss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