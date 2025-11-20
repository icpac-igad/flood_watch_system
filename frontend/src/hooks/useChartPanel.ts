import { useState, useCallback, useEffect } from 'react';

interface PanelPosition {
  x: number;
  y: number;
}

export const useChartPanel = () => {
  const [panelHeight, setPanelHeight] = useState(380);
  const [panelWidth, setPanelWidth] = useState(600);
  const [isResizing, setIsResizing] = useState(false);
  const [resizeDirection, setResizeDirection] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const [panelPosition, setPanelPosition] = useState<PanelPosition>({ x: 0, y: 0 });
  
  const handleResizeStart = useCallback((direction: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsResizing(true);
    setResizeDirection(direction);
  }, []);

  const handleDragStart = useCallback((e: React.MouseEvent) => {
    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
    setDragOffset({
      x: e.clientX - rect.left,
      y: e.clientY - rect.top
    });
    setIsDragging(true);
  }, []);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (isResizing && resizeDirection) {
        const minWidth = 400;
        const minHeight = 250;
        const maxWidth = window.innerWidth - 100;
        const maxHeight = window.innerHeight - 100;

        if (resizeDirection.includes('right')) {
          const newWidth = Math.max(minWidth, Math.min(maxWidth, e.clientX - panelPosition.x));
          setPanelWidth(newWidth);
        }
        if (resizeDirection.includes('left')) {
          const newWidth = Math.max(minWidth, Math.min(maxWidth, panelWidth + (panelPosition.x - e.clientX)));
          if (newWidth >= minWidth) {
            setPanelPosition(prev => ({ ...prev, x: e.clientX }));
            setPanelWidth(newWidth);
          }
        }
        if (resizeDirection.includes('bottom')) {
          const newHeight = Math.max(minHeight, Math.min(maxHeight, e.clientY - (panelPosition.y || (window.innerHeight - panelHeight))));
          setPanelHeight(newHeight);
        }
        if (resizeDirection.includes('top')) {
          const newHeight = Math.max(minHeight, Math.min(maxHeight, panelHeight + ((panelPosition.y || (window.innerHeight - panelHeight)) - e.clientY)));
          if (newHeight >= minHeight) {
            setPanelPosition(prev => ({ ...prev, y: e.clientY }));
            setPanelHeight(newHeight);
          }
        }
      }

      if (isDragging) {
        setPanelPosition({
          x: Math.max(0, Math.min(window.innerWidth - panelWidth, e.clientX - dragOffset.x)),
          y: Math.max(0, Math.min(window.innerHeight - panelHeight, e.clientY - dragOffset.y))
        });
      }
    };

    const handleMouseUp = () => {
      setIsResizing(false);
      setResizeDirection(null);
      setIsDragging(false);
    };

    if (isResizing || isDragging) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      return () => {
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
      };
    }
  }, [isResizing, isDragging, resizeDirection, panelPosition, panelWidth, panelHeight, dragOffset]);

  return {
    panelHeight,
    panelWidth,
    panelPosition,
    isResizing,
    isDragging,
    handleResizeStart,
    handleDragStart,
    setPanelPosition
  };
};
