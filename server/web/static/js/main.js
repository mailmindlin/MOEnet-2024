import React from 'react';
import { Router } from './routing';
class App extends React.Component {
    componentDidMount() {
    }
    render() {
        return React.createElement(React.Fragment, null,
            React.createElement(Router, null));
    }
}
const reactRoot = ReactDOM.createRoot(document.getElementById("root"));
reactRoot.render(React.createElement(App, null));
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoibWFpbi5qcyIsInNvdXJjZVJvb3QiOiIiLCJzb3VyY2VzIjpbIi4uL3RzL21haW4udHN4Il0sIm5hbWVzIjpbXSwibWFwcGluZ3MiOiJBQUFBLE9BQU8sS0FBSyxNQUFNLE9BQU8sQ0FBQztBQUcxQixPQUFPLEVBQUUsTUFBTSxFQUFFLE1BQU0sV0FBVyxDQUFDO0FBTW5DLE1BQU0sR0FBSSxTQUFRLEtBQUssQ0FBQyxTQUFvQjtJQUMvQixpQkFBaUI7SUFFMUIsQ0FBQztJQUNRLE1BQU07UUFDWCxPQUFPO1lBQ0gsb0JBQUMsTUFBTSxPQUFHLENBQ1gsQ0FBQztJQUNSLENBQUM7Q0FDSjtBQUVELE1BQU0sU0FBUyxHQUFHLFFBQVEsQ0FBQyxVQUFVLENBQUMsUUFBUSxDQUFDLGNBQWMsQ0FBQyxNQUFNLENBQUUsQ0FBQyxDQUFDO0FBQ3hFLFNBQVMsQ0FBQyxNQUFNLENBQUMsb0JBQUMsR0FBRyxPQUFHLENBQUMsQ0FBQyJ9