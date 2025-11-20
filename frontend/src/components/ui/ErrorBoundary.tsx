import { Component, ErrorInfo, ReactNode } from 'react';
import { Button } from '@mui/material';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught error:', error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          height: '100vh',
          padding: 20,
          textAlign: 'center'
        }}>
          <h2 style={{ color: '#d32f2f', marginBottom: 16 }}>Something went wrong</h2>
          <p style={{ marginBottom: 24, color: '#666' }}>
            {this.state.error?.message || 'An unexpected error occurred'}
          </p>
          <Button
            variant="contained"
            onClick={() => window.location.reload()}
            sx={{ backgroundColor: '#1B6840' }}
          >
            Reload Page
          </Button>
        </div>
      );
    }

    return this.props.children;
  }
}
