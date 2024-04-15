import React from 'react';
function getSchema(schema, path) {
    // const defs = schema['$defs'] ?? {};
    const current = schema;
    for (const _section of path) {
        if (current['title'])
            if (current['type'] == 'object') {
            }
    }
    return schema;
}
export default function JsonEditor({ schema, path = [] }) {
    const res = React.useMemo(() => getSchema(schema, path), [schema, path]);
    const id = React.useId();
    if (!res) {
        return React.createElement("span", null,
            "Unknown path ",
            path);
    }
    switch (res.type) {
        case 'object': {
            return (React.createElement("fieldset", null,
                res.title && React.createElement("legend", null, res.title),
                res.properties.map(prop => (React.createElement("span", null,
                    "Property ",
                    JSON.stringify(prop))))));
            break;
        }
        case 'string': {
            if (res.enum) {
                return (React.createElement(React.Fragment, null,
                    React.createElement("label", { htmlFor: id }, res.title ?? path.findLast(() => true)),
                    React.createElement("select", { id: id }, res.enum.map(item => (React.createElement("option", { value: item }, item))))));
            }
        }
    }
    throw new RangeError(`Unknown type: ${res.type}`);
}
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiSnNvbkVkaXRvci5qcyIsInNvdXJjZVJvb3QiOiIiLCJzb3VyY2VzIjpbIi4uLy4uL3RzL2NvbXBvbmVudHMvSnNvbkVkaXRvci50c3giXSwibmFtZXMiOltdLCJtYXBwaW5ncyI6IkFBQUEsT0FBTyxLQUFLLE1BQU0sT0FBTyxDQUFDO0FBMkIxQixTQUFTLFNBQVMsQ0FBQyxNQUFXLEVBQUUsSUFBYztJQUMxQyxzQ0FBc0M7SUFDdEMsTUFBTSxPQUFPLEdBQUcsTUFBTSxDQUFDO0lBQ3ZCLEtBQUssTUFBTSxRQUFRLElBQUksSUFBSSxFQUFFLENBQUM7UUFDMUIsSUFBSSxPQUFPLENBQUMsT0FBTyxDQUFDO1lBQ3BCLElBQUksT0FBTyxDQUFDLE1BQU0sQ0FBQyxJQUFJLFFBQVEsRUFBRSxDQUFDO1lBQ2xDLENBQUM7SUFDTCxDQUFDO0lBQ0QsT0FBTyxNQUFNLENBQUM7QUFDbEIsQ0FBQztBQUVELE1BQU0sQ0FBQyxPQUFPLFVBQVUsVUFBVSxDQUFDLEVBQUUsTUFBTSxFQUFFLElBQUksR0FBRyxFQUFFLEVBQW1CO0lBQ3JFLE1BQU0sR0FBRyxHQUFHLEtBQUssQ0FBQyxPQUFPLENBQUMsR0FBRyxFQUFFLENBQUMsU0FBUyxDQUFDLE1BQU0sRUFBRSxJQUFJLENBQUMsRUFBRSxDQUFDLE1BQU0sRUFBRSxJQUFJLENBQUMsQ0FBQyxDQUFDO0lBQ3pFLE1BQU0sRUFBRSxHQUFHLEtBQUssQ0FBQyxLQUFLLEVBQUUsQ0FBQztJQUV6QixJQUFJLENBQUMsR0FBRyxFQUFFLENBQUM7UUFDUCxPQUFPOztZQUFvQixJQUFJLENBQVEsQ0FBQztJQUM1QyxDQUFDO0lBRUQsUUFBUSxHQUFHLENBQUMsSUFBSSxFQUFFLENBQUM7UUFDZixLQUFLLFFBQVEsQ0FBQyxDQUFDLENBQUM7WUFDWixPQUFPLENBQ0g7Z0JBQ0ssR0FBRyxDQUFDLEtBQUssSUFBSSxvQ0FBUyxHQUFHLENBQUMsS0FBSyxDQUFVO2dCQUN6QyxHQUFHLENBQUMsVUFBVSxDQUFDLEdBQUcsQ0FBQyxJQUFJLENBQUMsRUFBRSxDQUFDLENBQ3hCOztvQkFBZ0IsSUFBSSxDQUFDLFNBQVMsQ0FBQyxJQUFJLENBQUMsQ0FBUSxDQUMvQyxDQUFDLENBQ0ssQ0FDZCxDQUFBO1lBQ0QsTUFBTTtRQUNWLENBQUM7UUFDRCxLQUFLLFFBQVEsQ0FBQyxDQUFDLENBQUM7WUFDWixJQUFJLEdBQUcsQ0FBQyxJQUFJLEVBQUUsQ0FBQztnQkFDWCxPQUFPLENBQUM7b0JBQ0osK0JBQU8sT0FBTyxFQUFFLEVBQUUsSUFBRyxHQUFHLENBQUMsS0FBSyxJQUFJLElBQUksQ0FBQyxRQUFRLENBQUMsR0FBRyxFQUFFLENBQUMsSUFBSSxDQUFDLENBQVM7b0JBQ3BFLGdDQUFRLEVBQUUsRUFBRSxFQUFFLElBQ1QsR0FBRyxDQUFDLElBQUksQ0FBQyxHQUFHLENBQUMsSUFBSSxDQUFDLEVBQUUsQ0FBQyxDQUNsQixnQ0FBUSxLQUFLLEVBQUUsSUFBSSxJQUFHLElBQUksQ0FBVSxDQUN2QyxDQUFDLENBQ0csQ0FDVixDQUFDLENBQUM7WUFDVCxDQUFDO1FBQ0wsQ0FBQztJQUNMLENBQUM7SUFDRCxNQUFNLElBQUksVUFBVSxDQUFDLGlCQUFpQixHQUFHLENBQUMsSUFBSSxFQUFFLENBQUMsQ0FBQztBQUN0RCxDQUFDIn0=