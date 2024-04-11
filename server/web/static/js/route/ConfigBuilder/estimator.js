import React from 'react';
import { Binding } from './bound';
import Collapsible from '../../components/Collapsible';
export default function EstimatorConfigEditor(props) {
    const config = props.config ?? {};
    const ObjectDetection = Binding(config?.detections ?? {}, props.onChange ? detections => props.onChange({ ...config, detections }) : undefined);
    const PoseEstimator = Binding(config?.pose ?? {}, props.onChange ? pose => props.onChange({ ...config, pose }) : undefined);
    return (React.createElement(Collapsible, { legend: 'Data Fusion' },
        React.createElement("fieldset", null,
            React.createElement("legend", null, "Object Detections"),
            React.createElement(ObjectDetection.Number, { name: 'min_detections', label: 'Minimum Detections', defaultValue: 0, min: 0, help: "Minimum times to detect an object before 'seeing' it" }),
            React.createElement(ObjectDetection.Number, { name: 'clustering_distance', label: 'Clustering Distance', min: 0, defaultValue: 0.1, step: 'any', help: "" }),
            React.createElement(ObjectDetection.Number, { name: 'min_depth', label: 'Min Depth', defaultValue: 0, min: 0, step: 'any' }),
            React.createElement(ObjectDetection.Number, { name: 'alpha', label: 'Alpha', defaultValue: 0.2, step: 'any', min: 0, max: 1 })),
        React.createElement("fieldset", null,
            React.createElement("legend", null, "Pose Estimation"),
            React.createElement(PoseEstimator.Select, { name: 'apriltagStrategy', label: 'Algorithm', defaultValue: '' },
                React.createElement("option", null, "Simple 2d"),
                React.createElement("option", null, "Simple 2d"),
                React.createElement("option", { disabled: true }, "GTSAM")),
            React.createElement(PoseEstimator.Checkbox, { name: 'force2d', label: 'Force 2d', defaultValue: true, help: "Should we force the pose to fit on the field?" }),
            config?.pose?.force2d && React.createElement(React.Fragment, null),
            React.createElement(PoseEstimator.Select, { name: 'apriltagStrategy', label: 'AprilTag strategy', defaultValue: 'LOWEST_AMBIGUITY' },
                React.createElement("option", { value: "LOWEST_AMBIGUITY" }, "Lowest ambiguity"),
                React.createElement("option", { value: "CLOSEST_TO_LAST_POSE" }, "Closest to last pose"),
                React.createElement("option", { value: "AVERAGE_BEST_TARGETS" }, "Average best targets")))));
}
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiZXN0aW1hdG9yLmpzIiwic291cmNlUm9vdCI6IiIsInNvdXJjZXMiOlsiLi4vLi4vLi4vdHMvcm91dGUvQ29uZmlnQnVpbGRlci9lc3RpbWF0b3IudHN4Il0sIm5hbWVzIjpbXSwibWFwcGluZ3MiOiJBQUFBLE9BQU8sS0FBSyxNQUFNLE9BQU8sQ0FBQztBQUUxQixPQUFPLEVBQUUsT0FBTyxFQUFFLE1BQU0sU0FBUyxDQUFDO0FBQ2xDLE9BQU8sV0FBVyxNQUFNLDhCQUE4QixDQUFDO0FBT3ZELE1BQU0sQ0FBQyxPQUFPLFVBQVUscUJBQXFCLENBQUMsS0FBaUM7SUFDOUUsTUFBTSxNQUFNLEdBQUcsS0FBSyxDQUFDLE1BQU0sSUFBSSxFQUFFLENBQUM7SUFFbEMsTUFBTSxlQUFlLEdBQUcsT0FBTyxDQUFDLE1BQU0sRUFBRSxVQUFVLElBQUksRUFBRSxFQUFFLEtBQUssQ0FBQyxRQUFRLENBQUMsQ0FBQyxDQUFDLFVBQVUsQ0FBQyxFQUFFLENBQUMsS0FBSyxDQUFDLFFBQVMsQ0FBQyxFQUFDLEdBQUcsTUFBTSxFQUFFLFVBQVUsRUFBRSxDQUFDLENBQUMsQ0FBQyxDQUFDLFNBQVMsQ0FBQyxDQUFDO0lBQ2hKLE1BQU0sYUFBYSxHQUFHLE9BQU8sQ0FBQyxNQUFNLEVBQUUsSUFBSSxJQUFJLEVBQUUsRUFBRSxLQUFLLENBQUMsUUFBUSxDQUFDLENBQUMsQ0FBQyxJQUFJLENBQUMsRUFBRSxDQUFDLEtBQUssQ0FBQyxRQUFTLENBQUMsRUFBQyxHQUFHLE1BQU0sRUFBRSxJQUFJLEVBQUUsQ0FBQyxDQUFDLENBQUMsQ0FBQyxTQUFTLENBQUMsQ0FBQztJQUM1SCxPQUFPLENBQ04sb0JBQUMsV0FBVyxJQUFDLE1BQU0sRUFBQyxhQUFhO1FBQ2hDO1lBQ0Msd0RBQWtDO1lBQ2xDLG9CQUFDLGVBQWUsQ0FBQyxNQUFNLElBQ3RCLElBQUksRUFBQyxnQkFBZ0IsRUFDckIsS0FBSyxFQUFDLG9CQUFvQixFQUMxQixZQUFZLEVBQUUsQ0FBQyxFQUNmLEdBQUcsRUFBRSxDQUFDLEVBQ04sSUFBSSxFQUFDLHNEQUFzRCxHQUMxRDtZQUNGLG9CQUFDLGVBQWUsQ0FBQyxNQUFNLElBQ3RCLElBQUksRUFBQyxxQkFBcUIsRUFDMUIsS0FBSyxFQUFDLHFCQUFxQixFQUMzQixHQUFHLEVBQUUsQ0FBQyxFQUNOLFlBQVksRUFBRSxHQUFHLEVBQ2pCLElBQUksRUFBQyxLQUFLLEVBQ1YsSUFBSSxFQUFDLEVBQUUsR0FDTjtZQUNGLG9CQUFDLGVBQWUsQ0FBQyxNQUFNLElBQ3RCLElBQUksRUFBQyxXQUFXLEVBQ2hCLEtBQUssRUFBQyxXQUFXLEVBQ2pCLFlBQVksRUFBRSxDQUFDLEVBQ2YsR0FBRyxFQUFFLENBQUMsRUFDTixJQUFJLEVBQUMsS0FBSyxHQUNUO1lBQ0Ysb0JBQUMsZUFBZSxDQUFDLE1BQU0sSUFDdEIsSUFBSSxFQUFDLE9BQU8sRUFDWixLQUFLLEVBQUMsT0FBTyxFQUNiLFlBQVksRUFBRSxHQUFHLEVBQ2pCLElBQUksRUFBQyxLQUFLLEVBQ1YsR0FBRyxFQUFFLENBQUMsRUFDTixHQUFHLEVBQUUsQ0FBQyxHQUNMLENBQ1E7UUFDWDtZQUNDLHNEQUFnQztZQUNoQyxvQkFBQyxhQUFhLENBQUMsTUFBTSxJQUFDLElBQUksRUFBQyxrQkFBa0IsRUFBQyxLQUFLLEVBQUMsV0FBVyxFQUFDLFlBQVksRUFBQyxFQUFFO2dCQUM5RSxnREFBMEI7Z0JBQzFCLGdEQUEwQjtnQkFDMUIsZ0NBQVEsUUFBUSxrQkFBZSxDQUNUO1lBQ3ZCLG9CQUFDLGFBQWEsQ0FBQyxRQUFRLElBQUMsSUFBSSxFQUFDLFNBQVMsRUFBQyxLQUFLLEVBQUMsVUFBVSxFQUFDLFlBQVksRUFBRSxJQUFJLEVBQUUsSUFBSSxFQUFDLCtDQUErQyxHQUFFO1lBQ2pJLE1BQU0sRUFBRSxJQUFJLEVBQUUsT0FBTyxJQUFJLHlDQUV2QjtZQUNILG9CQUFDLGFBQWEsQ0FBQyxNQUFNLElBQUMsSUFBSSxFQUFDLGtCQUFrQixFQUFDLEtBQUssRUFBQyxtQkFBbUIsRUFBQyxZQUFZLEVBQUMsa0JBQWtCO2dCQUN0RyxnQ0FBUSxLQUFLLEVBQUMsa0JBQWtCLHVCQUEwQjtnQkFDMUQsZ0NBQVEsS0FBSyxFQUFDLHNCQUFzQiwyQkFBOEI7Z0JBQ2xFLGdDQUFRLEtBQUssRUFBQyxzQkFBc0IsMkJBQThCLENBQzVDLENBQ2IsQ0FDRSxDQUNkLENBQUM7QUFDSCxDQUFDIn0=