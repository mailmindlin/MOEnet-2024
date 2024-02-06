import React from 'react';
export default function SelectorForm({ selector, cameras, onChange }) {
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
    return (React.createElement("fieldset", null,
        React.createElement("legend", null, "Camera Selector"),
        cameras.length > 0 && (React.createElement(React.Fragment, null,
            React.createElement("label", { htmlFor: 'camera_copysrc' }, "Template"),
            React.createElement("select", { id: "camera_copysrc", value: copySrc, onChange: e => setCopySrc(e.currentTarget.value) }, cameras.map(camera => (React.createElement("option", { key: camera.mxid, value: camera.mxid },
                "OAK (mxid=",
                camera.mxid,
                ")")))),
            React.createElement("button", { onClick: handleCopy }, "Apply"))),
        React.createElement("div", null,
            React.createElement("label", { htmlFor: 'camera_ordinal' }, "Ordinal"),
            React.createElement("input", { id: "camera_ordinal", type: "number", min: "0", value: selector.ordinal, onChange: e => onChange({ ...selector, ordinal: e.currentTarget.value == '0' ? undefined : parseInt(e.currentTarget.value) }) })),
        React.createElement("div", null,
            React.createElement("label", { htmlFor: "camera_mxid" }, "MxId"),
            React.createElement("input", { id: "camera_mxid_enable", type: "text", value: selector.mxid ?? '', onChange: e => onChange({ ...selector, mxid: e.currentTarget.value == '' ? undefined : e.currentTarget.value }) })),
        React.createElement("div", null,
            React.createElement("label", { htmlFor: "camera_name" }, "Name"),
            React.createElement("input", { id: "camera_name", type: "text", value: selector.name ?? '', onChange: e => onChange({ ...selector, name: e.currentTarget.value == '' ? undefined : e.currentTarget.value }) }))));
}
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiU2VsZWN0b3JGb3JtLmpzIiwic291cmNlUm9vdCI6IiIsInNvdXJjZXMiOlsiLi4vLi4vLi4vdHMvcm91dGUvQ29uZmlnQnVpbGRlci9TZWxlY3RvckZvcm0udHN4Il0sIm5hbWVzIjpbXSwibWFwcGluZ3MiOiJBQUFBLE9BQU8sS0FBSyxNQUFNLE9BQU8sQ0FBQztBQVMxQixNQUFNLENBQUMsT0FBTyxVQUFVLFlBQVksQ0FBQyxFQUFFLFFBQVEsRUFBRSxPQUFPLEVBQUUsUUFBUSxFQUFTO0lBQ3ZFLE1BQU0sQ0FBQyxPQUFPLEVBQUUsVUFBVSxDQUFDLEdBQUcsS0FBSyxDQUFDLFFBQVEsQ0FBQyxPQUFPLENBQUMsQ0FBQyxDQUFDLENBQUMsSUFBSSxDQUFDLENBQUM7SUFDOUQsTUFBTSxVQUFVLEdBQUcsS0FBSyxDQUFDLFdBQVcsQ0FBQyxHQUFHLEVBQUU7UUFDdEMsTUFBTSxXQUFXLEdBQUcsT0FBTyxDQUFDLFNBQVMsQ0FBQyxNQUFNLENBQUMsRUFBRSxDQUFDLE1BQU0sQ0FBQyxJQUFJLElBQUksT0FBTyxDQUFDLENBQUM7UUFDeEUsSUFBSSxXQUFXLElBQUksQ0FBQyxDQUFDO1lBQ2pCLE9BQU87UUFDWCxNQUFNLFFBQVEsR0FBRyxPQUFPLENBQUMsV0FBVyxDQUFDLENBQUM7UUFDdEMsUUFBUSxDQUFDO1lBQ0wsR0FBRyxRQUFRO1lBQ1gsSUFBSSxFQUFFLFFBQVEsQ0FBQyxJQUFJO1lBQ25CLElBQUksRUFBRSxRQUFRLENBQUMsSUFBSTtZQUNuQixPQUFPLEVBQUUsV0FBVyxHQUFHLENBQUM7U0FDM0IsQ0FBQyxDQUFDO0lBQ1AsQ0FBQyxFQUFFLENBQUMsT0FBTyxFQUFFLE9BQU8sRUFBRSxRQUFRLENBQUMsQ0FBQyxDQUFDO0lBRWpDLE9BQU8sQ0FDSDtRQUNJLHNEQUFnQztRQUMvQixPQUFPLENBQUMsTUFBTSxHQUFHLENBQUMsSUFBSSxDQUFDO1lBQ3BCLCtCQUFPLE9BQU8sRUFBQyxnQkFBZ0IsZUFBaUI7WUFDaEQsZ0NBQVEsRUFBRSxFQUFDLGdCQUFnQixFQUFDLEtBQUssRUFBRSxPQUFPLEVBQUUsUUFBUSxFQUFFLENBQUMsQ0FBQyxFQUFFLENBQUMsVUFBVSxDQUFDLENBQUMsQ0FBQyxhQUFhLENBQUMsS0FBSyxDQUFDLElBQ3ZGLE9BQU8sQ0FBQyxHQUFHLENBQUMsTUFBTSxDQUFDLEVBQUUsQ0FBQyxDQUNuQixnQ0FBUSxHQUFHLEVBQUUsTUFBTSxDQUFDLElBQUksRUFBRSxLQUFLLEVBQUUsTUFBTSxDQUFDLElBQUk7O2dCQUFhLE1BQU0sQ0FBQyxJQUFJO29CQUFXLENBQ2xGLENBQUMsQ0FDRztZQUNULGdDQUFRLE9BQU8sRUFBRSxVQUFVLFlBQWdCLENBQ3hDLENBQ047UUFDRDtZQUNJLCtCQUFPLE9BQU8sRUFBQyxnQkFBZ0IsY0FBZ0I7WUFDL0MsK0JBQ0ksRUFBRSxFQUFDLGdCQUFnQixFQUNuQixJQUFJLEVBQUMsUUFBUSxFQUNiLEdBQUcsRUFBQyxHQUFHLEVBQ1AsS0FBSyxFQUFFLFFBQVEsQ0FBQyxPQUFPLEVBQ3ZCLFFBQVEsRUFBRSxDQUFDLENBQUMsRUFBRSxDQUFDLFFBQVEsQ0FBQyxFQUFDLEdBQUcsUUFBUSxFQUFFLE9BQU8sRUFBRSxDQUFDLENBQUMsYUFBYSxDQUFDLEtBQUssSUFBSSxHQUFHLENBQUMsQ0FBQyxDQUFDLFNBQVMsQ0FBQyxDQUFDLENBQUMsUUFBUSxDQUFDLENBQUMsQ0FBQyxhQUFhLENBQUMsS0FBSyxDQUFDLEVBQUMsQ0FBQyxHQUM3SCxDQUNBO1FBQ047WUFDSSwrQkFBTyxPQUFPLEVBQUMsYUFBYSxXQUFhO1lBQ3pDLCtCQUNJLEVBQUUsRUFBQyxvQkFBb0IsRUFDdkIsSUFBSSxFQUFDLE1BQU0sRUFDWCxLQUFLLEVBQUUsUUFBUSxDQUFDLElBQUksSUFBSSxFQUFFLEVBQzFCLFFBQVEsRUFBRSxDQUFDLENBQUMsRUFBRSxDQUFDLFFBQVEsQ0FBQyxFQUFDLEdBQUcsUUFBUSxFQUFFLElBQUksRUFBRSxDQUFDLENBQUMsYUFBYSxDQUFDLEtBQUssSUFBSSxFQUFFLENBQUMsQ0FBQyxDQUFDLFNBQVMsQ0FBQyxDQUFDLENBQUMsQ0FBQyxDQUFDLGFBQWEsQ0FBQyxLQUFLLEVBQUMsQ0FBQyxHQUMvRyxDQUNBO1FBQ047WUFDSSwrQkFBTyxPQUFPLEVBQUMsYUFBYSxXQUFhO1lBQ3pDLCtCQUNJLEVBQUUsRUFBQyxhQUFhLEVBQ2hCLElBQUksRUFBQyxNQUFNLEVBQ1gsS0FBSyxFQUFFLFFBQVEsQ0FBQyxJQUFJLElBQUksRUFBRSxFQUMxQixRQUFRLEVBQUUsQ0FBQyxDQUFDLEVBQUUsQ0FBQyxRQUFRLENBQUMsRUFBQyxHQUFHLFFBQVEsRUFBRSxJQUFJLEVBQUUsQ0FBQyxDQUFDLGFBQWEsQ0FBQyxLQUFLLElBQUksRUFBRSxDQUFDLENBQUMsQ0FBQyxTQUFTLENBQUMsQ0FBQyxDQUFDLENBQUMsQ0FBQyxhQUFhLENBQUMsS0FBSyxFQUFDLENBQUMsR0FDL0csQ0FDQSxDQUNDLENBQ2QsQ0FBQTtBQUNMLENBQUMifQ==