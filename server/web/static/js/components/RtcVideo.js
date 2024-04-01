import React from "react";
export default class RtcVideo extends React.Component {
    pc;
    videoRef = React.createRef();
    componentWillUnmount() {
        console.log('unmount');
        this.stop();
    }
    start() {
        if (this.pc) {
            console.warn('restart');
        }
        const config = {
            sdpSemantics: 'unified-plan'
        };
        if (this.props.stun) {
            config.iceServers = [{ urls: ['stun:stun.l.google.com:19302'] }];
        }
        this.pc = new RTCPeerConnection(config);
        // connect audio / video
        this.pc.addEventListener('track', evt => {
            console.log('track');
            if (evt.track.kind == 'video') {
                console.log('got streams', evt.streams, this.videoRef.current);
                const video = this.videoRef.current;
                if (video) {
                    video.srcObject = evt.streams[0];
                }
                else {
                    console.warn('no video');
                }
            }
            else {
                console.warn('Got audio stream?');
            }
        });
        return this.negotiate();
    }
    async negotiate() {
        const pc = this.pc;
        if (!pc)
            return;
        pc.addTransceiver('video', { direction: 'recvonly' });
        // pc.addTransceiver('audio', { direction: 'recvonly' });
        try {
            const offer = await pc.createOffer();
            await pc.setLocalDescription(offer);
            // wait for ICE gathering to complete
            let offerDesc = await new Promise((resolve) => {
                if (pc.iceGatheringState === 'complete') {
                    resolve(pc.localDescription);
                }
                else {
                    const checkState = () => {
                        if (pc.iceGatheringState === 'complete') {
                            pc.removeEventListener('icegatheringstatechange', checkState);
                            resolve(pc.localDescription);
                        }
                    };
                    pc.addEventListener('icegatheringstatechange', checkState);
                }
            });
            const resp = await fetch('/api/stream', {
                body: JSON.stringify({
                    worker: this.props.worker,
                    stream: this.props.stream,
                    sdp: offerDesc.sdp,
                    type: offerDesc.type,
                }),
                headers: {
                    'Content-Type': 'application/json'
                },
                method: 'POST'
            });
            await pc.setRemoteDescription(await resp.json());
        }
        catch (e) {
            alert(e);
        }
    }
    stop() {
        this.pc?.close();
    }
    render() {
        return (React.createElement("video", { playsInline: true, autoPlay: true, muted: true, ref: this.videoRef }));
    }
}
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiUnRjVmlkZW8uanMiLCJzb3VyY2VSb290IjoiIiwic291cmNlcyI6WyIuLi8uLi90cy9jb21wb25lbnRzL1J0Y1ZpZGVvLnRzeCJdLCJuYW1lcyI6W10sIm1hcHBpbmdzIjoiQUFBQSxPQUFPLEtBQUssTUFBTSxPQUFPLENBQUM7QUFRMUIsTUFBTSxDQUFDLE9BQU8sT0FBTyxRQUFTLFNBQVEsS0FBSyxDQUFDLFNBQWdCO0lBQ25ELEVBQUUsQ0FBcUI7SUFDZCxRQUFRLEdBQUcsS0FBSyxDQUFDLFNBQVMsRUFBb0IsQ0FBQztJQUVoRSxvQkFBb0I7UUFDbkIsT0FBTyxDQUFDLEdBQUcsQ0FBQyxTQUFTLENBQUMsQ0FBQztRQUN2QixJQUFJLENBQUMsSUFBSSxFQUFFLENBQUM7SUFDYixDQUFDO0lBRUQsS0FBSztRQUNKLElBQUksSUFBSSxDQUFDLEVBQUUsRUFBRSxDQUFDO1lBQ2IsT0FBTyxDQUFDLElBQUksQ0FBQyxTQUFTLENBQUMsQ0FBQztRQUN6QixDQUFDO1FBQ0QsTUFBTSxNQUFNLEdBQWdEO1lBQzNELFlBQVksRUFBRSxjQUFjO1NBQzVCLENBQUM7UUFFRixJQUFJLElBQUksQ0FBQyxLQUFLLENBQUMsSUFBSSxFQUFFLENBQUM7WUFDckIsTUFBTSxDQUFDLFVBQVUsR0FBRyxDQUFDLEVBQUUsSUFBSSxFQUFFLENBQUMsOEJBQThCLENBQUMsRUFBRSxDQUFDLENBQUM7UUFDbEUsQ0FBQztRQUVELElBQUksQ0FBQyxFQUFFLEdBQUcsSUFBSSxpQkFBaUIsQ0FBQyxNQUFNLENBQUMsQ0FBQztRQUV4Qyx3QkFBd0I7UUFDeEIsSUFBSSxDQUFDLEVBQUUsQ0FBQyxnQkFBZ0IsQ0FBQyxPQUFPLEVBQUUsR0FBRyxDQUFDLEVBQUU7WUFDdkMsT0FBTyxDQUFDLEdBQUcsQ0FBQyxPQUFPLENBQUMsQ0FBQztZQUNyQixJQUFJLEdBQUcsQ0FBQyxLQUFLLENBQUMsSUFBSSxJQUFJLE9BQU8sRUFBRSxDQUFDO2dCQUMvQixPQUFPLENBQUMsR0FBRyxDQUFDLGFBQWEs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