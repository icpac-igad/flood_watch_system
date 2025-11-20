import React from 'react';
import { motion } from 'framer-motion';
import { Button, Container, Typography, Box } from '@mui/material';
import { Link } from 'react-router-dom';

export const HomePage: React.FC = () => {
  return (
    <Box
      sx={{
        minHeight: '100vh',
        width: '100vw',
        position: 'relative',
        color: 'white',
        display: 'flex',
        flexDirection: 'column',
        backgroundImage: 'url(/flood-background.png)',
        backgroundSize: 'cover',
        backgroundPosition: 'center',
        backgroundRepeat: 'no-repeat'
      }}
    >
      <Container maxWidth="lg" sx={{ 
        position: 'relative', 
        zIndex: 1,
        flex: 1,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        py: { xs: 10, md: 8 }
      }}>
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
        >
          <Box sx={{ textAlign: 'center' }}>
            <Typography
              variant="h1"
              sx={{
                mb: 6,
                fontWeight: 700,
                fontSize: { xs: '3rem', md: '4.5rem', lg: '6rem' },
                textShadow: '3px 3px 12px rgba(0,0,0,0.9)',
                lineHeight: 1.2,
                color: '#ffffff'
              }}
            >
              East Africa Flood Watch
            </Typography>

            <Button
              component={Link}
              to="/map"
              variant="contained"
              size="large"
              sx={{
                backgroundColor: '#FFC107',
                color: '#000',
                px: 10,
                py: 3,
                fontSize: '1.4rem',
                fontWeight: 700,
                borderRadius: 2,
                boxShadow: '0 8px 20px rgba(0,0,0,0.5)',
                '&:hover': {
                  backgroundColor: '#FFD54F',
                  transform: 'translateY(-4px)',
                  boxShadow: '0 12px 28px rgba(0,0,0,0.6)',
                  transition: 'all 0.3s ease'
                }
              }}
            >
              Explore Map
            </Button>
          </Box>

        </motion.div>
      </Container>
    </Box>
  );
};
