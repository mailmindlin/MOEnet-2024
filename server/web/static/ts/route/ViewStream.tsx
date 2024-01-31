import React from 'react';
import RtcVideo from '../components/RtcVideo';
import { RouteProps } from '../routing';
interface Props extends RouteProps {

}

interface State {

}

export default class ViewStream extends React.Component<Props, State> {
    static readonly pattern = [
        new URLPattern({pathname: '/stream/:worker/:stream', search: "autoplay=:autoplay" }),
        new URLPattern({pathname: '/stream/:worker/:stream' })
    ];
    static readonly title: string = 'Stream';

    private video?: RtcVideo;
    handleStart = () => {
        this.video?.start();
    }
    handleStop = () => {
        this.video?.stop();
    }
    handleVideoRef = (vid: RtcVideo) => {
        this.video = vid;
        if (vid && this.props.route.search.groups['autoplay']) {
            console.log('start');
            vid.start();
        }
    }
    
    render(): React.ReactNode {
        const worker = this.props.route.pathname.groups['worker']!;
        const stream = this.props.route.pathname.groups['stream']!;
        return (<>
            <RtcVideo
                ref={this.handleVideoRef}
                worker={worker}
                stream={stream}
            />
            <button onClick={this.handleStart}>Start</button>
            <button onClick={this.handleStop}>Stop</button>
        </>);
    }
}