import React from 'react';
import RtcVideo from '../components/RtcVideo';
import { RouteProps } from '../routing';
interface Props extends RouteProps {

}

interface State {
    cancel: AbortController;
    streams?: Array<{name: string, worker: string}>;
    error?: string;
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
            error: undefined,
        };
    }
    componentDidMount(): void {
        this.loadHeaders();
    }
    componentWillUnmount(): void {
        this.state.cancel.abort();
    }

    async loadHeaders() {
        try {
            let rsp = await fetch('/api/streams', {
                headers: { 'Content-Type': 'application/json' },
                signal: this.state.cancel.signal,
            });
            var json = await rsp.json();
        } catch(e) {
            console.error("Unable to load headers");
            this.setState({ error: `${e}`});
            return;
        }
        this.setState({streams: json });
    }
    render(): React.ReactNode {
        if (this.state.error) {
            return <div style={{color: 'red'}}>Error: {this.state.error}</div>
        }
        if (typeof this.state.streams === 'undefined')
            return <div>Loading...</div>;
        
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