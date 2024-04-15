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
        // Coallate streams by camera name
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
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiU3RyZWFtTGlzdC5qcyIsInNvdXJjZVJvb3QiOiIiLCJzb3VyY2VzIjpbIi4uLy4uL3RzL3JvdXRlL1N0cmVhbUxpc3QudHN4Il0sIm5hbWVzIjpbXSwibWFwcGluZ3MiOiJBQUFBLE9BQU8sS0FBSyxNQUFNLE9BQU8sQ0FBQztBQUUxQixPQUFPLFFBQVEsTUFBTSx3QkFBd0IsQ0FBQztBQUM5QyxPQUFPLE9BQU8sTUFBTSx1QkFBdUIsQ0FBQztBQVc1QyxNQUFNLENBQUMsT0FBTyxPQUFPLFVBQVcsU0FBUSxLQUFLLENBQUMsU0FBdUI7SUFDakUsTUFBTSxDQUFVLE9BQU8sR0FBZSxJQUFJLFVBQVUsQ0FBQyxFQUFFLFFBQVEsRUFBRSxTQUFTLEVBQUUsQ0FBQyxDQUFDO0lBQzlFLE1BQU0sQ0FBVSxLQUFLLEdBQVcsU0FBUyxDQUFDO0lBQzFDLE1BQU0sQ0FBVSxJQUFJLEdBQVcsU0FBUyxDQUFDO0lBQ3pDLFlBQVksS0FBWTtRQUNwQixLQUFLLENBQUMsS0FBSyxDQUFDLENBQUM7UUFFYixJQUFJLENBQUMsS0FBSyxHQUFHO1lBQ1QsTUFBTSxFQUFFLElBQUksZUFBZSxFQUFFO1lBQzdCLE9BQU8sRUFBRSxTQUFTO1lBQ2xCLEtBQUssRUFBRSxJQUFJO1NBQ2QsQ0FBQztJQUNOLENBQUM7SUFDUSxpQkFBaUI7UUFDdEIsSUFBSSxDQUFDLFdBQVcsRUFBRSxDQUFDO0lBQ3ZCLENBQUM7SUFDUSxvQkFBb0I7UUFDekIsSUFBSSxDQUFDLEtBQUssQ0FBQyxNQUFNLENBQUMsS0FBSyxFQUFFLENBQUM7SUFDOUIsQ0FBQztJQUVPLEtBQUssQ0FBQyxXQUFXO1FBQ3JCLElBQUksQ0FBQztZQUNELElBQUksR0FBRyxHQUFHLE1BQU0sS0FBSyxDQUFDLGNBQWMsRUFBRTtnQkFDbEMsT0FBTyxFQUFFLEVBQUUsY0FBYyxFQUFFLGtCQUFrQixFQUFFO2dCQUMvQyxNQUFNLEVBQUUsSUFBSSxDQUFDLEtBQUssQ0FBQyxNQUFNLENBQUMsTUFBTTthQUNuQyxDQUFDLENBQUM7UUFDUCxDQUFDO1FBQUMsT0FBTyxDQUFDLEVBQUUsQ0FBQztZQUNULElBQUksQ0FBQyxZQUFZLFlBQVksSUFBSSxDQUFDLENBQUMsSUFBSSxJQUFJLFlBQVksRUFBRSxDQUFDO2dCQUN0RCxJQUFJLENBQUMsUUFBUSxDQUFDLEVBQUUsS0FBSyxFQUFFLFNBQVMsRUFBRSxDQUFDLENBQUM7WUFDeEMsQ0FBQztpQkFBTSxDQUFDO2dCQUNKLElBQUksQ0FBQyxRQUFRLENBQUMsRUFBRSxLQUFLLEVBQUUsR0FBRyxDQUFDLEVBQUUsRUFBRSxDQUFDLENBQUM7WUFDckMsQ0FBQztZQUNELE9BQU87UUFDWCxDQUFDO1FBQ0QsSUFBSSxDQUFDLEdBQUcsQ0FBQyxFQUFFLEVBQUUsQ0FBQztZQUNWLElBQUksS0FBSyxHQUFHLCtCQUErQixHQUFHLENBQUMsTUFBTSxJQUFJLEdBQUcsQ0FBQyxVQUFVLEVBQUUsQ0FBQztZQUMxRSxJQUFJLENBQUM7Z0JBQ0QsS0FBSyxJQUFJLEdBQUcsR0FBRyxNQUFNLEdBQUcsQ0FBQyxJQUFJLEVBQUUsQ0FBQztZQUNwQyxDQUFDO1lBQUMsTUFBTSxDQUFDLENBQUEsQ0FBQztZQUNWLElBQUksQ0FBQyxRQUFRLENBQUMsRUFBRSxLQUFLLEVBQUUsQ0FBQyxDQUFDO1lBQ3pCLE9BQU87UUFDWCxDQUFDO1FBQ0QsT0FBTyxDQUFDLEdBQUcsQ0FBQyxHQUFHLENBQUMsQ0FBQztRQUNqQixJQUFJLENBQUM7WUFDRCxJQUFJLElBQUksR0FBRyxNQUFNLEdBQUcsQ0FBQyxJQUFJLEVBQUUsQ0FBQztRQUNoQyxDQUFDO1FBQUMsT0FBTSxDQUFDLEVBQUUsQ0FBQztZQUNSLE9BQU8sQ0FBQyxLQUFLLENBQUMsb0JBQW9CLENBQUMsQ0FBQztZQUNwQyxJQUFJLENBQUMsUUFBUSxDQUFDLEVBQUUsS0FBSyxFQUFFLDhCQUE4QixFQUFDLENBQUMsQ0FBQztZQUN4RCxPQUFPO1FBQ1gsQ0FBQztRQUNELElBQUksQ0FBQyxRQUFRLENBQUMsRUFBRSxLQUFLLEVBQUUsSUFBSSxFQUFFLE9BQU8sRUFBRSxJQUFJLEVBQUUsQ0FBQyxDQUFDO0lBQ2xELENBQUM7SUFDUSxNQUFNO1FBQ1gsSUFBSSxJQUFJLENBQUMsS0FBSyxDQUFDLEtBQUs7WUFDaEIsT0FBTyxvQkFBQyxRQUFRLFFBQUUsSUFBSSxDQUFDLEtBQUssQ0FBQyxLQUFLLENBQVksQ0FBQzthQUM5QyxJQUFJLE9BQU8sSUFBSSxDQUFDLEtBQUssQ0FBQyxPQUFPLEtBQUssV0FBVztZQUM5QyxPQUFPLG9CQUFDLE9BQU8sT0FBRyxDQUFDO1FBRXZCLGtDQUFrQztRQUNsQyxNQUFNLGVBQWUsR0FBRyxJQUFJLEdBQUcsRUFBb0IsQ0FBQztRQUNwRCxLQUFLLE1BQU0sTUFBTSxJQUFJLElBQUksQ0FBQyxLQUFLLENBQUMsT0FBTyxJQUFJLEVBQUUsRUFBRSxDQUFDO1lBQzVDLElBQUksQ0FBQyxlQUFlLENBQUMsR0FBRyxDQUFDLE1BQU0sQ0FBQyxNQUFNLENBQUM7Z0JBQ25DLGVBQWUsQ0FBQyxHQUFHLENBQUMsTUFBTSxDQUFDLE1BQU0sRUFBRSxFQUFFLENBQUMsQ0FBQztZQUMzQyxlQUFlLENBQUMsR0FBRyxDQUFDLE1BQU0sQ0FBQyxNQUFNLENBQUUsQ0FBQyxJQUFJLENBQUMsTUFBTSxDQUFDLElBQUksQ0FBQyxDQUFDO1FBQzFELENBQUM7UUFFRCxPQUFPLENBQ0gsZ0NBQ0ssS0FBSyxDQUFDLElBQUksQ0FBQyxlQUFlLENBQUMsT0FBTyxFQUFFLENBQUMsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLE1BQU0sRUFBRSxPQUFPLENBQUMsRUFBRSxFQUFFLENBQzdELDRCQUFJLEdBQUcsRUFBRSxNQUFNO1lBQ1YsTUFBTTtZQUNQLGdDQUNLLE9BQU8sQ0FBQyxHQUFHLENBQUMsTUFBTSxDQUFDLEVBQUUsQ0FBQyxDQUNuQiw0QkFBSSxHQUFHLEVBQUUsTUFBTTtnQkFDWCwyQkFBRyxJQUFJLEVBQUUsV0FBVyxNQUFNLElBQUksTUFBTSxFQUFFLElBQUcsTUFBTSxDQUFLLENBQ25ELENBQ1IsQ0FBQyxDQUNELENBQ0osQ0FDUixDQUNBLENBQ1IsQ0FBQztJQUNOLENBQUMifQ==