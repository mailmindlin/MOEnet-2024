import React from 'react';
export default class StreamList extends React.Component {
    static pattern = new URLPattern({ pathname: '/stream' });
    static title = 'Streams';
    static base = '/stream';
    constructor(props) {
        super(props);
        this.state = {
            cancel: new AbortController(),
            streams: undefined,
            error: undefined,
        };
    }
    componentDidMount() {
        this.loadHeaders();
    }
    componentWillUnmount() {
        this.state.cancel.abort();
    }
    async loadHeaders() {
        try {
            let rsp = await fetch('/api/streams', {
                headers: { 'Content-Type': 'application/json' },
                signal: this.state.cancel.signal,
            });
            var json = await rsp.json();
        }
        catch (e) {
            console.error("Unable to load headers");
            this.setState({ error: `${e}` });
            return;
        }
        this.setState({ streams: json });
    }
    render() {
        if (this.state.error) {
            return React.createElement("div", { style: { color: 'red' } },
                "Error: ",
                this.state.error);
        }
        if (typeof this.state.streams === 'undefined')
            return React.createElement("div", null, "Loading...");
        const streamsByCamera = new Map();
        for (const stream of this.state.streams ?? []) {
            if (!streamsByCamera.has(stream.worker))
                streamsByCamera.set(stream.worker, []);
            streamsByCamera.get(stream.worker).push(stream.name);
        }
        return (React.createElement("ul", null, Array.from(streamsByCamera.entries()).map(([worker, streams]) => React.createElement("li", { key: worker },
            worker,
            React.createElement("ul", null, streams.map(stream => (React.createElement("li", { key: stream },
                React.createElement("a", { href: `#stream/${worker}/${stream}` }, stream)))))))));
    }
}
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiU3RyZWFtTGlzdC5qcyIsInNvdXJjZVJvb3QiOiIiLCJzb3VyY2VzIjpbIi4uLy4uL3RzL3JvdXRlL1N0cmVhbUxpc3QudHN4Il0sIm5hbWVzIjpbXSwibWFwcGluZ3MiOiJBQUFBLE9BQU8sS0FBSyxNQUFNLE9BQU8sQ0FBQztBQWExQixNQUFNLENBQUMsT0FBTyxPQUFPLFVBQVcsU0FBUSxLQUFLLENBQUMsU0FBdUI7SUFDakUsTUFBTSxDQUFVLE9BQU8sR0FBZSxJQUFJLFVBQVUsQ0FBQyxFQUFFLFFBQVEsRUFBRSxTQUFTLEVBQUUsQ0FBQyxDQUFDO0lBQzlFLE1BQU0sQ0FBVSxLQUFLLEdBQVcsU0FBUyxDQUFDO0lBQzFDLE1BQU0sQ0FBVSxJQUFJLEdBQVcsU0FBUyxDQUFDO0lBQ3pDLFlBQVksS0FBWTtRQUNwQixLQUFLLENBQUMsS0FBSyxDQUFDLENBQUM7UUFFYixJQUFJLENBQUMsS0FBSyxHQUFHO1lBQ1QsTUFBTSxFQUFFLElBQUksZUFBZSxFQUFFO1lBQzdCLE9BQU8sRUFBRSxTQUFTO1lBQ2xCLEtBQUssRUFBRSxTQUFTO1NBQ25CLENBQUM7SUFDTixDQUFDO0lBQ0QsaUJBQWlCO1FBQ2IsSUFBSSxDQUFDLFdBQVcsRUFBRSxDQUFDO0lBQ3ZCLENBQUM7SUFDRCxvQkFBb0I7UUFDaEIsSUFBSSxDQUFDLEtBQUssQ0FBQyxNQUFNLENBQUMsS0FBSyxFQUFFLENBQUM7SUFDOUIsQ0FBQztJQUVELEtBQUssQ0FBQyxXQUFXO1FBQ2IsSUFBSTtZQUNBLElBQUksR0FBRyxHQUFHLE1BQU0sS0FBSyxDQUFDLGNBQWMsRUFBRTtnQkFDbEMsT0FBTyxFQUFFLEVBQUUsY0FBYyxFQUFFLGtCQUFrQixFQUFFO2dCQUMvQyxNQUFNLEVBQUUsSUFBSSxDQUFDLEtBQUssQ0FBQyxNQUFNLENBQUMsTUFBTTthQUNuQyxDQUFDLENBQUM7WUFDSCxJQUFJLElBQUksR0FBRyxNQUFNLEdBQUcsQ0FBQyxJQUFJLEVBQUUsQ0FBQztTQUMvQjtRQUFDLE9BQU0sQ0FBQyxFQUFFO1lBQ1AsT0FBTyxDQUFDLEtBQUssQ0FBQyx3QkFBd0IsQ0FBQyxDQUFDO1lBQ3hDLElBQUksQ0FBQyxRQUFRLENBQUMsRUFBRSxLQUFLLEVBQUUsR0FBRyxDQUFDLEVBQUUsRUFBQyxDQUFDLENBQUM7WUFDaEMsT0FBTztTQUNWO1FBQ0QsSUFBSSxDQUFDLFFBQVEsQ0FBQyxFQUFDLE9BQU8sRUFBRSxJQUFJLEVBQUUsQ0FBQyxDQUFDO0lBQ3BDLENBQUM7SUFDRCxNQUFNO1FBQ0YsSUFBSSxJQUFJLENBQUMsS0FBSyxDQUFDLEtBQUssRUFBRTtZQUNsQixPQUFPLDZCQUFLLEtBQUssRUFBRSxFQUFDLEtBQUssRUFBRSxLQUFLLEVBQUM7O2dCQUFVLElBQUksQ0FBQyxLQUFLLENBQUMsS0FBSyxDQUFPLENBQUE7U0FDckU7UUFDRCxJQUFJLE9BQU8sSUFBSSxDQUFDLEtBQUssQ0FBQyxPQUFPLEtBQUssV0FBVztZQUN6QyxPQUFPLDhDQUFxQixDQUFDO1FBRWpDLE1BQU0sZUFBZSxHQUFHLElBQUksR0FBRyxFQUFvQixDQUFDO1FBQ3BELEtBQUssTUFBTSxNQUFNLElBQUksSUFBSSxDQUFDLEtBQUssQ0FBQyxPQUFPLElBQUksRUFBRSxFQUFFO1lBQzNDLElBQUksQ0FBQyxlQUFlLENBQUMsR0FBRyxDQUFDLE1BQU0sQ0FBQyxNQUFNLENBQUM7Z0JBQ25DLGVBQWUsQ0FBQyxHQUFHLENBQUMsTUFBTSxDQUFDLE1BQU0sRUFBRSxFQUFFLENBQUMsQ0FBQztZQUMzQyxlQUFlLENBQUMsR0FBRyxDQUFDLE1BQU0sQ0FBQyxNQUFNLENBQUUsQ0FBQyxJQUFJLENBQUMsTUFBTSxDQUFDLElBQUksQ0FBQyxDQUFDO1NBQ3pEO1FBRUQsT0FBTyxDQUNILGdDQUNLLEtBQUssQ0FBQyxJQUFJLENBQUMsZUFBZSxDQUFDLE9BQU8sRUFBRSxDQUFDLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxNQUFNLEVBQUUsT0FBTyxDQUFDLEVBQUUsRUFBRSxDQUM3RCw0QkFBSSxHQUFHLEVBQUUsTUFBTTtZQUNWLE1BQU07WUFDUCxnQ0FDSyxPQUFPLENBQUMsR0FBRyxDQUFDLE1BQU0sQ0FBQyxFQUFFLENBQUMsQ0FDbkIsNEJBQUksR0FBRyxFQUFFLE1BQU07Z0JBQ1gsMkJBQUcsSUFBSSxFQUFFLFdBQVcsTUFBTSxJQUFJLE1BQU0sRUFBRSxJQUFHLE1BQU0sQ0FBSyxDQUNuRCxDQUNSLENBQUMsQ0FDRCxDQUNKLENBQ1IsQ0FDQSxDQUNSLENBQUM7SUFDTixDQUFDIn0=