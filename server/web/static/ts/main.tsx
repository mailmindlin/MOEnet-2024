import React from 'react';
import type * as ReactDOMT from 'react-dom/client';
declare var ReactDOM: typeof ReactDOMT;
import { Router } from './routing';

interface State {
    
}

class App extends React.Component<{}, State> {
    override componentDidMount(): void {
        
    }
    override render(): React.ReactElement {
        return <>
            <Router />
        </>;
    }
}

const reactRoot = ReactDOM.createRoot(document.getElementById("root")!);
reactRoot.render(<App />);