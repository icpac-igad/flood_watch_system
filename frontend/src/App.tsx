import React from 'react';
import { BrowserRouter as Router, Routes, Route, NavLink } from 'react-router-dom';
import { AppBar, Toolbar, Box, IconButton, Drawer, List, ListItem, ListItemText, Typography } from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import { ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { QueryProvider } from './providers/QueryProvider';
import { ErrorBoundary } from './components/ui/ErrorBoundary';
import { HomePage } from './components/pages/HomePage';
// @ts-ignore
import MapViewer from './components/pages/MapViewer.jsx';
// @ts-ignore
import Partners from './components/pages/Partners.jsx';
// @ts-ignore
import Reports from './components/pages/Reports.jsx';
// @ts-ignore
import StationReport from './components/pages/StationReport.jsx';
import TiPgTestMap from './components/pages/TiPgTestMap';
// @ts-ignore
import { floodWatchTheme } from './theme/muiTheme.js';
import leftLogo from './assets/ICPAC_Website_Header_Logo.svg';
import floodWatchLogo from './assets/flood-watch-banner-transparent.png';
import './App.css';

const Footer: React.FC = () => {
  return (
    <Box
      component="footer"
      sx={{
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        height: '30px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        px: 3,
        backgroundColor: '#034930',
        borderTop: '2px solid rgba(0, 0, 0, 0.3)',
        color: 'white',
        zIndex: 1000
      }}
    >
      <Typography sx={{ 
        color: 'white', 
        fontSize: { xs: '0.65rem', sm: '0.75rem' },
        fontWeight: 400
      }}>
        © 2025 ICPAC - IGAD Climate Prediction and Applications Centre
      </Typography>
    </Box>
  );
};

const App: React.FC = () => {
  const [mobileMenuOpen, setMobileMenuOpen] = React.useState(false);

  const toggleMobileMenu = () => {
    setMobileMenuOpen(!mobileMenuOpen);
  };

  const navLinks = [
    { to: '/', label: 'HOME' },
    { to: '/map', label: 'MAPVIEWER', bold: true },
    { to: '/reports', label: 'REPORTS' },
    { to: '/partners', label: 'PARTNERS' },
  ];

  return (
    <ErrorBoundary>
      <QueryProvider>
        <ThemeProvider theme={floodWatchTheme}>
          <CssBaseline />
          <Router>
            <div className="app-wrapper">
              {/* Navigation Bar using MUI AppBar */}
              <AppBar 
                position="fixed" 
                elevation={0} 
                sx={{ 
                  backgroundColor: '#034930', 
                  borderBottom: '2px solid rgba(0, 0, 0, 0.3)',
                  zIndex: 1100
                }}
              >
                <Toolbar sx={{ minHeight: { xs: '60px', md: '80px' }, px: 2 }}>
                  {/* Left Section: Branding */}
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexShrink: 0 }}>
                    <Box 
                      component="img"
                      src={floodWatchLogo}
                      alt="Flood Watch"
                      sx={{ 
                        height: { xs: '40px', md: '50px' },
                        width: 'auto',
                        display: 'block'
                      }}
                    />
                  </Box>

                  {/* Center Section: Desktop Navigation Links */}
                  <Box
                    sx={{
                      display: { xs: 'none', md: 'flex' },
                      gap: 1,
                      flex: 1,
                      justifyContent: 'center',
                      mx: 2
                    }}
                  >
                    {navLinks.map((link) => (
                      <Box
                        key={link.to}
                        component={NavLink}
                        to={link.to}
                        sx={{
                          textDecoration: 'none',
                          fontSize: '1.1rem',
                          px: 1.5,
                          py: 1,
                          fontWeight: 700,
                          borderRadius: '4px',
                          transition: 'color 0.2s ease, background-color 0.2s ease',
                          '&.active': {
                            color: '#FFC107'
                          },
                          color: 'white',
                          '&:hover': {
                            color: '#FFC107',
                            backgroundColor: 'rgba(255, 255, 255, 0.1)'
                          }
                        }}
                      >
                        {link.label}
                      </Box>
                    ))}
                  </Box>

                  {/* Right Section: ICPAC + Mobile Menu */}
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexShrink: 0 }}>
                    <Box 
                      component="img"
                      src={leftLogo}
                      alt="ICPAC"
                      sx={{ 
                        height: { xs: '40px', md: '50px' },
                        width: 'auto',
                        display: { xs: 'none', sm: 'block' }
                      }}
                    />
                    
                    {/* Mobile Menu Button */}
                    <IconButton
                      color="inherit"
                      aria-label="menu"
                      onClick={toggleMobileMenu}
                      sx={{ display: { xs: 'block', md: 'none' } }}
                    >
                      <MenuIcon />
                    </IconButton>
                  </Box>
                </Toolbar>
              </AppBar>

              {/* Mobile Drawer Menu */}
              <Drawer
                anchor="right"
                open={mobileMenuOpen}
                onClose={toggleMobileMenu}
                sx={{
                  '& .MuiDrawer-paper': {
                    width: 250,
                    backgroundColor: '#034930',
                    color: 'white',
                  }
                }}
              >
                <List>
                  {navLinks.map((link) => (
                    <ListItem
                      key={link.to}
                      component={NavLink}
                      to={link.to}
                      onClick={toggleMobileMenu}
                      sx={{
                        color: 'white',
                        textDecoration: 'none',
                        '&:hover': {
                          backgroundColor: 'rgba(255, 255, 255, 0.1)',
                        },
                        '&.active': {
                          backgroundColor: 'rgba(255, 193, 7, 0.2)',
                          color: '#FFC107',
                        }
                      }}
                    >
                      <ListItemText
                        primary={link.label}
                        primaryTypographyProps={{
                          fontWeight: link.bold ? 700 : 500,
                          fontSize: '1.1rem'
                        }}
                      />
                    </ListItem>
                  ))}
                </List>
              </Drawer>

              <div className="main-content">
                <Routes>
                  <Route path="/" element={<HomePage />} />
                  <Route path="/map" element={<MapViewer />} />
                  <Route path="/tipg-test" element={<TiPgTestMap />} />
                  <Route path="/reports" element={<Reports />} />
                  <Route path="/reports/station/:stationId" element={<StationReport />} />
                  <Route path="/partners" element={<Partners />} />
                </Routes>
              </div>

              <Footer />
            </div>
          </Router>
        </ThemeProvider>
      </QueryProvider>
    </ErrorBoundary>
  );
};

export default App;
