import React, { ChangeEvent } from 'react';
import { CameraSelectorDefinition, OakSelector, Pose2, Quaternion } from '../../config';
import type { CameraInfo } from './index';
import { Binding, BoundNumericInput } from './bound';
import { boundReplaceKey } from './ds';

interface PoseEditorProps {
    value: Pose2,
    onChange?(value: Pose2): void;
}

/**
 * Edit pose
 */
export function PoseEditor({ value, onChange }: PoseEditorProps) {
    const id = React.useId();
    //@ts-ignore
    const [rotationFormat, setRotationFormat] = React.useState('quat');

    const rotationInner = [];
    switch (rotationFormat) {
        case 'quat':
            const onChangeQuaternion = onChange && React.useCallback((quat: Quaternion) => {
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
            rotationInner.push(
                <BoundNumericInput value={value.rotation.quaternion} onChange={onChangeQuaternion} name='W' label='W' min={0} max={1} step='any' />,
                <BoundNumericInput value={value.rotation.quaternion} onChange={onChangeQuaternion} name='X' label='X' min={0} max={1} step='any' />,
                <BoundNumericInput value={value.rotation.quaternion} onChange={onChangeQuaternion} name='Y' label='Y' min={0} max={1} step='any' />,
                <BoundNumericInput value={value.rotation.quaternion} onChange={onChangeQuaternion} name='Z' label='Z' min={0} max={1} step='any' />,
            );
            break;
    }

    const onChangeTranslation = React.useCallback(boundReplaceKey('translation', value, onChange)!, [value, onChange]);

    return (
        <fieldset>
            <legend>Robot&rarr;Camera Transform</legend>
            <fieldset>
                <legend>Rotation</legend>
                <label htmlFor={id}>Format</label>
                <select
                    id={id}
                    value={rotationFormat}
                    onChange={() => {/*TODO */}}
                >
                    <option value='quat'>Quaternion</option>
                    <option value='euler' disabled>Axis-Angle (TODO)</option>
                    <option value='euler' disabled>Rotation Matrix (TODO)</option>
                    <option value='euler' disabled>Euler (TODO)</option>
                </select>
                {...rotationInner}
            </fieldset>
            <fieldset>
                <legend>Translation</legend>
                <BoundNumericInput value={value.translation} onChange={onChangeTranslation} name='x' label='x (m)' step='any' />
                <BoundNumericInput value={value.translation} onChange={onChangeTranslation} name='y' label='y (m)' step='any' />
                <BoundNumericInput value={value.translation} onChange={onChangeTranslation} name='z' label='z (m)' step='any' />
            </fieldset>
        </fieldset>
    )
}


interface CameraSelectorProps<T extends OakSelector> {
    legend: React.ReactNode;
    /** Known attached cameras (templates) */
    templates: CameraInfo[];
    selector: T;
    definitions: CameraSelectorDefinition[] | undefined;
    onChange?(cb: T | ((value: T) => T)): void;
    onDelete?(): void;
}

export function CameraFilterEditor<T extends OakSelector>({ templates, selector, definitions, onChange, onDelete, ...props }: CameraSelectorProps<T>) {
    if ((definitions?.length ?? 0) == 0)
        definitions = undefined;

    const [copySrc, setCopySrc] = React.useState(templates.length > 0 ? templates[0].mxid : '');
    const handleCopy = React.useCallback(() => {
        const selectedIdx = templates.findIndex(camera => camera.mxid == copySrc);
        if (selectedIdx == -1)
            return;
        const selected = templates[selectedIdx];
        onChange?.({
            ...(selector as any),
            devname: selected.name,
            mxid: selected.mxid,
            ordinal: selectedIdx + 1,
        });
    }, [copySrc, templates, onChange]);

    const _onChange: ((value: T) => void) | undefined = onChange;
    const Bound: Binding<OakSelector> = Binding<T>(selector, _onChange);

    const csId = React.useId()

    return (
        <fieldset>
            <legend>{props.legend}</legend>
            {templates.length > 0 && onChange && (<>
                <label htmlFor={csId}>Template</label>
                <select id={csId} value={copySrc} onChange={e => setCopySrc(e.currentTarget.value)}>
                    {templates.map(camera => (
                        <option key={camera.mxid} value={camera.mxid}>OAK (mxid={camera.mxid})</option>
                    ))}
                </select>
                <button onClick={handleCopy}>Apply</button>
                </>
            )}
            <Bound.Number
                name='ordinal'
                label='Ordinal'
                help='Filter OAK cameras by ordinal'
                min={1}
                nullable
            />
            <Bound.Text
                name='mxid'
                placeholder='(Match all)'
                help='Filter OAK cameras by MxId'
                label='MxId'
                nullable
            />
            <Bound.Text
                name='devname'
                placeholder='(Match all)'
                help='Filter OAK cameras by device name'
                label='Device Name'
                nullable
            />
            <Bound.Select name='platform' label='OAK Platform filter'>
                <option value="X_LINK_ANY_PLATFORM">Any (you probably want this)</option>
                <option value="X_LINK_MYRIAD_2">Myraid 2</option>
                <option value="X_LINK_MYRIAD_X">Myraid X</option>
            </Bound.Select>
            <Bound.Select name='protocol' label='USB Speed' nullable>
                <option value="$null">Default</option>
                <option value="LOW">Low (USB 1.0, 1.5mbps)</option>
                <option value="FULL">Full (USB 1.0, 12mbps)</option>
                <option value="HIGH">High (USB 2.0, 480mbps)</option>
                <option value="SUPER">Super (USB 3.0, 5gbps)</option>
                <option value="SUPER_PLUS">Super+ (USB 3.0, 10gbps)</option>
            </Bound.Select>
            {onDelete && <button onClick={onDelete}>Delete</button>}
        </fieldset>
    )
}



interface Props {
    templates: CameraInfo[];
    selector: string | OakSelector;
    definitions: CameraSelectorDefinition[] | undefined;
    onChange(selector: OakSelector | string): void;
}

export default function SelectorForm({ selector, templates, onChange, definitions }: Props) {
    let selectorInner: OakSelector | undefined;
    if (typeof selector === 'string') {
        selectorInner = definitions!.find(definition => definition.id == selector)!;
    } else {
        selectorInner = selector;
    }

    const handleSelectorChange = React.useCallback((e: ChangeEvent<HTMLSelectElement>) => {
        const selection = e.currentTarget.selectedIndex;
        if (selection === 0) {
            // Custom
            console.log('Update custom');
            onChange(selectorInner ?? {});
        } else {
            console.log('Update to ', definitions![selection - 1].id)
            onChange(definitions![selection - 1].id);
        }
    }, [onChange, selectorInner, definitions]);
    if ((definitions?.length ?? 0) == 0)
        definitions = undefined;

    const templateId = React.useId();
    return (
        <CameraFilterEditor
            templates={templates}
            selector={selectorInner}
            definitions={definitions}
            onChange={typeof selector === 'string' ? undefined : (onChange as (v: OakSelector) => void)}
            legend={<>
                <label htmlFor={templateId}>Camera Selector &nbsp;</label>
                <select id={templateId} value={typeof selector === 'string' ? selector : '$custom'} onChange={handleSelectorChange}>
                    <option value='$custom'>Custom</option>
                    {definitions && (
                        <optgroup label="Templates">
                            {definitions.map(definition => (
                                <option key={definition.id} value={definition.id}>{definition.id}</option>
                            ))}
                        </optgroup>
                    )}
                    {!definitions && <option disabled>No templates</option>}
                </select>
            </>}
        />
    );
}