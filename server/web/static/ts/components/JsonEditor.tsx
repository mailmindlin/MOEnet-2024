import React from 'react';

interface JsonSchemaProps {
    schema: object;
    value: object;
    path: Array<string>;
}

interface BaseSchema {
    title?: string;
    description?: string;
}
interface ObjectSchema extends BaseSchema {
    type: 'object';
    properties: Array<{

    }>;
    required?: string[];
}
interface StringSchema extends BaseSchema {
    type: 'string';
    enum?: string[];
    default?: string;
}

type ResolvedSchema = ObjectSchema | StringSchema;

function getSchema(schema: any, path: string[]): ResolvedSchema | undefined {
    // const defs = schema['$defs'] ?? {};
    const current = schema;
    for (const _section of path) {
        if (current['title'])
        if (current['type'] == 'object') {
        }
    }
    return schema;
}

export default function JsonEditor({ schema, path = [] }: JsonSchemaProps) {
    const res = React.useMemo(() => getSchema(schema, path), [schema, path]);
    const id = React.useId();

    if (!res) {
        return <span>Unknown path {path}</span>;
    }

    switch (res.type) {
        case 'object': {
            return (
                <fieldset>
                    {res.title && <legend>{res.title}</legend>}
                    {res.properties.map(prop => (
                        <span>Property {JSON.stringify(prop)}</span>
                    ))}
                </fieldset>
            )
            break;
        }
        case 'string': {
            if (res.enum) {
                return (<>
                    <label htmlFor={id}>{res.title ?? path.findLast(() => true)}</label>
                    <select id={id}>
                        {res.enum.map(item => (
                            <option value={item}>{item}</option>
                        ))}
                    </select>
                </>);
            }
        }
    }
    throw new RangeError(`Unknown type: ${res.type}`);
}