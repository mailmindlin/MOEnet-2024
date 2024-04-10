type ReplaceCallback<T> = (value: T) => void;
type UpdateCallback<T> = (cb: T | ((value: T) => T)) => void;
type UpdateCallbackLite<T> = (cb: T | ((value: T | undefined) => T)) => void;

function invokeUpdateCallback<K, T extends K>(ccb: T | ((value: K) => T), prev: K): T {
	if (typeof ccb === 'function') {
		return (ccb as (value: K) => T)(prev);
	} else {
		return (ccb as T);
	}
}

// export function boundReplaceKey<V extends object, K extends keyof V>(key: K, value: V, onChange: ReplaceCallback<V>): ReplaceCallback<V[K]>;
export function boundReplaceKey<V extends object, K extends keyof V>(key: K, value: V, onChange?: ReplaceCallback<V>): ReplaceCallback<V[K]> | undefined {
	if (!onChange)
		return undefined;

	return (val: V[K]) => {
		onChange({
			...value,
			[key]: val,
		})
	}
}
export function boundUpdateKey<V extends object, K extends keyof V>(key: K, onChange: UpdateCallback<V>): UpdateCallback<V[K]>;
export function boundUpdateKey<V extends object, K extends keyof V>(key: K, onChange: UpdateCallbackLite<V>, defaultInit: V[K]): UpdateCallback<Exclude<V[K], undefined | null>>;
export function boundUpdateKey<V extends object, K extends keyof V>(key: K, onChange?: UpdateCallback<V>, defaultInit?: V[K]): UpdateCallback<V[K]> | undefined {
	if (!onChange)
		return undefined;
	function boundUpdateKeyInner(ccb: V[K] | ((value: V[K]) => V[K])) {
		// console.log('ubk1', ccb, onChange, key);
		onChange!(v => {
			// console.log('boundUpdateKey', v, ccb);
			const res = {
				...v,
				[key]: invokeUpdateCallback(ccb, v[key] === undefined ? defaultInit ?? v[key] : v[key]),
			};
			// console.log('res', res);
			return res;
		})
	}
	return boundUpdateKeyInner;
}

// export function boundInsertItem<V>(onChange: UpdateCallback<V[]>): (item: V) => void {

// }

export function boundUpdateIdx<V>(key: number, onChange: UpdateCallback<V[]>): UpdateCallback<V>;
export function boundUpdateIdx<V>(key: number, onChange: UpdateCallbackLite<V[]>): UpdateCallbackLite<V>;
export function boundUpdateIdx<V>(key: number, onChange?: UpdateCallbackLite<V[]>): UpdateCallbackLite<V> | undefined {
	if (!onChange)
		return undefined;
	return (ccb) => onChange(v => [
		...(v ?? []).splice(0, key),
		invokeUpdateCallback(ccb, v?.[key]),
		...(v ?? []).splice(key + 1),
	]);
}

(window as any).boundUpdateKey = boundUpdateKey;
(window as any).boundUpdateIdx = boundUpdateIdx;