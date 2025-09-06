// Import necessary dependencies
import React from 'react';
import { BrowserRouter as Router, Routes, Route, NavLink } from 'react-router-dom';
import { Navbar, Container, Nav } from 'react-bootstrap';

// Import component pages
import Home from './components/Home';
import MapViewer from './components/MapViewer';
import Analysis from './components/Analysis';
import Indicators from './components/Indicators';
import About from './components/About';
import Partners from './components/Partners';
import Contact from './components/Contact';

// Import assets and styles
import leftLogo from '@assets/ICPAC_Website_Header_Logo.svg';
import floodWatchLogo from '@assets/flood-watch-banner-transparent.png'; // Import the PNG logo
import 'bootstrap/dist/css/bootstrap.min.css';
import './App.css';

const App = () => {
  return (
    <Router>
      <div className="app-wrapper">
        {/* Navigation Bar */}
        <Navbar 
          className="navbar-custom" 
          expand="lg"
        >
          <Container fluid>
            {/* Brand Logo Section (not a link) */}
            <div className="brand-container">
              <img
                src={floodWatchLogo}
                alt="East Africa Flood Watch"
                className="brand-logo"
              />
            </div>

            {/* Mobile Navigation Toggle Button */}
            <Navbar.Toggle aria-controls="basic-navbar-nav" />
            
            {/* Navigation Links */}
            <Navbar.Collapse id="basic-navbar-nav">
              <Nav className="mx-auto">
                <Nav.Link as={NavLink} to="/" className="nav-link">
                  HOME
                </Nav.Link>
                <Nav.Link 
                  as={NavLink} 
                  to="/map" 
                  className="nav-link fw-bold" 
                >
                  MAPVIEWER
                </Nav.Link>
                <Nav.Link as={NavLink} to="/analysis" className="nav-link">
                  ANALYSIS
                </Nav.Link>
                <Nav.Link as={NavLink} to="/indicators" className="nav-link">
                  FLOOD INDICATORS
                </Nav.Link>
                <Nav.Link as={NavLink} to="/about" className="nav-link">
                  ABOUT  
                </Nav.Link>
                <Nav.Link as={NavLink} to="/partners" className="nav-link">
                  PARTNERS
                </Nav.Link>
                <Nav.Link as={NavLink} to="/contact" className="nav-link">
                  CONTACT US
                </Nav.Link>
              </Nav>
            </Navbar.Collapse>

            {/* ICPAC Logo */}
            <div className="d-flex align-items-center">
              <img
                src={leftLogo}
                alt="ICPAC Logo"
                className="navbar-logo ms-3"
              />
            </div>
          </Container>
        </Navbar>

        {/* Main Content Area */}
        <div className="main-content">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/map" element={<MapViewer />} />
            <Route path="/analysis" element={<Analysis />} />
            <Route path="/indicators" element={<Indicators/>} />
            <Route path="/about" element={<About/>} />
            <Route path="/partners" element={<Partners/>} />
            <Route path="/contact" element={<Contact/>} />
          </Routes>
        </div>

        {/* Footer Section */}
        <footer className="footer">
          <div>© 2025 East Africa Flood Watch | IGAD-ICPAC</div>
        </footer>
      </div>
    </Router>
  );
};

export default App;