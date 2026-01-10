import './console.css';
// 2026-01-09
import { useRef, useEffect, useState } from 'react';

function Console({ logs, onClear }) {
  const consoleRef = useRef(null);
  const contentRef = useRef(null);
  const [isFlex, setIsFlex] = useState(true); // Default to filling space
  const [height, setHeight] = useState(181);  // Fallback fixed height
  const [isResizing, setIsResizing] = useState(false);

  // auto-scroll to bottom on new logs
  useEffect(() => {
    if (contentRef.current) {
      contentRef.current.scrollTop = contentRef.current.scrollHeight;
    }
  }, [logs]);

  // handle resize logic
  useEffect(() => {
    const handleMouseMove = (e) => {
      if (!isResizing) return;
      
      const newHeight = window.innerHeight - e.clientY;
      const clampedHeight = Math.max(80, Math.min(newHeight, window.innerHeight - 100));
      
      // Calculate flex basis roughly or just switch to fixed height
      setHeight(clampedHeight);
    };

    const handleMouseUp = () => {
      setIsResizing(false);
      document.body.style.cursor = 'default';
    };

    if (isResizing) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = 'row-resize';
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = 'default';
    };
  }, [isResizing]);

  const startResizing = (e) => {
    e.preventDefault();
    setIsResizing(true);
    setIsFlex(false); // Switch to fixed height mode on user interaction
    
    // Set initial custom height to current computed height to prevent jump
    if (consoleRef.current) {
      setHeight(consoleRef.current.offsetHeight);
    }
  };

  const getLogClass = (type) => {
    switch (type) {
      case 'error': return 'log-error';
      case 'success': return 'log-success';
      case 'warning': return 'log-warning';
      case 'info': return 'log-info';
      case 'stderr': return 'log-stderr';
      default: return 'log-default';
    }
  };

  return (
    <div 
      className="console" 
      ref={consoleRef} 
      style={!isFlex ? { height: `${height}px`, flex: '0 0 auto' } : {}}
    >
      <div 
        className={`resize-handle ${isResizing ? 'resizing' : ''}`}
        onMouseDown={startResizing}
        title="Drag to resize"
      />
      <div className="console-header">
        <span>Console Output</span>
        <button className="console-clear" onClick={onClear}>Clear</button>
      </div>
      <div className="console-content" ref={contentRef}>
        {logs.map((log, index) => (
          <div key={index} className={`log-entry ${getLogClass(log.type)}`}>
            <span className="log-time">{log.timestamp}</span>
            <span className="log-message">{log.message}</span>
          </div>
        ))}
        {logs.length === 0 && (
          <div className="log-empty">Console output will appear here...</div>
        )}
      </div>
    </div>
  );
}

export default Console;
