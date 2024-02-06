import React from 'react';
import ErrorMsg from '../components/ErrorMsg';
import Loading from '../components/Loading';
export default class StreamList extends React.Component {
    static pattern = new URLPattern({ pathname: '/stream' });
    static title = 'Streams';
    static base = '/stream';
    constructor(props) {
        super(props);
        this.state = {
            cancel: new AbortController(),
            streams: undefined,
            error: null,
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
            var rsp = await fetch('/api/streams', {
                headers: { 'Content-Type': 'application/json' },
                signal: this.state.cancel.signal,
            });
        }
        catch (e) {
            if (e instanceof DOMException && e.name == 'AbortError') {
                this.setState({ error: 'Aborted' });
            }
            else {
                this.setState({ error: `${e}` });
            }
            return;
        }
        if (!rsp.ok) {
            let error = `Error listing streams: HTTP ${rsp.status} ${rsp.statusText}`;
            try {
                error += " " + await rsp.text();
            }
            catch { }
            this.setState({ error });
            return;
        }
        console.log(rsp);
        try {
            var json = await rsp.json();
        }
        catch (e) {
            console.error("Unable to get json");
            this.setState({ error: `Unable to parse API response` });
            return;
        }
        this.setState({ error: null, streams: json });
    }
    render() {
        if (this.state.error)
            return React.createElement(ErrorMsg, null, this.state.error);
        else if (typeof this.state.streams === 'undefined')
            return React.createElement(Loading, null);
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
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiU3RyZWFtTGlzdC5qcyIsInNvdXJjZVJvb3QiOiIiLCJzb3VyY2VzIjpbIi4uLy4uL3RzL3JvdXRlL1N0cmVhbUxpc3QudHN4Il0sIm5hbWVzIjpbXSwibWFwcGluZ3MiOiJBQUFBLE9BQU8sS0FBSyxNQUFNLE9BQU8sQ0FBQztBQUcxQixPQUFPLFFBQVEsTUFBTSx3QkFBd0IsQ0FBQztBQUM5QyxPQUFPLE9BQU8sTUFBTSx1QkFBdUIsQ0FBQztBQVc1QyxNQUFNLENBQUMsT0FBTyxPQUFPLFVBQVcsU0FBUSxLQUFLLENBQUMsU0FBdUI7SUFDakUsTUFBTSxDQUFVLE9BQU8sR0FBZSxJQUFJLFVBQVUsQ0FBQyxFQUFFLFFBQVEsRUFBRSxTQUFTLEVBQUUsQ0FBQyxDQUFDO0lBQzlFLE1BQU0sQ0FBVSxLQUFLLEdBQVcsU0FBUyxDQUFDO0lBQzFDLE1BQU0sQ0FBVSxJQUFJLEdBQVcsU0FBUyxDQUFDO0lBQ3pDLFlBQVksS0FBWTtRQUNwQixLQUFLLENBQUMsS0FBSyxDQUFDLENBQUM7UUFFYixJQUFJLENBQUMsS0FBSyxHQUFHO1lBQ1QsTUFBTSxFQUFFLElBQUksZUFBZSxFQUFFO1lBQzdCLE9BQU8sRUFBRSxTQUFTO1lBQ2xCLEtBQUssRUFBRSxJQUFJO1NBQ2QsQ0FBQztJQUNOLENBQUM7SUFDRCxpQkFBaUI7UUFDYixJQUFJLENBQUMsV0FBVyxFQUFFLENBQUM7SUFDdkIsQ0FBQztJQUNELG9CQUFvQjtRQUNoQixJQUFJLENBQUMsS0FBSyxDQUFDLE1BQU0sQ0FBQyxLQUFLLEVBQUUsQ0FBQztJQUM5QixDQUFDO0lBRUQsS0FBSyxDQUFDLFdBQVc7UUFDYixJQUFJO1lBQ0EsSUFBSSxHQUFHLEdBQUcsTUFBTSxLQUFLLENBQUMsY0FBYyxFQUFFO2dCQUNsQyxPQUFPLEVBQUUsRUFBRSxjQUFjLEVBQUUsa0JBQWtCLEVBQUU7Z0JBQy9DLE1BQU0sRUFBRSxJQUFJLENBQUMsS0FBSyxDQUFDLE1BQU0sQ0FBQyxNQUFNO2FBQ25DLENBQUMsQ0FBQztTQUNOO1FB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