import React from 'react';
import { CameraInfo, OakSelector } from '../../config';

interface Props {
    cameras: CameraInfo[];
    selector: OakSelector;
    onChange(selector: OakSelector): void;
}

export default function SelectorForm({ selector, cameras, onChange }: Props) {
    const [copySrc, setCopySrc] = React.useState(cameras[0].mxid);
    const handleCopy = React.useCallback(() => {
        const selectedIdx = cameras.findIndex(camera => camera.mxid == copySrc);
        if (selectedIdx == -1)
            return;
        const selected = cameras[selectedIdx];
        onChange({
            ...selector,
            name: selected.name,
            mxid: selected.mxid,
            ordinal: selectedIdx + 1,
        });
    }, [copySrc, cameras, onChange]);

    return (
        <fieldset>
            <legend>Camera Selector</legend>
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
                    value={selector.ordinal}
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
                <label htmlFor="camera_name">Name</label>
                <input
                    id="camera_name"
                    type="text"
                    value={selector.name ?? ''}
                    onChange={e => onChange({...selector, name: e.currentTarget.value == '' ? undefined : e.currentTarget.value})}
                />
            </div>
        </fieldset>
    )
}