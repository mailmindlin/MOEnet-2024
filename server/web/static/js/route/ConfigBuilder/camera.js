import React from 'react';
import { Binding, BoundNumericInput } from './bound';
import { boundReplaceKey } from './ds';
/**
 * Edit pose
 */
export function PoseEditor({ value, onChange }) {
    const id = React.useId();
    //@ts-ignore
    const [rotationFormat, setRotationFormat] = React.useState('quat');
    const rotationInner = [];
    switch (rotationFormat) {
        case 'quat':
            const onChangeQuaternion = onChange && React.useCallback((quat) => {
                // const components = [quat.W, quat.X, quat.Y, quat.Z];
                // for (const i of components.keys()) {
                //     if (Number.isNaN(components[i]))
                //         components[i] = 0;
                //     else if (!Number.isFinite(components[i]))
                //         components[i] = Math.sign(components[i]) * 1.0;
                // }
                // const norm2 = components.reduce((u, v) => u + v * v, 0);
                // if (norm2 <= 0) {
                //     quat = { W: 1, X: 0, Y: 0, Z: 0 };
                // } else if (false) {
                //     const norm = Math.sqrt(norm2);
                //     quat = {
                //         W: components[0] / norm,
                //         X: components[1] / norm,
                //         Y: components[2] / norm,
                //         Z: components[3] / norm,
                //     }
                // }
                console.log('update', value.rotation.quaternion, quat);
                onChange({
                    translation: value.translation,
                    rotation: {
                        quaternion: quat,
                    }
                });
            }, [onChange, value]);
            rotationInner.push(React.createElement(BoundNumericInput, { value: value.rotation.quaternion, onChange: onChangeQuaternion, name: 'W', label: 'W', min: 0, max: 1, step: 'any' }), React.createElement(BoundNumericInput, { value: value.rotation.quaternion, onChange: onChangeQuaternion, name: 'X', label: 'X', min: 0, max: 1, step: 'any' }), React.createElement(BoundNumericInput, { value: value.rotation.quaternion, onChange: onChangeQuaternion, name: 'Y', label: 'Y', min: 0, max: 1, step: 'any' }), React.createElement(BoundNumericInput, { value: value.rotation.quaternion, onChange: onChangeQuaternion, name: 'Z', label: 'Z', min: 0, max: 1, step: 'any' }));
            break;
    }
    const onChangeTranslation = React.useCallback(boundReplaceKey('translation', value, onChange), [value, onChange]);
    return (React.createElement("fieldset", null,
        React.createElement("legend", null, "Robot\u2192Camera Transform"),
        React.createElement("fieldset", null,
            React.createElement("legend", null, "Rotation"),
            React.createElement("label", { htmlFor: id }, "Format"),
            React.createElement("select", { id: id, value: rotationFormat, onChange: () => { } },
                React.createElement("option", { value: 'quat' }, "Quaternion"),
                React.createElement("option", { value: 'euler', disabled: true }, "Axis-Angle (TODO)"),
                React.createElement("option", { value: 'euler', disabled: true }, "Rotation Matrix (TODO)"),
                React.createElement("option", { value: 'euler', disabled: true }, "Euler (TODO)")),
            ...rotationInner),
        React.createElement("fieldset", null,
            React.createElement("legend", null, "Translation"),
            React.createElement(BoundNumericInput, { value: value.translation, onChange: onChangeTranslation, name: 'x', label: 'x (m)', step: 'any' }),
            React.createElement(BoundNumericInput, { value: value.translation, onChange: onChangeTranslation, name: 'y', label: 'y (m)', step: 'any' }),
            React.createElement(BoundNumericInput, { value: value.translation, onChange: onChangeTranslation, name: 'z', label: 'z (m)', step: 'any' }))));
}
export function CameraFilterEditor({ templates, selector, definitions, onChange, onDelete, ...props }) {
    if ((definitions?.length ?? 0) == 0)
        definitions = undefined;
    const [copySrc, setCopySrc] = React.useState(templates.length > 0 ? templates[0].mxid : '');
    const handleCopy = React.useCallback(() => {
        const selectedIdx = templates.findIndex(camera => camera.mxid == copySrc);
        if (selectedIdx == -1)
            return;
        const selected = templates[selectedIdx];
        onChange?.({
            ...selector,
            devname: selected.name,
            mxid: selected.mxid,
            ordinal: selectedIdx + 1,
        });
    }, [copySrc, templates, onChange]);
    const _onChange = onChange;
    const Bound = Binding(selector, _onChange);
    const csId = React.useId();
    return (React.createElement("fieldset", null,
        React.createElement("legend", null, props.legend),
        templates.length > 0 && onChange && (React.createElement(React.Fragment, null,
            React.createElement("label", { htmlFor: csId }, "Template"),
            React.createElement("select", { id: csId, value: copySrc, onChange: e => setCopySrc(e.currentTarget.value) }, templates.map(camera => (React.createElement("option", { key: camera.mxid, value: camera.mxid },
                "OAK (mxid=",
                camera.mxid,
                ")")))),
            React.createElement("button", { onClick: handleCopy }, "Apply"))),
        React.createElement(Bound.Number, { name: 'ordinal', label: 'Ordinal', help: 'Filter OAK cameras by ordinal', min: 1, nullable: true }),
        React.createElement(Bound.Text, { name: 'mxid', placeholder: '(Match all)', help: 'Filter OAK cameras by MxId', label: 'MxId', nullable: true }),
        React.createElement(Bound.Text, { name: 'devname', placeholder: '(Match all)', help: 'Filter OAK cameras by device name', label: 'Device Name', nullable: true }),
        React.createElement(Bound.Select, { name: 'platform', label: 'OAK Platform filter' },
            React.createElement("option", { value: "X_LINK_ANY_PLATFORM" }, "Any (you probably want this)"),
            React.createElement("option", { value: "X_LINK_MYRIAD_2" }, "Myraid 2"),
            React.createElement("option", { value: "X_LINK_MYRIAD_X" }, "Myraid X")),
        React.createElement(Bound.Select, { name: 'protocol', label: 'USB Speed', nullable: true },
            React.createElement("option", { value: "$null" }, "Default"),
            React.createElement("option", { value: "LOW" }, "Low (USB 1.0, 1.5mbps)"),
            React.createElement("option", { value: "FULL" }, "Full (USB 1.0, 12mbps)"),
            React.createElement("option", { value: "HIGH" }, "High (USB 2.0, 480mbps)"),
            React.createElement("option", { value: "SUPER" }, "Super (USB 3.0, 5gbps)"),
            React.createElement("option", { value: "SUPER_PLUS" }, "Super+ (USB 3.0, 10gbps)")),
        onDelete && React.createElement("button", { onClick: onDelete }, "Delete")));
}
export default function SelectorForm({ selector, templates, onChange, definitions }) {
    let selectorInner;
    if (typeof selector === 'string') {
        selectorInner = definitions.find(definition => definition.id == selector);
    }
    else {
        selectorInner = selector;
    }
    const handleSelectorChange = React.useCallback((e) => {
        const selection = e.currentTarget.selectedIndex;
        if (selection === 0) {
            // Custom
            console.log('Update custom');
            onChange(selectorInner ?? {});
        }
        else {
            console.log('Update to ', definitions[selection - 1].id);
            onChange(definitions[selection - 1].id);
        }
    }, [onChange, selectorInner, definitions]);
    if ((definitions?.length ?? 0) == 0)
        definitions = undefined;
    const templateId = React.useId();
    return (React.createElement(CameraFilterEditor, { templates: templates, selector: selectorInner, definitions: definitions, onChange: typeof selector === 'string' ? undefined : onChange, legend: React.createElement(React.Fragment, null,
            React.createElement("label", { htmlFor: templateId }, "Camera Selector \u00A0"),
            React.createElement("select", { id: templateId, value: typeof selector === 'string' ? selector : '$custom', onChange: handleSelectorChange },
                React.createElement("option", { value: '$custom' }, "Custom"),
                definitions && (React.createElement("optgroup", { label: "Templates" }, definitions.map(definition => (React.createElement("option", { key: definition.id, value: definition.id }, definition.id))))),
                !definitions && React.createElement("option", { disabled: true }, "No templates"))) }));
}
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiY2FtZXJhLmpzIiwic291cmNlUm9vdCI6IiIsInNvdXJjZXMiOlsiLi4vLi4vLi4vdHMvcm91dGUvQ29uZmlnQnVpbGRlci9jYW1lcmEudHN4Il0sIm5hbWVzIjpbXSwibWFwcGluZ3MiOiJBQUFBLE9BQU8sS0FBc0IsTUFBTSxPQUFPLENBQUM7QUFHM0MsT0FBTyxFQUFFLE9BQU8sRUFBRSxpQkFBaUIsRUFBRSxNQUFNLFNBQVMsQ0FBQztBQUNyRCxPQUFPLEVBQUUsZUFBZSxFQUFFLE1BQU0sTUFBTSxDQUFDO0FBT3ZDOztHQUVHO0FBQ0gsTUFBTSxVQUFVLFVBQVUsQ0FBQyxFQUFFLEtBQUssRUFBRSxRQUFRLEVBQW1CO0lBQzNELE1BQU0sRUFBRSxHQUFHLEtBQUssQ0FBQyxLQUFLLEVBQUUsQ0FBQztJQUN6QixZQUFZO0lBQ1osTUFBTSxDQUFDLGNBQWMsRUFBRSxpQkFBaUIsQ0FBQyxHQUFHLEtBQUssQ0FBQyxRQUFRLENBQUMsTUFBTSxDQUFDLENBQUM7SUFFbkUsTUFBTSxhQUFhLEdBQUcsRUFBRSxDQUFDO0lBQ3pCLFFBQVEsY0FBYyxFQUFFLENBQUM7UUFDckIsS0FBSyxNQUFNO1lBQ1AsTUFBTSxrQkFBa0IsR0FBRyxRQUFRLElBQUksS0FBSyxDQUFDLFdBQVcsQ0FBQyxDQUFDLElBQWdCLEVBQUUsRUFBRTtnQkFDMUUsdURBQXVEO2dCQUN2RCx1Q0FBdUM7Z0JBQ3ZDLHVDQUF1QztnQkFDdkMsNkJBQTZCO2dCQUM3QixnREFBZ0Q7Z0JBQ2hELDBEQUEwRDtnQkFDMUQsSUFBSTtnQkFFSiwyREFBMkQ7Z0JBQzNELG9CQUFvQjtnQkFDcEIseUNBQXlDO2dCQUV6QyxzQkFBc0I7Z0JBQ3RCLHFDQUFxQztnQkFDckMsZUFBZTtnQkFDZixtQ0FBbUM7Z0JBQ25DLG1DQUFtQztnQkFDbkMsbUNBQW1DO2dCQUNuQyxtQ0FBbUM7Z0JBQ25DLFFBQVE7Z0JBQ1IsSUFBSTtnQkFDSixPQUFPLENBQUMsR0FBRyxDQUFDLFFBQVEsRUFBRSxLQUFLLENBQUMsUUFB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