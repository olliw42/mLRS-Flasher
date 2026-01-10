import { useState, useEffect, useCallback, useRef } from 'react';
// 2026-01-09

/**
 * custom hook for loading firmware files and metadata
 * encapsulates shared logic used by TxModuleExternal, TxModuleInternal, and Receiver components
 * 
 * @param {string} type - device type ('tx', 'rx', 'txint')
 * @param {string} selectedDevice - currently selected device
 * @param {string} selectedVersion - currently selected version
 * @returns {object} firmware loading state and functions
 */
export function useFirmwareLoader(type, selectedDevice, selectedVersion) {
  const [firmwareFiles, setFirmwareFiles] = useState([]);
  const [selectedFile, setSelectedFile] = useState('');
  const [metadata, setMetadata] = useState(null);
  const [isLoadingFiles, setIsLoadingFiles] = useState(false);
  const [error, setError] = useState(null);
  
  // track mounted state to prevent state updates after unmount
  const isMountedRef = useRef(true);
  
  useEffect(() => {
    isMountedRef.current = true;
    return () => { isMountedRef.current = false; };
  }, []);

  // load firmware files when device or version changes
  const loadFirmwareFiles = useCallback(async () => {
    if (!selectedDevice || !selectedVersion) return;
    
    setIsLoadingFiles(true);
    setError(null);
    
    try {
      const result = await window.api.listFirmware({
        type,
        device: selectedDevice,
        version: selectedVersion,
      });
      
      if (!isMountedRef.current) return;
      
      const files = result.files || [];
      setFirmwareFiles(files);
      
      if (files.length > 0) {
        setSelectedFile(files[0].filename);
      } else {
        setSelectedFile('');
      }
    } catch (err) {
      if (!isMountedRef.current) return;
      console.error('Failed to load firmware files:', err);
      setError('Failed to load firmware list. Please check your connection.');
      setFirmwareFiles([]);
      setSelectedFile('');
    } finally {
      if (isMountedRef.current) {
        setIsLoadingFiles(false);
      }
    }
  }, [type, selectedDevice, selectedVersion]);

  // load metadata when file selection changes
  const loadMetadata = useCallback(async () => {
    if (!selectedDevice || !selectedFile) {
      setMetadata(null);
      return;
    }
    
    try {
      const result = await window.api.getMetadata({
        type,
        device: selectedDevice,
        filename: selectedFile,
      });
      
      if (isMountedRef.current) {
        setMetadata(result);
      }
    } catch (err) {
      if (isMountedRef.current) {
        console.error('Failed to load metadata:', err);
        setMetadata(null);
      }
    }
  }, [type, selectedDevice, selectedFile]);

  // auto-load firmware files when device/version changes
  useEffect(() => {
    loadFirmwareFiles();
  }, [loadFirmwareFiles]);

  // auto-load metadata when file selection changes
  useEffect(() => {
    loadMetadata();
  }, [loadMetadata]);

  return {
    firmwareFiles,
    selectedFile,
    setSelectedFile,
    metadata,
    isLoadingFiles,
    error,
    setError,
    loadFirmwareFiles,
    loadMetadata,
  };
}

/**
 * custom hook for managing serial port selection
 * 
 * @param {boolean} isPaused - if true, auto-refresh is paused (e.g. during flashing)
 * @returns {object} port state and functions
 */
export function useSerialPorts(isPaused = false) {
  const [ports, setPorts] = useState([]);
  const [selectedPort, setSelectedPort] = useState('');
  const [isScanningPorts, setIsScanningPorts] = useState(false);

  // track mounted state to prevent state updates after unmount
  const isMountedRef = useRef(true);
  useEffect(() => {
    isMountedRef.current = true;
    return () => { isMountedRef.current = false; };
  }, []);

  const refreshPorts = useCallback(async (options = {}) => {
    const { silent = false } = options;
    
    if (!silent) setIsScanningPorts(true);
    
    try {
      const result = await window.api.listPorts();
      
      if (!isMountedRef.current) return;
      
      const newPorts = result.ports || [];
      
      // only update if port list actually changed to avoid unnecessary re-renders
      setPorts(prevPorts => {
        if (JSON.stringify(prevPorts) === JSON.stringify(newPorts)) {
          return prevPorts;
        }
        return newPorts;
      });
      
      // if selected port is no longer available, select first available
      setSelectedPort(prevSelected => {
        if (prevSelected && !newPorts.includes(prevSelected)) {
          return newPorts.length > 0 ? newPorts[0] : '';
        } else if (newPorts.length > 0 && !prevSelected) {
          return newPorts[0];
        }
        return prevSelected;
      });
    } catch (err) {
      console.error('Failed to list ports:', err);
    } finally {
      if (isMountedRef.current && !silent) {
        setIsScanningPorts(false);
      }
    }
  }, []);

  // initial port refresh on mount
  useEffect(() => {
    refreshPorts();
  }, [refreshPorts]);

  // auto-refresh interval
  useEffect(() => {
    if (isPaused) return;

    const intervalId = setInterval(() => {
      refreshPorts({ silent: true });
    }, 2000); // refresh every 2 seconds

    return () => clearInterval(intervalId);
  }, [refreshPorts, isPaused]);

  return {
    ports,
    selectedPort,
    setSelectedPort,
    isScanningPorts,
    refreshPorts,
  };
}

/**
 * custom hook for managing default selections
 * sets initial values when data becomes available
 * 
 * @param {Array} items - available items to select from
 * @param {string} currentValue - current selection
 * @param {Function} setValue - setter function
 * @param {Function} [extractValue] - optional function to extract value from item
 */
export function useDefaultSelection(items, currentValue, setValue, extractValue = (item) => item) {
  useEffect(() => {
    if (items.length > 0 && !currentValue) {
      setValue(extractValue(items[0]));
    }
  }, [items, currentValue, setValue, extractValue]);
}
