import React from 'react';
export default function ErrorMsg(props: { children: React.ReactNode }) {
    return (<div style={{color: 'red', fontWeight: 'bold'}}>Error: {props.children}</div>);
}