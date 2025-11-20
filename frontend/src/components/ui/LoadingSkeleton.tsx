import React from 'react';
import { Skeleton } from '@mui/material';

export const MapSkeleton: React.FC = () => (
  <div style={{ width: '100%', height: '100vh', position: 'relative' }}>
    <Skeleton variant="rectangular" width="100%" height="100%" animation="wave" />
    <div style={{ position: 'absolute', top: 20, left: 20 }}>
      <Skeleton variant="rectangular" width={300} height={600} animation="wave" />
    </div>
  </div>
);

export const ChartSkeleton: React.FC = () => (
  <div style={{ padding: 20 }}>
    <Skeleton variant="text" width="40%" height={40} />
    <Skeleton variant="rectangular" width="100%" height={300} style={{ marginTop: 20 }} animation="wave" />
  </div>
);

export const LayerSkeleton: React.FC = () => (
  <div style={{ padding: 10 }}>
    {[...Array(5)].map((_, i) => (
      <Skeleton key={i} variant="rectangular" width="100%" height={40} style={{ marginBottom: 8 }} animation="wave" />
    ))}
  </div>
);
