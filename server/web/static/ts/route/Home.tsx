import React from 'react';
import { RouteProps } from '../routing';

export default class HomeView extends React.Component<RouteProps, {}> {
    static readonly pattern: URLPattern = new URLPattern({pathname: '/' });
    static readonly title: string = 'Home';
    static readonly base: string = '/';

    render(): React.ReactNode {
        return (
            <div>Home</div>
        );
    }
}