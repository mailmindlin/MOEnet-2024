import React from 'react';
import { Binding, BoundCheckbox, BoundSelect, bindChangeHandler } from './bound';
import { AprilTagFieldSelector } from './apriltag';
function RenderStage({ stage, title, description, children, onChange, onDelete }) {
    const id = React.useId();
    return (React.createElement("fieldset", null,
        title && React.createElement("legend", null, title),
        description && React.createElement("div", null, description),
        React.createElement("div", null,
            React.createElement("label", { htmlFor: `${id}-enabled` }, "Enabled"),
            React.createElement("input", { id: `${id}-enabled`, type: "checkbox", checked: stage.enabled ?? true, disabled: !onChange, onChange: bindChangeHandler(stage, 'enabled', onChange) })),
        React.createElement("div", null,
            React.createElement("label", { htmlFor: `${id}-optional` }, "Optional"),
            React.createElement("input", { id: `${id}-optional`, type: "checkbox", checked: stage.optional ?? false, disabled: !onChange, onChange: bindChangeHandler(stage, 'optional', onChange) })),
        children,
        onDelete && (React.createElement("div", null,
            React.createElement("button", { onClick: onDelete }, "Delete")))));
}
function StageInherit({ config, stage, onChange, ...props }) {
    return (React.createElement(RenderStage, { title: 'Inherit', stage: stage, onChange: onChange, ...props },
        React.createElement(PipelineStages, { config: config, stages: config.pipelines.find(p => p.id == stage.id).stages, legend: (React.createElement("select", { value: stage.id, disabled: !onChange, onChange: bindChangeHandler(stage, 'stage', onChange) }, config.pipelines.map(pipeline => (React.createElement("option", { key: pipeline.id },
                "Pipeline ",
                pipeline.id))))) })));
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
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoic3RhZ2VzLmpzIiwic291cmNlUm9vdCI6IiIsInNvdXJjZXMiOlsiLi4vLi4vLi4vdHMvcm91dGUvQ29uZmlnQnVpbGRlci9zdGFnZXMudHN4Il0sIm5hbWVzIjpbXSwibWFwcGluZ3MiOiJBQUFBLE9BQU8sS0FBc0IsTUFBTSxPQUFPLENBQUM7QUFFM0MsT0FBTyxFQUFFLE9BQU8sRUFBRSxhQUFhLEVBQUUsV0FBVyxFQUFFLGlCQUFpQixFQUFFLE1BQU0sU0FBUyxDQUFDO0FBQ2pGLE9BQU8sRUFBRSxxQkFBcUIsRUFBRSxNQUFNLFlBQVksQ0FBQztBQXlCbkQsU0FBUyxXQUFXLENBQXFCLEVBQUUsS0FBSyxFQUFFLEtBQUssRUFBRSxXQUFXLEVBQUUsUUFBUSxFQUFFLFFBQVEsRUFBRSxRQUFRLEVBQXVCO0lBQ3hILE1BQU0sRUFBRSxHQUFHLEtBQUssQ0FBQyxLQUFLLEVBQUUsQ0FBQztJQUV6QixPQUFPLENBQ047UUFDRyxLQUFLLElBQUksb0NBQVMsS0FBSyxDQUFVO1FBQ2xDLFdBQVcsSUFBSSxpQ0FBTSxXQUFXLENBQU87UUFDeEM7WUFDQywrQkFBTyxPQUFPLEVBQUUsR0FBRyxFQUFFLFVBQVUsY0FBaUI7WUFDaEQsK0JBQ0MsRUFBRSxFQUFFLEdBQUcsRUFBRSxVQUFVLEVBQ25CLElBQUksRUFBQyxVQUFVLEVBQ2YsT0FBTyxFQUFFLEtBQUssQ0FBQyxPQUFPLElBQUksSUFBSSxFQUM5QixRQUFRLEVBQUUsQ0FBQyxRQUFRLEVBQ25CLFFBQVEsRUFBRSxpQkFBaUIsQ0FBQyxLQUFLLEVBQUUsU0FBUyxFQUFFLFFBQVEsQ0FBQyxHQUN0RCxDQUNHO1FBQ047WUFDQywrQkFBTyxPQUFPLEVBQUUsR0FBRyxFQUFFLFdBQVcsZUFBa0I7WUFDbEQsK0JBQ0MsRUFBRSxFQUFFLEdBQUcsRUFBRSxXQUFXLEVBQ3BCLElBQUksRUFBQyxVQUFVLEVBQ2YsT0FBTyxFQUFFLEtBQUssQ0FBQyxRQUFRLElBQUksS0FBSyxFQUNoQyxRQUFRLEVBQUUsQ0FBQyxRQUFR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