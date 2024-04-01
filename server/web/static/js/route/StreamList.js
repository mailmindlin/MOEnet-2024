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
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiU3RyZWFtTGlzdC5qcyIsInNvdXJjZVJvb3QiOiIiLCJzb3VyY2VzIjpbIi4uLy4uL3RzL3JvdXRlL1N0cmVhbUxpc3QudHN4Il0sIm5hbWVzIjpbXSwibWFwcGluZ3MiOiJBQUFBLE9BQU8sS0FBSyxNQUFNLE9BQU8sQ0FBQztBQUcxQixPQUFPLFFBQVEsTUFBTSx3QkFBd0IsQ0FBQztBQUM5QyxPQUFPLE9BQU8sTUFBTSx1QkFBdUIsQ0FBQztBQVc1QyxNQUFNLENBQUMsT0FBTyxPQUFPLFVBQVcsU0FBUSxLQUFLLENBQUMsU0FBdUI7SUFDakUsTUFBTSxDQUFVLE9BQU8sR0FBZSxJQUFJLFVBQVUsQ0FBQyxFQUFFLFFBQVEsRUFBRSxTQUFTLEVBQUUsQ0FBQyxDQUFDO0lBQzlFLE1BQU0sQ0FBVSxLQUFLLEdBQVcsU0FBUyxDQUFDO0lBQzFDLE1BQU0sQ0FBVSxJQUFJLEdBQVcsU0FBUyxDQUFDO0lBQ3pDLFlBQVksS0FBWTtRQUNwQixLQUFLLENBQUMsS0FBSyxDQUFDLENBQUM7UUFFYixJQUFJLENBQUMsS0FBSyxHQUFHO1lBQ1QsTUFBTSxFQUFFLElBQUksZUFBZSxFQUFFO1lBQzdCLE9BQU8sRUFBRSxTQUFTO1lBQ2xCLEtBQUssRUFBRSxJQUFJO1NBQ2QsQ0FBQztJQUNOLENBQUM7SUFDRCxpQkFBaUI7UUFDYixJQUFJLENBQUMsV0FBVyxFQUFFLENBQUM7SUFDdkIsQ0FBQztJQUNELG9CQUFvQjtRQUNoQixJQUFJLENBQUMsS0FBSyxDQUFDLE1BQU0sQ0FBQyxLQUFLLEVBQUUsQ0FBQztJQUM5QixDQUFDO0lBRUQsS0FBSyxDQUFDLFdBQVc7UUFDYixJQUFJLENBQUM7WUFDRCxJQUFJLEdBQUcsR0FBRyxNQUFNLEtBQUssQ0FBQyxjQUFjLEVBQUU7Z0JBQ2xDLE9BQU8sRUFBRSxFQUFFLGNBQWMsRUFBRSxrQkFBa0IsRUFBRTtnQkFDL0MsTUFBTSxFQUFFLElBQUksQ0FBQyxLQUFLLENBQUMsTUFBTSxDQUFDLE1BQU07YUFDbkMsQ0FBQyxDQUFDO1FB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