import React from 'react';
import HomeView from "./route/Home";
import EditConfig from "./route/EditConfig";
import ViewStream from "./route/ViewStream";
import StreamList from './route/StreamList';
const routes = [
    HomeView,
    EditConfig,
    StreamList,
    ViewStream,
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
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoicm91dGluZy5qcyIsInNvdXJjZVJvb3QiOiIiLCJzb3VyY2VzIjpbIi4uL3RzL3JvdXRpbmcudHN4Il0sIm5hbWVzIjpbXSwibWFwcGluZ3MiOiJBQUFBLE9BQU8sS0FBSyxNQUFNLE9BQU8sQ0FBQztBQUMxQixPQUFPLFFBQVEsTUFBTSxjQUFjLENBQUM7QUFDcEMsT0FBTyxVQUFVLE1BQU0sb0JBQW9CLENBQUM7QUFDNUMsT0FBTyxVQUFVLE1BQU0sb0JBQW9CLENBQUM7QUFFNUMsT0FBTyxVQUFVLE1BQU0sb0JBQW9CLENBQUM7QUFZNUMsTUFBTSxNQUFNLEdBQWlDO0lBQzVDLFFBQVE7SUFDUixVQUFVO0lBQ1YsVUFBVTtJQUNWLFVBQVU7Q0FDVixDQUFDO0FBRUYsU0FBUyxPQUFPLENBQUMsS0FBK0M7SUFDL0QsSUFBSSxPQUFPLEdBQUcsS0FBSyxDQUFDLE1BQU0sQ0FBQyxJQUFJLENBQUM7SUFDaEMsSUFBSSxDQUFDLE9BQU87UUFDWCxPQUFPLElBQUksQ0FBQztJQUViLGtHQUFrRztJQUNsRyx1QkFBdUI7SUFDdkIsb0RBQW9EO0lBQ3BELHNCQUFzQjtJQUVuQixPQUFPLENBQ0gsMkJBQUcsSUFBSSxFQUFFLEdBQUcsR0FBRyxPQUFPLGlCQUFlLEtBQUssQ0FBQyxNQUFNLElBQzVDLEtBQUssQ0FBQyxNQUFNLENBQUMsS0FBSyxDQUNuQixDQUNQLENBQUE7QUFDTCxDQUFDO0FBT0QsTUFBTSxPQUFPLE1BQU8sU0FBUSxLQUFLLENBQUMsU0FBMEI7SUFDM0QsaUJBQWlCO1FBQ2hCLE1BQU0sQ0FBQyxnQkFBZ0IsQ0FBQyxZQUFZLEVBQUUsSUFBSSxDQUFDLGdCQUFnQixDQUFDLENBQUM7SUFDOUQsQ0FBQztJQUVELG9CQUFvQjtRQUNuQixNQUFNLENBQUMsbUJBQW1CLENBQUMsWUFBWSxFQUFFLElBQUksQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDO0lBQ2pFLENBQUM7SUFDRCxNQUFNLENBQUMsWUFBWSxDQUFDLEdBQVE7UUFDM0IsSUFBSSxJQUFJLEdBQUcs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