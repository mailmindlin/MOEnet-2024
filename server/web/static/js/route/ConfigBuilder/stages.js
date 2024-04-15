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
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoic3RhZ2VzLmpzIiwic291cmNlUm9vdCI6IiIsInNvdXJjZXMiOlsiLi4vLi4vLi4vdHMvcm91dGUvQ29uZmlnQnVpbGRlci9zdGFnZXMudHN4Il0sIm5hbWVzIjpbXSwibWFwcGluZ3MiOiJBQUFBLE9BQU8sS0FBSyxNQUFNLE9BQU8sQ0FBQztBQUUxQixPQUFPLEVBQUUsT0FBTyxFQUFFLGFBQWEsRUFBRSxXQUFXLEVBQUUsTUFBTSxTQUFTLENBQUM7QUFDOUQsT0FBTyxFQUFFLHFCQUFxQixFQUFFLE1BQU0sWUFBWSxDQUFDO0FBd0JuRCxTQUFTLFdBQVcsQ0FBcUIsRUFBRSxLQUFLLEVBQUUsS0FBSyxFQUFFLFdBQVcsRUFBRSxRQUFRLEVBQUUsUUFBUSxFQUFFLFFBQVEsRUFBdUI7SUFDeEgsTUFBTSxLQUFLLEdBQXNCLE9BQU8sQ0FBQyxLQUFLLEVBQUUsUUFBUSxDQUFDLENBQUM7SUFFMUQsT0FBTyxDQUNOO1FBQ0csS0FBSyxJQUFJLG9DQUFTLEtBQUssQ0FBVTtRQUNsQyxXQUFXLElBQUksaUNBQU0sV0FBVyxDQUFPO1FBQ3hDLG9CQUFDLEtBQUssQ0FBQyxRQUFRLElBQ2QsSUFBSSxFQUFDLFNBQVMsRUFDZCxLQUFLLEVBQUMsU0FBUyxFQUNmLFlBQVksRUFBRSxJQUFJLEdBQ2pCO1FBQ0Ysb0JBQUMsS0FBSyxDQUFDLFFBQVEsSUFDZCxJQUFJLEVBQUMsVUFBVSxFQUNmLEtBQUssRUFBQyxVQUFVLEVBQ2hCLFlBQVksRUFBRSxLQUFLLEdBQ2xCO1FBQ0EsUUFBUTtRQUNULFFBQVEsSUFBSSxDQUNaO1lBQ0MsZ0NBQVEsT0FBTyxFQUFFLFFBQVEsYUFBaUIsQ0FDckMsQ0FDTixDQUNTLENBQ1gsQ0FBQztBQUNILENBQUM7QUFFRCxTQUFTLFlBQVksQ0FBQyxFQUFFLE1BQU0sRUFBRSxLQUFLLEVBQUUsUUFBUSxFQUFFLEdBQUcsS0FBSyxFQUFrQztJQUMxRixPQUFPLENBQ04sb0JBQUMsV0FBVyxJQUFDLEtBQUssRUFBQyxTQUFTLEVBQUMsS0FBSyxF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