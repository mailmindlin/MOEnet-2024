import React from 'react';
import { Binding, BoundCheckbox, BoundSelect } from './bound';
import { AprilTagFieldSelector } from './apriltag';
function RenderStage({ stage, title, description, children, onChange, onDelete }) {
    const Bound = Binding(stage, onChange);
    return (React.createElement("fieldset", null,
        title && React.createElement("legend", null, title),
        description && React.createElement("div", null, description),
        React.createElement(Bound.Checkbox, { name: 'enabled', label: 'Enabled', defaultValue: true }),
        React.createElement(Bound.Checkbox, { name: 'optional', label: 'Optional', defaultValue: false }),
        children,
        onDelete && (React.createElement("div", null,
            React.createElement("button", { onClick: onDelete }, "Delete")))));
}
function StageInherit({ config, stage, onChange, ...props }) {
    return (React.createElement(RenderStage, { title: 'Inherit', stage: stage, onChange: onChange, ...props },
        React.createElement(PipelineStages, { config: config, stages: /* TODO: Handle inconsistency */ (config.pipelines ?? []).find(p => p.id == stage.id).stages, legend: (React.createElement(BoundSelect, { value: stage, name: 'id', onChange: onChange, label: 'Pipeline' }, config.pipelines.map(pipeline => (React.createElement("option", { key: pipeline.id }, pipeline.id))))) })));
}
function StageWeb({ stage, onChange, ...props }) {
    return (React.createElement(RenderStage, { title: 'Web', description: 'Stream images to web server', stage: stage, onChange: onChange, ...props },
        React.createElement(BoundSelect, { label: 'Target', value: stage, name: 'target', onChange: onChange },
            React.createElement("option", { value: "left" }, "Left"),
            React.createElement("option", { value: "right" }, "Right"),
            React.createElement("option", { value: "rgb" }, "RGB"),
            React.createElement("option", { value: "depth" }, "Depth"))));
}
function StageApriltag({ onChange, stage, ...props }) {
    const Bound = Binding(stage, onChange);
    return (React.createElement(RenderStage, { title: 'AprilTag', description: 'Detect AprilTags', stage: stage, onChange: onChange, ...props },
        React.createElement(Bound.Select, { label: 'Runtime', name: 'runtime' },
            React.createElement("option", { value: "host" }, "Host"),
            React.createElement("option", { value: "device" }, "Device (OAK camera)")),
        React.createElement(Bound.Select, { label: 'Camera', name: 'camera' },
            React.createElement("option", { value: "left" }, "Left"),
            React.createElement("option", { value: "right" }, "Right"),
            React.createElement("option", { value: "rgb" }, "RGB")),
        React.createElement(Bound.Checkbox, { label: 'Async', name: 'detectorAsync', help: "Should we run the detector on a different thread? Only useful if we're doing multiple things with the same camera" }),
        React.createElement(Bound.Number, { label: 'Detector Threads', name: 'detectorThreads', min: 1, nullable: true, help: 'How many threads should be used for computation' }),
        React.createElement(Bound.Number, { label: 'Decode Sharpening', name: 'decodeSharpening', min: 0, nullable: true, help: 'How much sharpening should be done to decoded images' }),
        React.createElement(Bound.Number, { label: 'Quad Decimate', name: 'quadDecimate', min: 0, step: 'any', nullable: true }),
        React.createElement(Bound.Number, { label: 'Quad Sigma', name: 'quadSigma', min: 0, step: 'any', nullable: true }),
        React.createElement(Bound.Checkbox, { label: 'Refine Edges', name: 'refineEdges' }),
        React.createElement(Bound.Number, { label: 'Hamming Distance', name: 'hammingDist', min: 0, max: 3, help: 'Maximum number of bits to correct' }),
        React.createElement(Bound.Number, { label: 'Decision Margin', name: 'decisionMargin', min: 0, step: 'any', nullable: true }),
        React.createElement(Bound.Number, { label: '# Iterations', name: 'numIterations', min: 0, nullable: true }),
        React.createElement(Bound.Checkbox, { label: 'Undistort', name: 'undistort', help: "Should we try to undistort the camera lens?" }),
        React.createElement(Bound.Checkbox, { label: 'Solve PnP', name: 'solvePNP', help: 'Compute position (PnP) from AprilTag detections' }),
        React.createElement(Bound.Checkbox, { label: 'Multi Target', name: 'doMultiTarget', help: 'Run SolvePnP with multiple AprilTags in a single frame' }),
        React.createElement(Bound.Checkbox, { label: 'Single Target Always?', name: 'doSingleTargetAlways', help: 'Always run SolvePnP for each AprilTag detection individually' }),
        React.createElement(AprilTagFieldSelector, { value: stage.apriltags, onChange: onChange && React.useCallback((apriltags) => onChange({ ...stage, apriltags }), [stage]) })));
}
function StageMono({ stage, onChange, ...props }) {
    return (React.createElement(RenderStage, { title: 'IR Camera', description: 'Configure IR camera', stage: stage, onChange: onChange, ...props },
        React.createElement(BoundSelect, { label: 'Camera', value: stage, name: 'target', onChange: onChange },
            React.createElement("option", { value: "left" }, "Left"),
            React.createElement("option", { value: "right" }, "Right")),
        React.createElement(BoundSelect, { label: 'Sensor Resolution', value: stage, name: 'resolution', onChange: onChange },
            React.createElement("option", { value: "$null" }, "Default"),
            React.createElement("option", { value: "THE_400_P" }, "400p"),
            React.createElement("option", { value: "THE_480_P" }, "480p"),
            React.createElement("option", { value: "THE_720_P" }, "720p"),
            React.createElement("option", { value: "THE_800_P" }, "800p"),
            React.createElement("option", { value: "THE_1200_P" }, "1200p"))));
}
function StageRgb({ stage, onChange, ...props }) {
    return (React.createElement(RenderStage, { title: 'Color Camera', description: 'Configure color camera', stage: stage, onChange: onChange, ...props },
        React.createElement(BoundSelect, { label: 'Sensor Resolution', value: stage, name: 'resolution', onChange: onChange },
            React.createElement("option", { value: "$null" }, "Default"),
            React.createElement("option", { value: "THE_720_P" }, "720p"),
            React.createElement("option", { value: "THE_800_P" }, "800p"),
            React.createElement("option", { value: "THE_1080_P" }, "1080p"),
            React.createElement("option", { value: "THE_1200_P" }, "1200p"),
            React.createElement("option", { value: "THE_4_K" }, "4k"),
            React.createElement("option", { value: "THE_4000X3000" }, "4000x3000"),
            React.createElement("option", { value: "THE_5312X6000" }, "5312x6000"),
            React.createElement("option", { value: "THE_1440X1080" }, "1440x1080"),
            React.createElement("option", { value: "THE_1352X1012" }, "1352x1012"),
            React.createElement("option", { value: "THE_2024X1520" }, "2024x1520"),
            React.createElement("option", { value: "THE_5_MP" }, "5 MP"),
            React.createElement("option", { value: "THE_12_MP" }, "12 MP"),
            React.createElement("option", { value: "THE_13_MP" }, "13 MP"),
            React.createElement("option", { value: "THE_48_MP" }, "48 MP"))));
}
function StageDepth({ stage, onChange, ...props }) {
    return (React.createElement(RenderStage, { title: 'Stereo Depth', description: 'Configure stereo depth', stage: stage, onChange: onChange, ...props },
        React.createElement(BoundCheckbox, { value: stage, onChange: onChange, name: 'checkLeftRight', label: 'Check Left/Right' }),
        React.createElement(BoundCheckbox, { value: stage, onChange: onChange, name: 'extendedDisparity', label: 'Extended Disparity' }),
        React.createElement(BoundSelect, { label: 'Preset', value: stage, name: 'preset', onChange: onChange },
            React.createElement("option", { value: "$null" }, "None"),
            React.createElement("option", { value: "high_accuracy" }, "High Accuracy"),
            React.createElement("option", { value: "high_density" }, "High Density"))));
}
function StageObjectDetection({ stage, onChange, ...props }) {
    return (React.createElement(RenderStage, { title: 'Object Detection', description: 'Detect Objects', stage: stage, onChange: onChange, ...props }));
}
function StageSaveImage({ stage, idx, onChange, ...props }) {
    return (React.createElement(RenderStage, { title: 'Save Image', description: 'Save images from camera to disk', stage: stage, onChange: onChange, ...props },
        React.createElement("label", { htmlFor: `saveImagePath-${idx}` }, "Path"),
        React.createElement("input", { id: `saveImagePath-${idx}`, type: "text" }),
        React.createElement(BoundSelect, { label: 'Camera', value: stage, name: 'target', onChange: onChange },
            React.createElement("option", { value: "left" }, "Left IR"),
            React.createElement("option", { value: "right" }, "Right IR"),
            React.createElement("option", { value: "rgb" }, "Color"))));
}
function StageShow({ stage, onChange, ...props }) {
    return (React.createElement(RenderStage, { title: 'Show Image', description: 'Show image on device (for debugging only)', stage: stage, onChange: onChange, ...props },
        React.createElement(BoundSelect, { label: 'Camera', value: stage, name: 'target', onChange: onChange },
            React.createElement("option", { value: "left" }, "Left IR"),
            React.createElement("option", { value: "right" }, "Right IR"),
            React.createElement("option", { value: "rgb" }, "Color"))));
}
function StageTelemetry({ stage, onChange, ...props }) {
    return (React.createElement(RenderStage, { title: 'Telemetry', description: 'Fetch device telemetry', stage: stage, onChange: onChange, ...props }));
}
function StageSlam({ stage, onChange, ...props }) {
    return (React.createElement(RenderStage, { title: 'SLAM', description: 'SpectacularAI SLAM', stage: stage, onChange: onChange, ...props },
        React.createElement(BoundCheckbox, { value: stage, onChange: onChange, name: 'slam', label: 'Enable SLAM' }),
        React.createElement(BoundCheckbox, { value: stage, onChange: onChange, name: 'vio', label: 'Enable VIO' }),
        React.createElement(BoundCheckbox, { value: stage, onChange: onChange, name: 'waitForPose', label: 'Wait for pose' })));
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
    'slam': StageSlam,
};
function renderInner(config, stage, idx, onChange, onDelete) {
    const Element = stages[stage.stage];
    const key = `stage-${idx}`;
    if (Element)
        return React.createElement(Element, { key: key, config: config, stage: stage, idx: idx, onChange: onChange, onDelete: onDelete });
    return (React.createElement("span", { key: key },
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
                id: config.pipelines?.[0]?.id ?? 'unknown',
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
                apriltags: '2024Crescendo',
            };
        case 'mono':
            return {
                stage: 'mono',
                target: targetsRemaining(stages, 'mono', ['left', 'right'])[0],
            };
        case 'depth':
        case 'rgb':
        case 'slam':
        case 'telemetry':
            return { stage };
        case 'show':
            return {
                stage: 'show',
                target: targetsRemaining(stages, 'show', ['left', 'right', 'rgb', 'depth'])[0],
            };
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
    const asId = React.useId();
    // Disable adding stages that must be unique
    function disableUnique(type) {
        return !!stages.find(stage => stage.stage == type);
    }
    // Disable targets that must be unique
    function disableTargets(type, values) {
        return targetsRemaining(stages, type, values).length === 0;
    }
    function replaceStage(idx, stage) {
        onChange([
            ...stages.slice(0, idx),
            stage,
            ...stages.slice(idx + 1),
        ]);
    }
    function deleteStage(idx) {
        onChange([
            ...stages.slice(0, idx),
            ...stages.slice(idx + 1),
        ]);
    }
    return (React.createElement("fieldset", null,
        React.createElement("legend", null, props.legend),
        stages.map((stage, i) => (renderInner(config, stage, i, onChange ? replaceStage.bind(replaceStage, i) : undefined, onChange ? deleteStage.bind(null, i) : undefined))),
        onChange && React.createElement(React.Fragment, null,
            React.createElement("label", { htmlFor: asId }, "Add stage\u00A0"),
            React.createElement("select", { id: asId, value: addOption, onChange: e => setAddOption(e.currentTarget.value) },
                React.createElement("option", { value: "inherit", disabled: config.pipelines?.length == 0 }, "Inherit"),
                React.createElement("option", { value: "web", disabled: disableTargets('web', ['left', 'right', 'rgb', 'depth']) }, "Web"),
                React.createElement("option", { value: "mono", disabled: disableTargets('mono', ['left', 'right']) }, "IR Camera"),
                React.createElement("option", { value: "rgb", disabled: disableUnique('rgb') }, "Color Camera"),
                React.createElement("option", { value: "depth", disabled: disableUnique('depth') }, "Stereo Depth"),
                React.createElement("option", { value: "slam", disabled: disableUnique('slam') }, "SLAM"),
                React.createElement("option", { value: "apriltag", disabled: disableUnique('apriltag') }, "AprilTag"),
                React.createElement("option", { value: "show" }, "Show"),
                React.createElement("option", { value: "nn", disabled: disableUnique('nn') }, "Object Detection"),
                React.createElement("option", { value: "save" }, "Save Image"),
                React.createElement("option", { value: "telemetry", disabled: disableUnique('telemetry') }, "Telemetry")),
            React.createElement("button", { onClick: () => {
                    onChange([
                        ...stages,
                        makeDefault(config, stages, addOption)
                    ]);
                } }, "Add")),
        props.onDelete && React.createElement("div", null,
            React.createElement("button", { onClick: props.onDelete }, "Delete Pipeline"))));
}
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoic3RhZ2VzLmpzIiwic291cmNlUm9vdCI6IiIsInNvdXJjZXMiOlsiLi4vLi4vLi4vdHMvcm91dGUvQ29uZmlnQnVpbGRlci9zdGFnZXMudHN4Il0sIm5hbWVzIjpbXSwibWFwcGluZ3MiOiJBQUFBLE9BQU8sS0FBc0IsTUFBTSxPQUFPLENBQUM7QUFFM0MsT0FBTyxFQUFFLE9BQU8sRUFBRSxhQUFhLEVBQUUsV0FBVyxFQUFxQixNQUFNLFNBQVMsQ0FBQztBQUNqRixPQUFPLEVBQUUscUJBQXFCLEVBQUUsTUFBTSxZQUFZLENBQUM7QUF5Qm5ELFNBQVMsV0FBVyxDQUFxQixFQUFFLEtBQUssRUFBRSxLQUFLLEVBQUUsV0FBVyxFQUFFLFFBQVEsRUFBRSxRQUFRLEVBQUUsUUFBUSxFQUF1QjtJQUN4SCxNQUFNLEtBQUssR0FBc0IsT0FBTyxDQUFDLEtBQUssRUFBRSxRQUFRLENBQUMsQ0FBQztJQUUxRCxPQUFPLENBQ047UUFDRyxLQUFLLElBQUksb0NBQVMsS0FBSyxDQUFVO1FBQ2xDLFdBQVcsSUFBSSxpQ0FBTSxXQUFXLENBQU87UUFDeEMsb0JBQUMsS0FBSyxDQUFDLFFBQVEsSUFDZCxJQUFJLEVBQUMsU0FBUyxFQUNkLEtBQUssRUFBQyxTQUFTLEVBQ2YsWUFBWSxFQUFFLElBQUksR0FDakI7UUFDRixvQkFBQyxLQUFLLENBQUMsUUFBUSxJQUNkLElBQUksRUFBQyxVQUFVLEVBQ2YsS0FBSyxFQUFDLFVBQVUsRUFDaEIsWUFBWSxFQUFFLEtBQUssR0FDbEI7UUFDQSxRQUFRO1FBQ1QsUUFBUSxJQUFJLENBQ1o7WUFDQyxnQ0FBUSxPQUFPLEVBQUUsUUFBUSxhQUFpQixDQUNyQyxDQUNOLENBQ1MsQ0FDWCxDQUFDO0FBQ0gsQ0FBQztBQUVELFNBQVMsWUFBWSxDQUFDLEVBQUUsTUFBTSxFQUFFLEtBQUssRUFBRSxRQUFRLEVBQUUsR0FBRyxLQUFLLEVBQWtDO0lBQzFGLE9BQU8sQ0FDTixvQkFBQyxXQUFXLElBQUMsS0FBSyxFQUFDLFNBQVMsRUFBQyxLQUFL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