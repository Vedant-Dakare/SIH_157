import * as React from 'react';

import { ErrorState } from '@/components/common/ErrorState';

export interface ErrorBoundaryProps {
  children: React.ReactNode;
  label: string;
}

interface ErrorBoundaryState {
  error: Error | null;
}

/** Isolates one section so its crash never takes down sibling sections. */
export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error };
  }

  render(): React.ReactNode {
    if (this.state.error) {
      return (
        <ErrorState
          error={this.state.error}
          message={`${this.props.label} failed to render.`}
          retry={() => this.setState({ error: null })}
        />
      );
    }
    return this.props.children;
  }
}
