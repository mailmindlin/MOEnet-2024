import React, { ChangeEvent, FormEvent } from 'react';
import { RouteProps } from '../routing';


interface Props extends RouteProps {

}

interface State {
    schema: object,
    value: string,
    valueRaw: string,
    isValid: boolean,
    editingRaw: boolean,
    cancel: AbortController,
}


export default class EditConfig extends React.Component<Props, State> {
    static readonly pattern: URLPattern = new URLPattern({ pathname: '/configraw' });
    static readonly title: string = 'Raw Config';
    static readonly base: string = '/configraw';
    private readonly suffix: string;

    constructor(props: Props) {
        super(props);
        this.suffix = `${Math.floor(Math.random() * 1e6)}`;
        this.state = {
            schema: {},
            value: '{}',
            valueRaw: '{}',
            editingRaw: true,
            isValid: true,
            cancel: new AbortController(),
        }
    }

    private uniqueId(name: string): string {
        return `${name}${this.suffix}`;
    }

    componentDidMount(): void {
        this.fetchConfig();
        this.fetchSchema();
    }

    async fetchSchema() {
        try {
            const res = await fetch('/api/schema', {
                signal: this.state.cancel.signal,
                headers: { 'Content-Type': 'application/json' }
            });
            var data = await res.json();
        } catch {
            console.error('No schema');
            return;
        }
        this.setState({
            schema: data
        })
    }

    async fetchConfig() {
        try {
            const res = await fetch('/api/config', {
                signal: this.state.cancel.signal,
                headers: { 'Content-Type': 'application/json' }
            });
            var data = await res.json();
        } catch {
            console.error('No config');
            return;
        }
        this.setState({
            value: JSON.stringify(data),
            valueRaw: JSON.stringify(data, undefined, '  '),
        })
    }
    

    handleValueChange = (e: FormEvent<HTMLPreElement>) => {
        const valueRaw = e.currentTarget.innerText;
        try {
            var parsed = JSON.parse(valueRaw);
        } catch {
            this.setState({ valueRaw, isValid: false });
            return;
        }
        var value = JSON.stringify(parsed);
        var valueRaw2 = JSON.stringify(parsed,undefined,'  ');
        this.setState(({ value: valueOld }) => (value == valueOld ? { valueRaw: valueRaw, value: valueOld, isValid: true } : { value, valueRaw: valueRaw2, isValid: true }));
    }

    handleEditingRawChange = (e: ChangeEvent<HTMLInputElement>) => {
        this.setState({ editingRaw: e.currentTarget.checked });
    }

    render(): React.ReactNode {
        return (
            <div>
                <label
                    htmlFor={this.uniqueId('editingRaw')}
                >
                    Edit raw?
                </label>
                <input
                    id={this.uniqueId('editingRaw')}
                    type='checkbox'
                    checked={this.state.editingRaw}
                    onChange={this.handleEditingRawChange}
                />
                { this.state.editingRaw && (
                    <pre
                        style={{width: "100%", display: "block"}}
                        contentEditable
                        onInput={this.handleValueChange}
                    >
                        {this.state.valueRaw}
                    </pre>
                )}
                { this.state.editingRaw || (<></>
                )}
                <button
                    disabled={!this.state.isValid}
                >
                    Save
                </button>
            </div>
        )
    }
}