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
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiUnRjVmlkZW8uanMiLCJzb3VyY2VSb290IjoiIiwic291cmNlcyI6WyIuLi8uLi90cy9jb21wb25lbnRzL1J0Y1ZpZGVvLnRzeCJdLCJuYW1lcyI6W10sIm1hcHBpbmdzIjoiQUFBQSxPQUFPLEtBQUssTUFBTSxPQUFPLENBQUM7QUFRMUIsTUFBTSxDQUFDLE9BQU8sT0FBTyxRQUFTLFNBQVEsS0FBSyxDQUFDLFNBQWdCO0lBQ25ELEVBQUUsQ0FBcUI7SUFDZCxRQUFRLEdBQUcsS0FBSyxDQUFDLFNBQVMsRUFBb0IsQ0FBQztJQUVoRSxvQkFBb0I7UUFDbkIsT0FBTyxDQUFDLEdBQUcsQ0FBQyxTQUFTLENBQUMsQ0FBQztRQUN2QixJQUFJLENBQUMsSUFBSSxFQUFFLENBQUM7SUFDYixDQUFDO0lBRUQsS0FBSztRQUNKLElBQUksSUFBSSxDQUFDLEVBQUUsRUFBRTtZQUNaLE9BQU8sQ0FBQyxJQUFJLENBQUMsU0FBUyxDQUFDLENBQUM7U0FDeEI7UUFDRCxNQUFNLE1BQU0sR0FBZ0Q7WUFDM0QsWUFBWSxFQUFFLGNBQWM7U0FDNUIsQ0FBQztRQUVGLElBQUksSUFBSSxDQUFDLEtBQUssQ0FBQyxJQUFJLEVBQUU7WUFDcEIsTUFBTSxDQUFDLFVBQVUsR0FBRyxDQUFDLEVBQUUsSUFBSSxFQUFFLENBQUMsOEJBQThCLENBQUMsRUFBRSxDQUFDLENBQUM7U0FDakU7UUFFRCxJQUFJLENBQUMsRUFBRSxHQUFHLElBQUksaUJBQWlCLENBQUMsTUFBTSxDQUFDLENBQUM7UUFFeEMsd0JBQXdCO1FBQ3hCLElBQUksQ0FBQyxFQUFFLENBQUMsZ0JBQWdCLENBQUMsT0FBTyxFQUFFLEdBQUcsQ0FBQyxFQUFFO1lBQ3ZDLE9BQU8sQ0FBQyxHQUFHLENBQUMsT0FBTyxDQUFDLENBQUM7WUFDckIsSUFBSSxHQUFHLENBQUMsS0FBSyxDQUFDLElBQUksSUFBSSxPQUFPLEVBQUU7Z0JBQzlCLE9BQU8sQ0FBQyxHQUFHLENBQUMsYUFBYSxFQUFFLEdBQUcsQ0FBQyxPQUFPLEVBQUUs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