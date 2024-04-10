import React from 'react';
import { Binding, Collapsible } from './bound';
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
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiZXN0aW1hdG9yLmpzIiwic291cmNlUm9vdCI6IiIsInNvdXJjZXMiOlsiLi4vLi4vLi4vdHMvcm91dGUvQ29uZmlnQnVpbGRlci9lc3RpbWF0b3IudHN4Il0sIm5hbWVzIjpbXSwibWFwcGluZ3MiOiJBQUFBLE9BQU8sS0FBSyxNQUFNLE9BQU8sQ0FBQztBQUUxQixPQUFPLEVBQThCLE9BQU8sRUFBRSxXQUFXLEVBQUUsTUFBTSxTQUFTLENBQUM7QUFPM0UsTUFBTSxDQUFDLE9BQU8sVUFBVSxxQkFBcUIsQ0FBQyxLQUFpQztJQUM5RSxNQUFNLE1BQU0sR0FBRyxLQUFLLENBQUMsTUFBTSxJQUFJLEVBQUUsQ0FBQztJQUVsQyxNQUFNLGVBQWUsR0FBRyxPQUFPLENBQUMsTUFBTSxFQUFFLFVBQVUsSUFBSSxFQUFFLEVBQUUsS0FBSyxDQUFDLFFBQVEsQ0FBQyxDQUFDLENBQUMsVUFBVSxDQUFDLEVBQUUsQ0FBQyxLQUFLLENBQUMsUUFBUyxDQUFDLEVBQUMsR0FBRyxNQUFNLEVBQUUsVUFBVSxFQUFFLENBQUMsQ0FBQyxDQUFDLENBQUMsU0FBUyxDQUFDLENBQUM7SUFDaEosTUFBTSxhQUFhLEdBQUcsT0FBTyxDQUFDLE1BQU0sRUFBRSxJQUFJLElBQUksRUFBRSxFQUFFLEtBQUssQ0FBQyxRQUFRLENBQUMsQ0FBQyxDQUFDLElBQUksQ0FBQyxFQUFFLENBQUMsS0FBSyxDQUFDLFFBQVMsQ0FBQyxFQUFDLEdBQUcsTUFBTSxFQUFFLElBQUksRUFBRSxDQUFDLENBQUMsQ0FBQyxDQUFDLFNBQVMsQ0FBQyxDQUFDO0lBQzVILE9BQU8sQ0FDTixvQkFBQyxXQUFXLElBQUMsTUFBTSxFQUFDLGFBQWE7UUFDaEM7WUFDQyx3REFBa0M7WUFDbEMsb0JBQUMsZUFBZSxDQUFDLE1BQU0sSUFDdEIsSUFBSSxFQUFDLGdCQUFnQixFQUNyQixLQUFLLEVBQUMsb0JBQW9CLEVBQzFCLFlBQVksRUFBRSxDQUFDLEVBQ2YsR0FBRyxFQUFFLENBQUMsRUFDTixJQUFJLEVBQUMsc0RBQXNELEdBQzFEO1lBQ0Ysb0JBQUMsZUFBZSxDQUFDLE1BQU0sSUFDdEIsSUFBSSxFQUFDLHFCQUFxQixFQUMxQixLQUFLLEVBQUMscUJBQXFCLEVBQzNCLEdBQUcsRUFBRSxDQUFDLEVBQ04sWUFBWSxFQUFFLEdBQUcsRUFDakIsSUFBSSxFQUFDLEtBQUssRUFDVixJQUFJLEVBQUMsRUFBRSxHQUNOO1lBQ0Ysb0JBQUMsZUFBZSxDQUFDLE1BQU0sSUFDdEIsSUFBSSxFQUFDLFdBQVcsRUFDaEIsS0FBSyxFQUFDLFdBQVcsRUFDakIsWUFBWSxFQUFFLENBQUMsRUFDZixHQUFHLEVBQUUsQ0FBQyxFQUNOLElBQUksRUFBQyxLQUFLLEdBQ1Q7WUFDRixvQkFBQyxlQUFlLENBQUMsTUFBTSxJQUN0QixJQUFJLEVBQUMsT0FBTyxFQUNaLEtBQUssRUFBQyxPQUFPLEVBQ2IsWUFBWSxFQUFFLEdBQUcsRUFDakIsSUFBSSxFQUFDLEtBQUssRUFDVixHQUFHLEVBQUUsQ0FBQyxFQUNOLEdBQUcsRUFBRSxDQUFDLEdBQ0wsQ0FDUTtRQUNYO1lBQ0Msc0RBQWdDO1lBQ2hDLG9CQUFDLGFBQWEsQ0FBQyxNQUFNLElBQUMsSUFBSSxFQUFDLGtCQUFrQixFQUFDLEtBQUssRUFBQyxXQUFXLEVBQUMsWUFBWSxFQUFDLEVBQUU7Z0JBQzlFLGdEQUEwQjtnQkFDMUIsZ0RBQTBCO2dCQUMxQixnQ0FBUSxRQUFRLGtCQUFlLENBQ1Q7WUFDdkIsb0JBQUMsYUFBYSxDQUFDLFFBQVEsSUFBQyxJQUFJLEVBQUMsU0FBUyxFQUFDLEtBQUssRUFBQyxVQUFVLEVBQUMsWUFBWSxFQUFFLElBQUksRUFBRSxJQUFJLEVBQUMsK0NBQStDLEdBQUU7WUFDakksTUFBTSxFQUFFLElBQUksRUFBRSxPQUFPLElBQUkseUNBRXZCO1lBQ0gsb0JBQUMsYUFBYSxDQUFDLE1BQU0sSUFBQyxJQUFJLEVBQUMsa0JBQWtCLEVBQUMsS0FBSyxFQUFDLG1CQUFtQixFQUFDLFlBQVksRUFBQyxrQkFBa0I7Z0JBQ3RHLGdDQUFRLEtBQUssRUFBQyxrQkFBa0IsdUJBQTBCO2dCQUMxRCxnQ0FBUSxLQUFLLEVBQUMsc0JBQXNCLDJCQUE4QjtnQkFDbEUsZ0NBQVEsS0FBSyxFQUFDLHNCQUFzQiwyQkFBOEIsQ0FDNUMsQ0FDYixDQUNFLENBQ2QsQ0FBQztBQUNILENBQUMifQ==