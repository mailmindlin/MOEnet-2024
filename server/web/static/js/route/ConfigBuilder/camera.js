import React from 'react';
import { BoundNumericInput, BoundSelect, BoundTextInput } from './bound';
import { boundReplaceKey } from './ds';
export function PoseEditor({ value, onChange }) {
    const id = React.useId();
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
export function CameraSelector({ cameras, selector, definitions, onChange, onDelete, ...props }) {
    if ((definitions?.length ?? 0) == 0)
        definitions = undefined;
    const [copySrc, setCopySrc] = React.useState(cameras.length > 0 ? cameras[0].mxid : '');
    const handleCopy = React.useCallback(() => {
        const selectedIdx = cameras.findIndex(camera => camera.mxid == copySrc);
        if (selectedIdx == -1)
            return;
        const selected = cameras[selectedIdx];
        onChange?.({
            ...selector,
            devname: selected.name,
            mxid: selected.mxid,
            ordinal: selectedIdx + 1,
        });
    }, [copySrc, cameras, onChange]);
    const _onChange = onChange;
    const csId = React.useId();
    return (React.createElement("fieldset", null,
        React.createElement("legend", null, props.legend),
        cameras.length > 0 && onChange && (React.createElement(React.Fragment, null,
            React.createElement("label", { htmlFor: csId }, "Template"),
            React.createElement("select", { id: csId, value: copySrc, onChange: e => setCopySrc(e.currentTarget.value) }, cameras.map(camera => (React.createElement("option", { key: camera.mxid, value: camera.mxid },
                "OAK (mxid=",
                camera.mxid,
                ")")))),
            React.createElement("button", { onClick: handleCopy }, "Apply"))),
        React.createElement(BoundNumericInput, { value: selector, onChange: _onChange, name: 'ordinal', label: 'Ordinal', help: 'Filter OAK cameras by ordinal', min: 1, nullable: true }),
        React.createElement(BoundTextInput, { value: selector, onChange: _onChange, name: 'mxid', placeholder: '(Match all)', help: 'Filter OAK cameras by MxId', label: 'MxId' }),
        React.createElement(BoundTextInput, { value: selector, onChange: _onChange, name: 'devname', placeholder: '(Match all)', help: 'Filter OAK cameras by device name', label: 'Device Name' }),
        React.createElement(BoundSelect, { value: selector, onChange: _onChange, name: 'platform', label: 'OAK Platform filter' },
            React.createElement("option", { value: "X_LINK_ANY_PLATFORM" }, "Any (you probably want this)"),
            React.createElement("option", { value: "X_LINK_MYRIAD_2" }, "Myraid 2"),
            React.createElement("option", { value: "X_LINK_MYRIAD_X" }, "Myraid X")),
        React.createElement(BoundSelect, { value: selector, onChange: _onChange, name: 'protocol', label: 'USB Speed' },
            React.createElement("option", { value: "$null" }, "Default"),
            React.createElement("option", { value: "LOW" }, "Low (USB 1.0, 1.5mbps)"),
            React.createElement("option", { value: "FULL" }, "Full (USB 1.0, 12mbps)"),
            React.createElement("option", { value: "HIGH" }, "High (USB 2.0, 480mbps)"),
            React.createElement("option", { value: "SUPER" }, "Super (USB 3.0, 5gbps)"),
            React.createElement("option", { value: "SUPER_PLUS" }, "Super+ (USB 3.0, 10gbps)")),
        onDelete && React.createElement("button", { onClick: onDelete }, "Delete")));
}
export default function SelectorForm({ selector, cameras, onChange, definitions }) {
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
    return (React.createElement(CameraSelector, { cameras: cameras, selector: selectorInner, definitions: definitions, onChange: typeof selector === 'string' ? undefined : onChange, legend: React.createElement(React.Fragment, null,
            React.createElement("label", { htmlFor: templateId }, "Camera Selector \u00A0"),
            React.createElement("select", { id: templateId, value: typeof selector === 'string' ? selector : '$custom', onChange: handleSelectorChange },
                React.createElement("option", { value: '$custom' }, "Custom"),
                definitions && (React.createElement("optgroup", { label: "Templates" }, definitions.map(definition => (React.createElement("option", { key: definition.id, value: definition.id }, definition.id))))),
                !definitions && React.createElement("option", { disabled: true }, "No templates"))) })); /*
        <fieldset>
            <legend>
                
                </select>
            </legend>
            {cameras.length > 0 && (<>
                <label htmlFor='camera_copysrc'>Template</label>
                <select id="camera_copysrc" value={copySrc} onChange={e => setCopySrc(e.currentTarget.value)}>
                    {cameras.map(camera => (
                        <option key={camera.mxid} value={camera.mxid}>OAK (mxid={camera.mxid})</option>
                    ))}
                </select>
                <button onClick={handleCopy}>Apply</button>
                </>
            )}
            <div>
                <label htmlFor='camera_ordinal'>Ordinal</label>
                <input
                    id="camera_ordinal"
                    type="number"
                    min="0"
                    value={selector.ordinal!}
                    onChange={e => onChange({...selector, ordinal: e.currentTarget.value == '0' ? undefined : parseInt(e.currentTarget.value)})}
                />
            </div>
            <div>
                <label htmlFor="camera_mxid">MxId</label>
                <input
                    id="camera_mxid_enable"
                    type="text"
                    value={selector.mxid ?? ''}
                    onChange={e => onChange({...selector, mxid: e.currentTarget.value == '' ? undefined : e.currentTarget.value})}
                />
            </div>
            <div>
                <label htmlFor="camera_name">Device Name</label>
                <input
                    id="camera_name"
                    type="text"
                    value={selector.devname ?? ''}
                    onChange={e => onChange({...selector, devname: e.currentTarget.value == '' ? undefined : e.currentTarget.value})}
                />
            </div>
        </fieldset>
    )*/
}
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiY2FtZXJhLmpzIiwic291cmNlUm9vdCI6IiIsInNvdXJjZXMiOlsiLi4vLi4vLi4vdHMvcm91dGUvQ29uZmlnQnVpbGRlci9jYW1lcmEudHN4Il0sIm5hbWVzIjpbXSwibWFwcGluZ3MiOiJBQUFBLE9BQU8sS0FBc0IsTUFBTSxPQUFPLENBQUM7QUFHM0MsT0FBTyxFQUFFLGlCQUFpQixFQUFFLFdBQVcsRUFBRSxjQUFjLEVBQUUsTUFBTSxTQUFTLENBQUM7QUFDekUsT0FBTyxFQUFFLGVBQWUsRUFBRSxNQUFNLE1BQU0sQ0FBQztBQU92QyxNQUFNLFVBQVUsVUFBVSxDQUFDLEVBQUUsS0FBSyxFQUFFLFFBQVEsRUFBbUI7SUFDM0QsTUFBTSxFQUFFLEdBQUcsS0FBSyxDQUFDLEtBQUssRUFBRSxDQUFDO0lBQ3pCLE1BQU0sQ0FBQyxjQUFjLEVBQUUsaUJBQWlCLENBQUMsR0FBRyxLQUFLLENBQUMsUUFBUSxDQUFDLE1BQU0sQ0FBQyxDQUFDO0lBRW5FLE1BQU0sYUFBYSxHQUFHLEVBQUUsQ0FBQztJQUN6QixRQUFRLGNBQWMsRUFBRSxDQUFDO1FBQ3JCLEtBQUssTUFBTTtZQUNQLE1BQU0sa0JBQWtCLEdBQUcsUUFBUSxJQUFJLEtBQUssQ0FBQyxXQUFXLENBQUMsQ0FBQyxJQUFnQixFQUFFLEVBQUU7Z0JBQzFFLHVEQUF1RDtnQkFDdkQsdUNBQXVDO2dCQUN2Qyx1Q0FBdUM7Z0JBQ3ZDLDZCQUE2QjtnQkFDN0IsZ0RBQWdEO2dCQUNoRCwwREFBMEQ7Z0JBQzFELElBQUk7Z0JBRUosMkRBQTJEO2dCQUMzRCxvQkFBb0I7Z0JBQ3BCLHlDQUF5QztnQkFFekMsc0JBQXNCO2dCQUN0QixxQ0FBcUM7Z0JBQ3JDLGVBQWU7Z0JBQ2YsbUNBQW1DO2dCQUNuQyxtQ0FBbUM7Z0JBQ25DLG1DQUFtQztnQkFDbkMsbUNBQW1DO2dCQUNuQyxRQUFRO2dCQUNSLElBQUk7Z0JBQ0osT0FBTyxDQUFDLEdBQUcsQ0FBQyxRQUFRLEVBQUUsS0FBSyxDQUFDLFFBQVEsQ0FBQyxVQUFV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