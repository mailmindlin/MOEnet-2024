import React from 'react';
function getSchema(schema, path) {
    const defs = schema['$defs'] ?? {};
    const current = schema;
    for (const section of path) {
        if (current['title'])
            if (current['type'] == 'object') {
            }
    }
    return schema;
}
export default function JsonEditor({ schema, value, path = [] }) {
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
}
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiSnNvbkVkaXRvci5qcyIsInNvdXJjZVJvb3QiOiIiLCJzb3VyY2VzIjpbIi4uLy4uL3RzL2NvbXBvbmVudHMvSnNvbkVkaXRvci50c3giXSwibmFtZXMiOltdLCJtYXBwaW5ncyI6IkFBQUEsT0FBTyxLQUFLLE1BQU0sT0FBTyxDQUFDO0FBMkIxQixTQUFTLFNBQVMsQ0FBQyxNQUFXLEVBQUUsSUFBYztJQUMxQyxNQUFNLElBQUksR0FBRyxNQUFNLENBQUMsT0FBTyxDQUFDLElBQUksRUFBRSxDQUFDO0lBQ25DLE1BQU0sT0FBTyxHQUFHLE1BQU0sQ0FBQztJQUN2QixLQUFLLE1BQU0sT0FBTyxJQUFJLElBQUksRUFBRSxDQUFDO1FBQ3pCLElBQUksT0FBTyxDQUFDLE9BQU8sQ0FBQztZQUNwQixJQUFJLE9BQU8sQ0FBQyxNQUFNLENBQUMsSUFBSSxRQUFRLEVBQUUsQ0FBQztZQUNsQyxDQUFDO0lBQ0wsQ0FBQztJQUNELE9BQU8sTUFBTSxDQUFDO0FBQ2xCLENBQUM7QUFFRCxNQUFNLENBQUMsT0FBTyxVQUFVLFVBQVUsQ0FBQyxFQUFFLE1BQU0sRUFBRSxLQUFLLEVBQUUsSUFBSSxHQUFHLEVBQUUsRUFBbUI7SUFDNUUsTUFBTSxHQUFHLEdBQUcsS0FBSyxDQUFDLE9BQU8sQ0FBQyxHQUFHLEVBQUUsQ0FBQyxTQUFTLENBQUMsTUFBTSxFQUFFLElBQUksQ0FBQyxFQUFFLENBQUMsTUFBTSxFQUFFLElBQUksQ0FBQyxDQUFDLENBQUM7SUFDekUsTUFBTSxFQUFFLEdBQUcsS0FBSyxDQUFDLEtBQUssRUFBRSxDQUFDO0lBRXpCLElBQUksQ0FBQyxHQUFHLEVBQUUsQ0FBQztRQUNQLE9BQU87O1lBQW9CLElBQUksQ0FBUSxDQUFDO0lBQzVDLENBQUM7SUFFRCxRQUFRLEdBQUcsQ0FBQyxJQUFJLEVBQUUsQ0FBQztRQUNmLEtBQUssUUFBUSxDQUFDLENBQUMsQ0FBQztZQUNaLE9BQU8sQ0FDSDtnQkFDSyxHQUFHLENBQUMsS0FBSyxJQUFJLG9DQUFTLEdBQUcsQ0FBQyxLQUFLLENBQVU7Z0JBQ3pDLEdBQUcsQ0FBQyxVQUFVLENBQUMsR0FBRyxDQUFDLElBQUksQ0FBQyxFQUFFLENBQUMsQ0FDeEI7O29CQUFnQixJQUFJLENBQUMsU0FBUyxDQUFDLElBQUksQ0FBQyxDQUFRLENBQy9DLENBQUMsQ0FDSyxDQUNkLENBQUE7WUFDRCxNQUFNO1FBQ1YsQ0FBQztRQUNELEtBQUssUUFBUSxDQUFDLENBQUMsQ0FBQztZQUNaLElBQUksR0FBRyxDQUFDLElBQUksRUFBRSxDQUFDO2dCQUNYLE9BQU8sQ0FBQztvQkFDSiwrQkFBTyxPQUFPLEVBQUUsRUFBRSxJQUFHLEdBQUcsQ0FBQyxLQUFLLElBQUksSUFBSSxDQUFDLFFBQVEsQ0FBQyxHQUFHLEVBQUUsQ0FBQyxJQUFJLENBQUMsQ0FBUztvQkFDcEUsZ0NBQVEsRUFBRSxFQUFFLEVBQUUsSUFDVCxHQUFHLENBQUMsSUFBSSxDQUFDLEdBQUcsQ0FBQyxJQUFJLENBQUMsRUFBRSxDQUFDLENBQ2xCLGdDQUFRLEtBQUssRUFBRSxJQUFJLElBQUcsSUFBSSxDQUFVLENBQ3ZDLENBQUMsQ0FDRyxDQUNWLENBQUMsQ0FBQztZQUNULENBQUM7UUFDTCxDQUFDO0lBQ0wsQ0FBQztBQUNMLENBQUMifQ==