import React from "react";

interface Props {
	stun?: boolean;
	worker: string;
	stream: string;
}

export default class RtcVideo extends React.Component<Props> {
	private pc?: RTCPeerConnection;
	private readonly videoRef = React.createRef<HTMLVideoElement>();

	override componentWillUnmount(): void {
		console.log('unmount');
		this.stop();
	}

	start() {
		if (this.pc) {
			console.warn('restart');
		}
		const config: RTCConfiguration & { sdpSemantics: string } = {
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
				} else {
					console.warn('no video');
				}
			} else {
				console.warn('Got audio stream?');
			}
		});

		return this.negotiate();
	}
	private async negotiate() {
		const pc = this.pc;
		if (!pc)
			return;
		pc.addTransceiver('video', { direction: 'recvonly' });
		// pc.addTransceiver('audio', { direction: 'recvonly' });
		try {
			const offer = await pc.createOffer();
			await pc.setLocalDescription(offer);

			// wait for ICE gathering to complete
			let offerDesc = await new Promise<RTCSessionDescription>((resolve) => {
				if (pc.iceGatheringState === 'complete') {
					resolve(pc.localDescription!);
				} else {
					const checkState = () => {
						if (pc.iceGatheringState === 'complete') {
							pc.removeEventListener('icegatheringstatechange', checkState);
							resolve(pc.localDescription!);
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
		} catch (e) {
			alert(e);
		}
	}

	stop() {
		this.pc?.close();
	}

	override render(): React.ReactNode {
		return (
			<video
				playsInline
				autoPlay
				muted
				ref={this.videoRef}
			/>
		)
	}
}