import React from 'react';
import HomeView from "./route/Home";
import EditConfig from "./route/EditConfig";
import ViewStream from "./route/ViewStream";
import { URLPatternResult } from './pattern';
import StreamList from './route/StreamList';
import ConfigBuilder from './route/ConfigBuilder/index';

export interface RouteProps {
	route: URLPatternResult,
}

interface DeclaredRoute extends React.ComponentClass<RouteProps> {
	readonly pattern: URLPattern | ReadonlyArray<URLPattern>,
	readonly title: string;
	readonly base?: string;
}

const routes: ReadonlyArray<DeclaredRoute> = [
	HomeView,
	EditConfig,
	StreamList,
	ViewStream,
	ConfigBuilder,
];

function NavLink(props: {target: DeclaredRoute, active: boolean}) {
	let pattern = props.target.base;
	if (!pattern)
		return null;

	// const handleClick = React.useCallback((e: React.MouseEvent<HTMLAnchorElement, MouseEvent>) => {
	// 	e.preventDefault();
	// 	window.history.pushState({}, "Title", pathname);
	// }, [props.target]);

    return (
        <a href={'#' + pattern} data-active={props.active}>
            {props.target.title}
        </a>
    )
}

interface RouterState {
	url: string,
	activeRoute: [DeclaredRoute, URLPatternResult],
}

export class Router extends React.Component<{}, RouterState> {
	override componentDidMount(): void {
		window.addEventListener('hashchange', this.handleHashChange);
	}
	
	override componentWillUnmount(): void {
		window.removeEventListener('hashchange', this.handleHashChange);
	}
	static stateFromURL(url: URL): RouterState {
		let hash = url.hash;
		if (hash.startsWith('#'))
			hash = hash.substring(1);
		if (hash.startsWith('/'))
			hash = hash.substring(1);
		url = new URL(url.origin + '/' + hash);

		let activeRoute = [routes[0], {}] as [DeclaredRoute, URLPatternResult];
		outer:for (const route of routes) {
			let patterns = Array.isArray(route.pattern) ? route.pattern : [route.pattern];
			for (const pattern of patterns) {
				const match = pattern.exec(url);
				if (match) {
					activeRoute = [route, match];
					break outer;
				}
			}
		}
		return {
			url: hash,
			activeRoute,
		};
	}
	constructor(props: {}) {
		super(props);

		this.state = Router.stateFromURL(new URL(window.location.toString()));
	}
	handleHashChange = (e: HashChangeEvent) => {
		this.setState(Router.stateFromURL(new URL(e.newURL)));
	}
	override render(): React.ReactNode {
		return (<>
			<nav>
				{
					routes.map(route => (
						<NavLink target={route} active={this.state.activeRoute[0] == route} key={route.title} />
					))
				}
        	</nav>
			<div id="view">
				{
					React.createElement(this.state.activeRoute[0], { route: this.state.activeRoute[1] })
				}
			</div>
		</>);
	}
}