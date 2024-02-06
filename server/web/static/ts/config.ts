
export interface CameraInfo {
    mxid: string;
    name: string;
}

export interface NNConfig {
	confidence_threshold: number;
	iou_threshold: number;
	labels: string[];
	depthLowerThreshold: number;
	depthUpperThreshold: number;
	classes: number;
	coordinateSize: number;
	anchors: number[];
	anchor_masks: Record<string, number[]>;
}

export interface InheritStage {
    stage: 'inherit';
    id: string;
}
export interface RgbConfigStage {
    stage: 'rgb';
}
export interface MonoConfigStage {
    stage: 'mono';
    target: 'left' | 'right';
}
export interface DepthConfigStage {
    stage: 'depth';
}
export interface ObjectDetectionStage {
    stage: 'nn';
    config: NNConfig;
    blobPath: string;
}

export interface WebStreamStage {
    stage: 'web';
    target: 'left' | 'right' | 'rgb' | 'depth';
    maxFramerate?: number;
}
export interface ShowStage {
    stage: 'show';
    target: 'left' | 'right' | 'rgb' | 'depth';
}
export interface ApriltagStage {
    stage: 'apriltag';
    runtime: 'device' | 'host';
    camera: 'left' | 'right' | 'rgb';
	// apriltags: Union[apriltag.AprilTagFieldRef, apriltag.InlineAprilTagField]

    quadDecimate: number;
	quadSigma: number;
	refineEdges: boolean;
	numIterations: number;
	hammingDist: number;
	decisionMargin: number;
}

export interface TelemetryStage {
    stage: 'telemetry';
}

export interface SaveStage {
    stage: 'save';
    target: 'rgb' | 'left' | 'right';
    path: string;
}

export interface SlamStage {
    stage: 'slam';
    slam: boolean;
    vio: boolean;
    map_save?: string;
    map_load?: string;
    apriltags?: any;
}

export type StageTypes = {
    'inherit': InheritStage,
    'apriltag': ApriltagStage,
    'web': WebStreamStage,
    'nn': ObjectDetectionStage,
    'depth': DepthConfigStage,
    'mono': MonoConfigStage,
    'rgb': RgbConfigStage,
    'slam': SlamStage,
    'telemetry': TelemetryStage,
    'show': ShowStage,
    'save': SaveStage,
}

export type AnyStage = InheritStage | RgbConfigStage | MonoConfigStage | DepthConfigStage | ObjectDetectionStage | WebStreamStage | ApriltagStage | SlamStage
    | TelemetryStage | ShowStage | SaveStage;

export interface Pose3d {

}

export interface Transform3d {

}

export interface OakSelector {
    ordinal?: number;
    mxid?: string;
    name?: string;
    platform?: string;
    protocol?: string;
}
export interface CameraSelectorConfig extends OakSelector {
    id: string;
    pose?: Pose3d;
}
export interface PipelineDefinition {
    id: string;
    stages: AnyStage[];
}
export interface CameraConfig {
    id?: string;
    selector: string | OakSelector;
    max_usb?: "FULL" | "HIGH" | "LOW" | "SUPER" | "SUPER_PLUS" | "UNKNOWN";
    // retry: common.RetryConfig = Field(default_factory=common.RetryConfig)
    pose?: Transform3d;
    pipeline?: string | AnyStage[];
}
export interface LocalConfig {
    allow_overwrite:boolean
    // nt: NetworkTablesConfig;
    camera_selectors: CameraSelectorConfig[]
    pipelines: PipelineDefinition[]
    cameras: CameraConfig[]
}