function invokeUpdateCallback(ccb, prev) {
    if (typeof ccb === 'function') {
        return ccb(prev);
    }
    else {
        return ccb;
    }
}
// export function boundReplaceKey<V extends object, K extends keyof V>(key: K, value: V, onChange: ReplaceCallback<V>): ReplaceCallback<V[K]>;
export function boundReplaceKey(key, value, onChange) {
    if (!onChange)
        return undefined;
    return (val) => {
        onChange({
            ...value,
            [key]: val,
        });
    };
}
export function boundUpdateKey(key, onChange, defaultInit) {
    if (!onChange)
        return undefined;
    function boundUpdateKeyInner(ccb) {
        // console.log('ubk1', ccb, onChange, key);
        onChange(v => {
            // console.log('boundUpdateKey', v, ccb);
            const res = {
                ...v,
                [key]: invokeUpdateCallback(ccb, v[key] === undefined ? defaultInit ?? v[key] : v[key]),
            };
            // console.log('res', res);
            return res;
        });
    }
    return boundUpdateKeyInner;
}
export function boundUpdateIdx(key, onChange) {
    if (!onChange)
        return undefined;
    return (ccb) => onChange(v => [
        ...(v ?? []).splice(0, key),
        invokeUpdateCallback(ccb, v?.[key]),
        ...(v ?? []).splice(key + 1),
    ]);
}
window.boundUpdateKey = boundUpdateKey;
window.boundUpdateIdx = boundUpdateIdx;
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiZHMuanMiLCJzb3VyY2VSb290IjoiIiwic291cmNlcyI6WyIuLi8uLi8uLi90cy9yb3V0ZS9Db25maWdCdWlsZGVyL2RzLnRzIl0sIm5hbWVzIjpbXSwibWFwcGluZ3MiOiJBQUlBLFNBQVMsb0JBQW9CLENBQWlCLEdBQTBCLEVBQUUsSUFBTztJQUNoRixJQUFJLE9BQU8sR0FBRyxLQUFLLFVBQVUsRUFBRSxDQUFDO1FBQy9CLE9BQVEsR0FBdUIsQ0FBQyxJQUFJLENBQUMsQ0FBQztJQUN2QyxDQUFDO1NBQU0sQ0FBQztRQUNQLE9BQVEsR0FBUyxDQUFDO0lBQ25CLENBQUM7QUFDRixDQUFDO0FBRUQsK0lBQStJO0FBQy9JLE1BQU0sVUFBVSxlQUFlLENBQXNDLEdBQU0sRUFBRSxLQUFRLEVBQUUsUUFBNkI7SUFDbkgsSUFBSSxDQUFDLFFBQVE7UUFDWixPQUFPLFNBQVMsQ0FBQztJQUVsQixPQUFPLENBQUMsR0FBUyxFQUFFLEVBQUU7UUFDcEIsUUFBUSxDQUFDO1lBQ1IsR0FBRyxLQUFLO1lBQ1IsQ0FBQyxHQUFHLENBQUMsRUFBRSxHQUFHO1NBQ1YsQ0FBQyxDQUFBO0lBQ0gsQ0FBQyxDQUFBO0FBQ0YsQ0FBQztBQUdELE1BQU0sVUFBVSxjQUFjLENBQXNDLEdBQU0sRUFBRSxRQUE0QixFQUFFLFdBQWtCO0lBQzNILElBQUksQ0FBQyxRQUFRO1FBQ1osT0FBTyxTQUFTLENBQUM7SUFDbEIsU0FBUyxtQkFBbUIsQ0FBQyxHQUFtQztRQUMvRCwyQ0FBMkM7UUFDM0MsUUFBUyxDQUFDLENBQUMsQ0FBQyxFQUFFO1lBQ2IseUNBQXlDO1lBQ3pDLE1BQU0sR0FBRyxHQUFHO2dCQUNYLEdBQUcsQ0FBQztnQkFDSixDQUFDLEdBQUcsQ0FBQyxFQUFFLG9CQUFvQixDQUFDLEdBQUcsRUFBRSxDQUFDLENBQUMsR0FBRyxDQUFDLEtBQUssU0FBUyxDQUFDLENBQUMsQ0FBQyxXQUFXLElBQUksQ0FBQyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsQ0FBQyxDQUFDLENBQUMsR0FBRyxDQUFDLENBQUM7YUFDdkYsQ0FBQztZQUNGLDJCQUEyQjtZQUMzQixPQUFPLEdBQUcsQ0FBQztRQUNaLENBQUMsQ0FBQyxDQUFBO0lBQ0gsQ0FBQztJQUNELE9BQU8sbUJBQW1CLENBQUM7QUFDNUIsQ0FBQztBQVFELE1BQU0sVUFBVSxjQUFjLENBQUksR0FBVyxFQUFFLFFBQWtDO0lBQ2hGLElBQUksQ0FBQyxRQUFRO1FBQ1osT0FBTyxTQUFTLENBQUM7SUFDbEIsT0FBTyxDQUFDLEdBQUcsRUFBRSxFQUFFLENBQUMsUUFBUSxDQUFDLENBQUMsQ0FBQyxFQUFFLENBQUM7UUFDN0IsR0FBRyxDQUFDLENBQUMsSUFBSSxFQUFFLENBQUMsQ0FBQyxNQUFNLENBQUMsQ0FBQyxFQUFFLEdBQUcsQ0FBQztRQUMzQixvQkFBb0IsQ0FBQyxHQUFHLEVBQUUsQ0FBQyxFQUFFLENBQUMsR0FBRyxDQUFDLENBQUM7UUFDbkMsR0FBRyxDQUFDLENBQUMsSUFBSSxFQUFFLENBQUMsQ0FBQyxNQUFNLENBQUMsR0FBRyxHQUFHLENBQUMsQ0FBQztLQUM1QixDQUFDLENBQUM7QUFDSixDQUFDO0FBRUEsTUFBYyxDQUFDLGNBQWMsR0FBRyxjQUFjLENBQUM7QUFDL0MsTUFBYyxDQUFDLGNBQWMsR0FBRyxjQUFjLENBQUMifQ==