import React from 'react';
import { RouteProps } from '../routing';
import ErrorMsg from '../components/ErrorMsg';
import Loading from '../components/Loading';
interface Props extends RouteProps {

}

interface State {
    cancel: AbortController;
    streams?: Array<{name: string, worker: string}>;
    error: string | null;
}

export default class StreamList extends React.Component<Props, State> {
    static readonly pattern: URLPattern = new URLPattern({ pathname: '/stream' });
    static readonly title: string = 'Streams';
    static readonly base: string = '/stream';
    constructor(props: Props) {
        super(props);

        this.state = {
            cancel: new AbortController(),
            streams: undefined,
            error: null,
        };
    }
    override componentDidMount(): void {
        this.loadHeaders();
    }
    override componentWillUnmount(): void {
        this.state.cancel.abort();
    }

    private async loadHeaders() {
        try {
            var rsp = await fetch('/api/streams', {
                headers: { 'Content-Type': 'application/json' },
                signal: this.state.cancel.signal,
            });
        } catch (e) {
            if (e instanceof DOMException && e.name == 'AbortError') {
                this.setState({ error: 'Aborted' });
            } else {
                this.setState({ error: `${e}` });
            }
            return;
        }
        if (!rsp.ok) {
            let error = `Error listing streams: HTTP ${rsp.status} ${rsp.statusText}`;
            try {
                error += " " + await rsp.text();
            } catch {}
            this.setState({ error });
            return;
        }
        console.log(rsp);
        try {
            var json = await rsp.json();
        } catch(e) {
            console.error("Unable to get json");
            this.setState({ error: `Unable to parse API response`});
            return;
        }
        this.setState({ error: null, streams: json });
    }
    override render(): React.ReactNode {
        if (this.state.error)
            return <ErrorMsg>{this.state.error}</ErrorMsg>;
        else if (typeof this.state.streams === 'undefined')
            return <Loading />;
        
        // Coallate streams by camera name
        const streamsByCamera = new Map<string, string[]>();
        for (const stream of this.state.streams ?? []) {
            if (!streamsByCamera.has(stream.worker))
                streamsByCamera.set(stream.worker, []);
            streamsByCamera.get(stream.worker)!.push(stream.name);
        }
        
        return (
            <ul>
                {Array.from(streamsByCamera.entries()).map(([worker, streams]) =>
                    <li key={worker}>
                        {worker}
                        <ul>
                            {streams.map(stream => (
                                <li key={stream}>
                                    <a href={`#stream/${worker}/${stream}`}>{stream}</a>
                                </li>
                            ))}
                        </ul>
                    </li>
                )}
            </ul>
        );
    }
}