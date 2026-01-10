import { useState, useEffect, useCallback, useRef } from 'react';
import Navigation from './components/Navigation';
import TxModuleExternal from './components/TxModuleExternal';
import Receiver from './components/Receiver';
import TxModuleInternal from './components/TxModuleInternal';
import LuaScript from './components/LuaScript';
import Console from './components/Console';
import './styles/app.css';

function App() {
  const [activeTab, setActiveTab] = useState('tx_ext');
  const [logs, setLogs] = useState([]);
  const [versions, setVersions] = useState([]);
  const [devices, setDevices] = useState({ tx: [], rx: [], txint: [] });
  const [isLoading, setIsLoading] = useState(true);
  const [isFlashing, setIsFlashing] = useState(false);
  const [flashTarget, setFlashTarget] = useState(null);
  const [progress, setProgress] = useState(0);

  const hasLoaded = useRef(false);

  // load initial data on mount
  useEffect(() => {
    async function loadInitialData() {
      if (hasLoaded.current) return;
      hasLoaded.current = true;

      try {
        addLog({ type: 'info', message: 'Downloading metadata from GitHub...' });
        
        const versionsResult = await window.api.listVersions();
        const loadedVersions = versionsResult.versions || [];
        setVersions(loadedVersions);
        
        const [txDevices, rxDevices, txintDevices] = await Promise.all([
          window.api.listDevices('tx'),
          window.api.listDevices('rx'),
          window.api.listDevices('txint'),
        ]);
        
        setDevices({
          tx: txDevices.devices || [],
          rx: rxDevices.devices || [],
          txint: txintDevices.devices || [],
        });
        
        if (loadedVersions.length === 0) {
          addLog({ type: 'error', message: 'No firmware versions found. GitHub API may be rate-limited.' });
        } else {
          addLog({ type: 'info', message: 'Metadata loaded successfully' });
        }
      } catch (err) {
        addLog({ type: 'error', message: `Failed to load metadata: ${err.message}` });
      } finally {
        setIsLoading(false);
      }
    }
    
    loadInitialData();
  }, []);

  // listen for python output
  useEffect(() => {
    const cleanup = window.api.onOutput((data) => {
      if (data.type === 'progress') {
        setProgress(data.percent);
      } else {
        addLog(data);
      }
    });
    return cleanup;
  }, []);

  // listen for command completion
  useEffect(() => {
    const cleanup = window.api.onComplete((data) => {
      setIsFlashing(false);
      setFlashTarget(null);
      if (data.code === 0) {
        addLog({ type: 'success', message: 'Operation completed successfully!' });
      } else if (data.code === null || data.code === 'SIGTERM' || data.code === 137) {
        addLog({ type: 'warning', message: 'Operation cancelled by user' });
      } else {
        addLog({ type: 'error', message: `Operation failed with code ${data.code}` });
      }
    });
    return cleanup;
  }, []);

  const addLog = useCallback((entry) => {
    const timestamp = new Date().toLocaleTimeString();
    setLogs(prev => [...prev.slice(-200), { ...entry, timestamp }]); // keep last 200 entries
  }, []);

  const clearLogs = useCallback(() => {
    setLogs([]);
  }, []);

  const handleFlash = useCallback((options) => {
    setIsFlashing(true);
    setFlashTarget(options.target || null);
    setProgress(0);
    addLog({ type: 'info', message: `Starting flash: ${options.filename}` });
    window.api.flash(options);
  }, [addLog]);

  const renderContent = () => {
    if (isLoading) {
      return (
        <div className="loading">
          <div className="spinner"></div>
          <p>Loading metadata from GitHub...</p>
        </div>
      );
    }

    switch (activeTab) {
      case 'tx_ext':
        return (
          <TxModuleExternal 
            versions={versions} 
            devices={devices.tx} 
            onFlash={handleFlash}
            isFlashing={isFlashing}
            flashTarget={flashTarget}
            progress={progress}
          />
        );
      case 'receiver':
        return (
          <Receiver 
            versions={versions} 
            devices={devices.rx} 
            onFlash={handleFlash}
            isFlashing={isFlashing}
            flashTarget={flashTarget}
            progress={progress}
          />
        );
      case 'tx_int':
        return (
          <TxModuleInternal 
            versions={versions} 
            devices={devices.txint} 
            onFlash={handleFlash}
            isFlashing={isFlashing}
            flashTarget={flashTarget}
            progress={progress}
          />
        );
      case 'lua':
        return (
          <LuaScript 
            versions={versions}
          />
        );
      default:
        return null;
    }
  };

  return (
    <div className="app">
      <Navigation activeTab={activeTab} onTabChange={setActiveTab} />
      <div className="main-content">
        <main className="content">
          {renderContent()}
        </main>
        <Console logs={logs} onClear={clearLogs} />
      </div>
    </div>
  );
}

export default App;
