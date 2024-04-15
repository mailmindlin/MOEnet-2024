import React from 'react';
import HomeView from "./route/Home";
import EditConfig from "./route/EditConfig";
import ViewStream from "./route/ViewStream";
import StreamList from './route/StreamList';
import ConfigBuilder from './route/ConfigBuilder/index';
const routes = [
    HomeView,
    EditConfig,
    StreamList,
    ViewStream,
    ConfigBuilder,
];
function NavLink(props) {
    let pattern = props.target.base;
    if (!pattern)
        return null;
    // const handleClick = React.useCallback((e: React.MouseEvent<HTMLAnchorElement, MouseEvent>) => {
    // 	e.preventDefault();
    // 	window.history.pushState({}, "Title", pathname);
    // }, [props.target]);
    return (React.createElement("a", { href: '#' + pattern, "data-active": props.active }, props.target.title));
}
export class Router extends React.Component {
    componentDidMount() {
        window.addEventListener('hashchange', this.handleHashChange);
    }
    componentWillUnmount() {
        window.removeEventListener('hashchange', this.handleHashChange);
    }
    static stateFromURL(url) {
        let hash = url.hash;
        if (hash.startsWith('#'))
            hash = hash.substring(1);
        if (hash.startsWith('/'))
            hash = hash.substring(1);
        url = new URL(url.origin + '/' + hash);
        let activeRoute = [routes[0], {}];
        outer: for (const route of routes) {
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
    constructor(props) {
        super(props);
        this.state = Router.stateFromURL(new URL(window.location.toString()));
    }
    handleHashChange = (e) => {
        this.setState(Router.stateFromURL(new URL(e.newURL)));
    };
    render() {
        return (React.createElement(React.Fragment, null,
            React.createElement("nav", null, routes.map(route => (React.createElement(NavLink, { target: route, active: this.state.activeRoute[0] == route, key: route.title })))),
            React.createElement("div", { id: "view" }, React.createElement(this.state.activeRoute[0], { route: this.state.activeRoute[1] }))));
    }
}
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoicm91dGluZy5qcyIsInNvdXJjZVJvb3QiOiIiLCJzb3VyY2VzIjpbIi4uL3RzL3JvdXRpbmcudHN4Il0sIm5hbWVzIjpbXSwibWFwcGluZ3MiOiJBQUFBLE9BQU8sS0FBSyxNQUFNLE9BQU8sQ0FBQztBQUMxQixPQUFPLFFBQVEsTUFBTSxjQUFjLENBQUM7QUFDcEMsT0FBTyxVQUFVLE1BQU0sb0JBQW9CLENBQUM7QUFDNUMsT0FBTyxVQUFVLE1BQU0sb0JBQW9CLENBQUM7QUFFNUMsT0FBTyxVQUFVLE1BQU0sb0JBQW9CLENBQUM7QUFDNUMsT0FBTyxhQUFhLE1BQU0sNkJBQTZCLENBQUM7QUFZeEQsTUFBTSxNQUFNLEdBQWlDO0lBQzVDLFFBQVE7SUFDUixVQUFVO0lBQ1YsVUFBVTtJQUNWLFVBQVU7SUFDVixhQUFhO0NBQ2IsQ0FBQztBQUVGLFNBQVMsT0FBTyxDQUFDLEtBQStDO0lBQy9ELElBQUksT0FBTyxHQUFHLEtBQUssQ0FBQyxNQUFNLENBQUMsSUFBSSxDQUFDO0lBQ2hDLElBQUksQ0FBQyxPQUFPO1FBQ1gsT0FBTyxJQUFJLENBQUM7SUFFYixrR0FBa0c7SUFDbEcsdUJBQXVCO0lBQ3ZCLG9EQUFvRDtJQUNwRCxzQkFBc0I7SUFFbkIsT0FBTyxDQUNILDJCQUFHLElBQUksRUFBRSxHQUFHLEdBQUcsT0FBTyxpQkFBZSxLQUFLLENBQUMsTUFBTSxJQUM1QyxLQUFLLENBQUMsTUFBTSxDQUFDLEtBQUssQ0FDbkIsQ0FDUCxDQUFBO0FBQ0wsQ0FBQztBQU9ELE1BQU0sT0FBTyxNQUFPLFNBQVEsS0FBSyxDQUFDLFNBQTBCO0lBQ2xELGlCQUFpQjtRQUN6QixNQUFNLENBQUMsZ0JBQWdCLENBQUMsWUFBWSxFQUFFLElBQUksQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDO0lBQzlELENBQUM7SUFFUSxvQkFBb0I7UUFDNUIsTUFBTSxDQUFDLG1CQUFtQixDQUFDLFlBQVksRUFBRSxJQUFJLENBQUMsZ0JBQWdCLENBQUMsQ0FBQztJQUNqRSxDQUFDO0lBQ0QsTUFB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