import React from 'react';
import type * as ReactDOMT from 'react-dom/client';
declare var ReactDOM: typeof ReactDOMT;
import EditConfig from './route/EditConfig';
import ViewStream from './route/ViewStream';
import { Router } from './routing';

const routes = {

}


interface State {
    
}

class App extends React.Component<{}, State> {
    componentDidMount(): void {
        
    }
    render(): React.ReactElement {
        return <>
            <Router />
        </>;
    }
}

const reactRoot = ReactDOM.createRoot(document.getElementById("root")!);
reactRoot.render(<App />);