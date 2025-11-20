import React from 'react';
import { Dialog, DialogTitle, DialogContent, DialogActions, Button, IconButton, Box } from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';

interface LayerMetadata {
  title: string;
  description: string;
  details: string[];
  source: string;
}

interface MetadataModalProps {
  show: boolean;
  handleClose: () => void;
  metadata: LayerMetadata | null;
}

export const MetadataModal: React.FC<MetadataModalProps> = ({ show, handleClose, metadata }) => {
  if (!metadata) return null;

  return (
    <Dialog open={show} onClose={handleClose} maxWidth="md" fullWidth>
      <DialogTitle sx={{ bgcolor: '#f8f9fa', color: '#1B6840', fontWeight: 600 }}>
        {metadata.title}
        <IconButton
          aria-label="close"
          onClick={handleClose}
          sx={{ position: 'absolute', right: 8, top: 8, color: '#666' }}
        >
          <CloseIcon />
        </IconButton>
      </DialogTitle>
      <DialogContent sx={{ pt: 2 }}>
        <Box sx={{ mb: 2 }}>
          <p>{metadata.description}</p>
        </Box>
        <Box component="ul" sx={{ mb: 2, pl: 2.5 }}>
          {metadata.details.map((detail, index) => (
            <li key={index} style={{ marginBottom: '8px' }}>{detail}</li>
          ))}
        </Box>
        <p><strong>Source:</strong> {metadata.source}</p>
      </DialogContent>
      <DialogActions sx={{ bgcolor: '#f8f9fa', px: 2, py: 1.5 }}>
        <Button onClick={handleClose} variant="contained" sx={{ bgcolor: '#034930', '&:hover': { bgcolor: '#145432' } }}>
          Close
        </Button>
      </DialogActions>
    </Dialog>
  );
};
