import React from 'react';
function StageInherit({ config, stage }) {
    return (React.createElement(React.Fragment, null,
        React.createElement("legend", null, "Inherit"),
        React.createElement(PipelineStages, { config: config, stages: config.pipelines.find(p => p.id == stage.id).stages, legend: (React.createElement("select", { value: stage.id }, config.pipelines.map(pipeline => (React.createElement("option", { key: pipeline.id },
                "Pipeline ",
                pipeline.id))))) })));
}
function StageWeb({ config, stage, idx }) {
    return (React.createElement(React.Fragment, null,
        React.createElement("legend", null, "Web"),
        "Stream images to web server",
        React.createElement("label", { htmlFor: `target_${idx}` }, "Target "),
        React.createElement("select", { id: `target_${idx}`, value: stage.target },
            React.createElement("option", { value: "left" }, "Left"),
            React.createElement("option", { value: "right" }, "Right"),
            React.createElement("option", { value: "rgb" }, "RGB"),
            React.createElement("option", { value: "depth" }, "Depth"))));
}
function StageApriltag({ config, stage, idx }) {
    return (React.createElement(React.Fragment, null,
        React.createElement("legend", null, "AprilTag"),
        "Detect AprilTags",
        React.createElement("label", { htmlFor: `target_${idx}` }, "Camera"),
        React.createElement("select", { id: `target_${idx}`, value: stage.target },
            React.createElement("option", { value: "left" }, "Left"),
            React.createElement("option", { value: "right" }, "Right"),
            React.createElement("option", { value: "rgb" }, "RGB"),
            React.createElement("option", { value: "depth" }, "Depth"))));
}
function StageMono({ stage, idx }) {
    return (React.createElement(React.Fragment, null,
        React.createElement("legend", null, "Mono"),
        "Configure IR camera",
        React.createElement("label", { htmlFor: `target_${idx}` }, "Target "),
        React.createElement("select", { id: `target_${idx}`, value: stage.target },
            React.createElement("option", { value: "left" }, "Left"),
            React.createElement("option", { value: "right" }, "Right"))));
}
function StageRgb({ stage, idx }) {
    return (React.createElement(React.Fragment, null,
        React.createElement("legend", null, "Color Camera"),
        "Configure color camera"));
}
function StageDepth({ stage, idx }) {
    return (React.createElement(React.Fragment, null,
        React.createElement("legend", null, "Stereo Depth"),
        "Configure stereo depth"));
}
function StageObjectDetection({ stage, idx }) {
    return (React.createElement(React.Fragment, null,
        React.createElement("legend", null, "Object Detection"),
        "Detect objects"));
}
function StageSaveImage({ stage, idx }) {
    return (React.createElement(React.Fragment, null,
        React.createElement("legend", null, "Save Image"),
        "Save image from camera to file",
        React.createElement("label", { htmlFor: `saveImagePath-${idx}` }, "Path"),
        React.createElement("input", { id: `saveImagePath-${idx}`, type: "text" }),
        React.createElement("label", { htmlFor: `target_${idx}` }, "Camera"),
        React.createElement("select", { id: `target_${idx}`, value: stage.target },
            React.createElement("option", { value: "left" }, "Left IR"),
            React.createElement("option", { value: "right" }, "Right IR"),
            React.createElement("option", { value: "rgb" }, "Color camer"))));
}
function StageShow({ stage, idx }) {
    return (React.createElement(React.Fragment, null,
        React.createElement("legend", null, "Show Image"),
        "Show image on device (for debugging only)"));
}
function StageTelemetry({ stage, idx }) {
    return (React.createElement(React.Fragment, null,
        React.createElement("legend", null, "Telemetry")));
}
const stages = {
    'inherit': StageInherit,
    'web': StageWeb,
    'apriltag': StageApriltag,
    'mono': StageMono,
    'rgb': StageRgb,
    'depth': StageDepth,
    'nn': StageObjectDetection,
    'save': StageSaveImage,
    'show': StageShow,
    'telemetry': StageTelemetry,
};
function renderInner(config, stage, idx, onChange) {
    const Element = stages[stage.stage];
    if (Element)
        return React.createElement(React.Fragment, null,
            React.createElement("input", { type: "checkbox", checked: true /* TODO */ }),
            React.createElement(Element, { config: config, stage: stage, idx: idx }));
    return (React.createElement("span", null,
        "Unknown stage ",
        stage.stage));
}
function targetsRemaining(stages, type, values) {
    const unique = stages.filter(stage => stage.stage == type);
    const remaining = new Set(values);
    for (const e of unique)
        remaining.delete(e.target);
    return values.filter(value => remaining.has(value));
}
function makeDefault(config, stages, stage) {
    switch (stage) {
        case 'inherit':
            return {
                stage: 'inherit',
                id: config.pipelines[0].id,
            };
        case 'apriltag':
            return {
                stage: 'apriltag',
                runtime: 'host',
                camera: 'left',
                quadDecimate: 1,
                quadSigma: 0,
                refineEdges: true,
                numIterations: 40,
                hammingDist: 0,
                decisionMargin: 35,
            };
        case 'mono':
            return {
                stage: 'mono',
                target: targetsRemaining(stages, 'mono', ['left', 'right'])[0],
            };
        case 'depth':
        case 'rgb':
            return { stage };
        case 'web':
            return {
                stage: 'web',
                target: targetsRemaining(stages, 'web', ['left', 'right', 'depth', 'rgb'])[0],
            };
        case 'save':
            return { stage: 'save', target: 'left', path: '' };
        case 'nn':
            return {
                stage: 'nn',
                blobPath: '',
                config: {
                    anchor_masks: {},
                    anchors: [],
                    classes: 0,
                    confidence_threshold: 0.9,
                    coordinateSize: 0.5,
                    labels: [],
                    iou_threshold: 0.5,
                    depthLowerThreshold: 0,
                    depthUpperThreshold: 0,
                },
            };
        default:
            return {};
    }
}
export default function PipelineStages({ config, stages, onChange, ...props }) {
    const [addOption, setAddOption] = React.useState('inherit');
    function disableUnique(type) {
        return !!stages.find(stage => stage.stage == type);
    }
    function disableTargets(type, values) {
        return targetsRemaining(stages, type, values).length === 0;
    }
    return (React.createElement("fieldset", null,
        React.createElement("legend", null,
            "Pipeline ",
            props.legend),
        stages.map((stage, i) => (React.createElement("fieldset", { key: `stage-${i}` }, renderInner(config, stage, i, onChange)))),
        onChange && React.createElement(React.Fragment, null,
            React.createElement("label", { htmlFor: 'ps_addoption' }, "Add stage"),
            React.createElement("select", { id: "ps_addoption", value: addOption, onChange: e => setAddOption(e.currentTarget.value) },
                React.createElement("option", { value: "inherit", disabled: config.pipelines.length == 0 }, "Inherit"),
                React.createElement("option", { value: "web", disabled: disableTargets('web', ['left', 'right', 'rgb', 'depth']) }, "Web"),
                React.createElement("option", { value: "mono", disabled: disableTargets('mono', ['left', 'right']) }, "IR Camera"),
                React.createElement("option", { value: "rgb", disabled: disableUnique('rgb') }, "Color Camera"),
                React.createElement("option", { value: "stereo", disabled: disableUnique('depth') }, "Stereo Depth"),
                React.createElement("option", { value: "slam", disabled: disableUnique('slam') }, "SLAM"),
                React.createElement("option", { value: "show" }, "Show"),
                React.createElement("option", { value: "nn", disabled: disableUnique('nn') }, "Object Detection"),
                React.createElement("option", { value: "save" }, "Save Image"),
                React.createElement("option", { value: "telemetry", disabled: disableUnique('telemetry') }, "Telemetry")),
            React.createElement("button", { onClick: e => {
                    onChange([
                        ...stages,
                        makeDefault(config, stages, addOption)
                    ]);
                } }, "Add"))));
}
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoic3RhZ2VzLmpzIiwic291cmNlUm9vdCI6IiIsInNvdXJjZXMiOlsiLi4vLi4vLi4vdHMvcm91dGUvQ29uZmlnQnVpbGRlci9zdGFnZXMudHN4Il0sIm5hbWVzIjpbXSwibWFwcGluZ3MiOiJBQUFBLE9BQU8sS0FBSyxNQUFNLE9BQU8sQ0FBQztBQVMxQixTQUFTLFlBQVksQ0FBQyxFQUFFLE1BQU0sRUFBRSxLQUFLLEVBQTRCO0lBQ2hFLE9BQU8sQ0FBQztRQUNQLDhDQUF3QjtRQUN4QixvQkFBQyxjQUFjLElBQ2QsTUFBTSxFQUFFLE1BQU0sRUFDZCxNQUFNLEVBQUUsTUFBTSxDQUFDLFNBQVMsQ0FBQyxJQUFJLENBQUMsQ0FBQyxDQUFDLEVBQUUsQ0FBQyxDQUFDLENBQUMsRUFBRSxJQUFJLEtBQUssQ0FBQyxFQUFFLENBQUUsQ0FBQyxNQUFNLEVBQzVELE1BQU0sRUFBRSxDQUNQLGdDQUFRLEtBQUssRUFBRSxLQUFLLENBQUMsRUFBRSxJQUNyQixNQUFNLENBQUMsU0FBUyxDQUFDLEdBQUcsQ0FBQyxRQUFRLENBQUMsRUFBRSxDQUFDLENBQ2pDLGdDQUFRLEdBQUcsRUFBRSxRQUFRLENBQUMsRUFBRTs7Z0JBQVksUUFBUSxDQUFDLEVBQUUsQ0FBVSxDQUN6RCxDQUFDLENBQ00sQ0FDVCxHQUNBLENBQ0EsQ0FBQyxDQUFDO0FBQ04sQ0FBQztBQUNELFNBQVMsUUFBUSxDQUFDLEVBQUUsTUFBTSxFQUFFLEtBQUssRUFBRSxHQUFHLEVBQThCO0lBQ25FLE9BQU8sQ0FBQztRQUNQLDBDQUFvQjs7UUFFcEIsK0JBQU8sT0FBTyxFQUFFLFVBQVUsR0FBRyxFQUFFLGNBQWlCO1FBQ2hELGdDQUFRLEVBQUUsRUFBRSxVQUFVLEdBQUcsRUFBRSxFQUFFLEtBQUssRUFBRSxLQUFLLENBQUMsTUFBTTtZQUMvQyxnQ0FBUSxLQUFLLEVBQUMsTUFBTSxXQUFjO1lBQ2xDLGdDQUFRLEtBQUssRUFBQyxPQUFPLFlBQWU7WUFDcEMsZ0NBQVEsS0FBSyxFQUFDLEtBQUssVUFBYTtZ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