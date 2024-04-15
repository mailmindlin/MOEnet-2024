
export interface JsonSchemaRoot {
	"$refs": any
}

interface JsonSchemaString {
	title?: string;
	description?: string;
	default?: string;
	enum?: string[];
}

interface JsonSchemaObject<T> {
	"type": "object";
	value: T;
}

interface JsonSchemaRef<T> {
	"$ref": string;
	value: T;
}

export type JsonSchemaLike<T> =
	JsonSchemaRef<T> | 
	T extends string ? JsonSchemaString :
	T extends object ? JsonSchemaObject<T> :
	never;