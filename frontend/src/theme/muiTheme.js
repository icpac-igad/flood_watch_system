import { createTheme } from '@mui/material/styles';

// FloodWatch custom theme matching existing design
export const floodWatchTheme = createTheme({
  palette: {
    primary: {
      main: '#034930', // FloodWatch green
      light: '#056b47',
      dark: '#023321',
      contrastText: '#ffffff',
    },
    secondary: {
      main: '#FFC107', // Warning yellow
      light: '#FFD54F',
      dark: '#FFA000',
      contrastText: '#000000',
    },
    info: {
      main: '#2196F3',
      light: '#64B5F6',
      dark: '#1976D2',
    },
    success: {
      main: '#4CAF50',
      light: '#81C784',
      dark: '#388E3C',
    },
    warning: {
      main: '#FF9800',
      light: '#FFB74D',
      dark: '#F57C00',
    },
    error: {
      main: '#F44336',
      light: '#E57373',
      dark: '#D32F2F',
    },
    background: {
      default: '#f8f9fa',
      paper: '#ffffff',
    },
    text: {
      primary: '#333333',
      secondary: '#666666',
    },
  },
  typography: {
    fontFamily: [
      '-apple-system',
      'BlinkMacSystemFont',
      '"Segoe UI"',
      'Roboto',
      '"Helvetica Neue"',
      'Arial',
      'sans-serif',
    ].join(','),
    h1: {
      fontSize: '2rem',
      fontWeight: 600,
      color: '#034930',
    },
    h2: {
      fontSize: '1.75rem',
      fontWeight: 600,
      color: '#034930',
    },
    h3: {
      fontSize: '1.5rem',
      fontWeight: 600,
      color: '#034930',
    },
    h4: {
      fontSize: '1.25rem',
      fontWeight: 600,
      color: '#034930',
    },
    h5: {
      fontSize: '1.1rem',
      fontWeight: 600,
      color: '#034930',
    },
    h6: {
      fontSize: '1rem',
      fontWeight: 600,
      color: '#034930',
    },
    body1: {
      fontSize: '0.875rem',
      lineHeight: 1.5,
    },
    body2: {
      fontSize: '0.8125rem',
      lineHeight: 1.5,
    },
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          minHeight: 44,
          fontSize: '0.9rem',
          fontWeight: 500,
          borderRadius: 4,
        },
      },
    },
    MuiSwitch: {
      styleOverrides: {
        root: {
          padding: 8,
        },
        thumb: {
          width: 20,
          height: 20,
        },
        track: {
          borderRadius: 11,
        },
      },
    },
    MuiAccordion: {
      styleOverrides: {
        root: {
          boxShadow: 'none',
          border: '1px solid #dee2e6',
          borderRadius: '4px !important',
          '&:before': {
            display: 'none',
          },
          marginBottom: 15,
        },
      },
    },
    MuiAccordionSummary: {
      styleOverrides: {
        root: {
          minHeight: 48,
          '&.Mui-expanded': {
            minHeight: 48,
          },
        },
        content: {
          margin: '12px 0',
          '&.Mui-expanded': {
            margin: '12px 0',
          },
        },
      },
    },
    MuiDrawer: {
      styleOverrides: {
        paper: {
          borderRight: '2px solid #d0d0d0',
          boxShadow: '2px 0 6px rgba(0, 0, 0, 0.15)',
        },
      },
    },
    MuiTextField: {
      styleOverrides: {
        root: {
          '& .MuiInputBase-root': {
            minHeight: 44,
          },
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          height: 28,
          fontSize: '0.8125rem',
        },
      },
    },
    MuiAlert: {
      styleOverrides: {
        root: {
          borderRadius: 4,
          fontSize: '0.875rem',
        },
      },
    },
    MuiListItemButton: {
      styleOverrides: {
        root: {
          minHeight: 44,
          padding: '8px 15px',
        },
      },
    },
    MuiFormControlLabel: {
      styleOverrides: {
        root: {
          marginLeft: 0,
          marginRight: 0,
        },
      },
    },
    MuiTooltip: {
      styleOverrides: {
        tooltip: {
          fontSize: '0.8125rem',
          backgroundColor: '#034930',
        },
        arrow: {
          color: '#034930',
        },
      },
    },
  },
  breakpoints: {
    values: {
      xs: 0,
      sm: 576,
      md: 768,
      lg: 992,
      xl: 1200,
    },
  },
  spacing: 8, // Base spacing unit (8px)
  shape: {
    borderRadius: 4,
  },
  shadows: [
    'none',
    '0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.24)',
    '0 3px 6px rgba(0,0,0,0.15), 0 2px 4px rgba(0,0,0,0.12)',
    '0 10px 20px rgba(0,0,0,0.15), 0 3px 6px rgba(0,0,0,0.10)',
    '0 15px 25px rgba(0,0,0,0.15), 0 5px 10px rgba(0,0,0,0.05)',
    '0 20px 40px rgba(0,0,0,0.2)',
    '0 -4px 16px rgba(0,0,0,0.2)', // For bottom sheets
    ...Array(18).fill('none'), // Fill remaining shadow levels
  ],
});
