import React from 'react';
import RtcVideo from '../components/RtcVideo';
export default class ViewStream extends React.Component {
    static pattern = [
        new URLPattern({ pathname: '/stream/:worker/:stream', search: "autoplay=:autoplay" }),
        new URLPattern({ pathname: '/stream/:worker/:stream' })
    ];
    static title = 'Stream';
    video;
    handleStart = () => {
        this.video?.start();
    };
    handleStop = () => {
        this.video?.stop();
    };
    handleVideoRef = (vid) => {
        this.video = vid;
        if (vid && this.props.route.search.groups['autoplay']) {
            console.log('start');
            vid.start();
        }
    };
    render() {
        const worker = this.props.route.pathname.groups['worker'];
        const stream = this.props.route.pathname.groups['stream'];
        return (React.createElement(React.Fragment, null,
            React.createElement(RtcVideo, { ref: this.handleVideoRef, worker: worker, stream: stream }),
            React.createElement("button", { onClick: this.handleStart }, "Start"),
            React.createElement("button", { onClick: this.handleStop }, "Stop")));
    }
}
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiVmlld1N0cmVhbS5qcyIsInNvdXJjZVJvb3QiOiIiLCJzb3VyY2VzIjpbIi4uLy4uL3RzL3JvdXRlL1ZpZXdTdHJlYW0udHN4Il0sIm5hbWVzIjpbXSwibWFwcGluZ3MiOiJBQUFBLE9BQU8sS0FBSyxNQUFNLE9BQU8sQ0FBQztBQUMxQixPQUFPLFFBQVEsTUFBTSx3QkFBd0IsQ0FBQztBQVU5QyxNQUFNLENBQUMsT0FBTyxPQUFPLFVBQVcsU0FBUSxLQUFLLENBQUMsU0FBdUI7SUFDakUsTUFBTSxDQUFVLE9BQU8sR0FBRztRQUN0QixJQUFJLFVBQVUsQ0FBQyxFQUFDLFFBQVEsRUFBRSx5QkFBeUIsRUFBRSxNQUFNLEVBQUUsb0JBQW9CLEVBQUUsQ0FBQztRQUNwRixJQUFJLFVBQVUsQ0FBQyxFQUFDLFFBQVEsRUFBRSx5QkFBeUIsRUFBRSxDQUFDO0tBQ3pELENBQUM7SUFDRixNQUFNLENBQVUsS0FBSyxHQUFXLFFBQVEsQ0FBQztJQUVqQyxLQUFLLENBQVk7SUFDekIsV0FBVyxHQUFHLEdBQUcsRUFBRTtRQUNmLElBQUksQ0FBQyxLQUFLLEVBQUUsS0FBSyxFQUFFLENBQUM7SUFDeEIsQ0FBQyxDQUFBO0lBQ0QsVUFBVSxHQUFHLEdBQUcsRUFBRTtRQUNkLElBQUksQ0FBQyxLQUFLLEVBQUUsSUFBSSxFQUFFLENBQUM7SUFDdkIsQ0FBQyxDQUFBO0lBQ0QsY0FBYyxHQUFHLENBQUMsR0FBYSxFQUFFLEVBQUU7UUFDL0IsSUFBSSxDQUFDLEtBQUssR0FBRyxHQUFHLENBQUM7UUFDakIsSUFBSSxHQUFHLElBQUksSUFBSSxDQUFDLEtBQUssQ0FBQyxLQUFLLENBQUMsTUFBTSxDQUFDLE1BQU0sQ0FBQyxVQUFVLENBQUMsRUFBRTtZQUNuRCxPQUFPLENBQUMsR0FBRyxDQUFDLE9BQU8sQ0FBQyxDQUFDO1lBQ3JCLEdBQUcsQ0FBQyxLQUFLLEVBQUUsQ0FBQztTQUNmO0lBQ0wsQ0FBQyxDQUFBO0lBRUQsTUFBTTtRQUNGLE1BQU0sTUFBTSxHQUFHLElBQUksQ0FBQyxLQUFLLENBQUMsS0FBSyxDQUFDLFFBQVEsQ0FBQyxNQUFNLENBQUMsUUFBUSxDQUFFLENBQUM7UUFDM0QsTUFBTSxNQUFNLEdBQUcsSUFBSSxDQUFDLEtBQUssQ0FBQyxLQUFLLENBQUMsUUFBUSxDQUFDLE1BQU0sQ0FBQyxRQUFRLENBQUUsQ0FBQztRQUMzRCxPQUFPLENBQUM7WUFDSixvQkFBQyxRQUFRLElBQ0wsR0FBRyxFQUFFLElBQUksQ0FBQyxjQUFjLEVBQ3hCLE1BQU0sRUFBRSxNQUFNLEVBQ2QsTUFBTSxFQUFFLE1BQU0sR0FDaEI7WUFDRixnQ0FBUSxPQUFPLEVBQUUsSUFBSSxDQUFDLFdBQVcsWUFBZ0I7WUFDakQsZ0NBQVEsT0FBTyxFQUFFLElBQUksQ0FBQyxVQUFVLFdBQWUsQ0FDaEQsQ0FBQyxDQUFDO0lBQ1QsQ0FBQyJ9