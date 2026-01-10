import { useState, useEffect, useCallback } from 'react';
import { useFirmwareLoader, useSerialPorts, useDefaultSelection } from '../hooks/useFirmwareLoader';
import './panel.css';

const SERIAL_PORTS = ['SERIAL1', 'SERIAL2', 'SERIAL3', 'SERIAL4', 'SERIAL5', 'SERIAL6', 'SERIAL7', 'SERIAL8'];

function FirmwareFlasherPanel({
  title,
  targetType,
  versions,
  devices,
  onFlash,
  isFlashing,
  flashTarget,
  progress,
  showSerialX = false,
  allowWirelessBridge = false,
}) {
  const [selectedDevice, setSelectedDevice] = useState('');
  const [selectedVersion, setSelectedVersion] = useState('');
  const [flashMethod, setFlashMethod] = useState('');
  const [serialX, setSerialX] = useState('SERIAL1');

  // use custom hooks for common functionality
  const {
    firmwareFiles,
    selectedFile,
    setSelectedFile,
    metadata,
    isLoadingFiles,
    error,
    setError,
  } = useFirmwareLoader(targetType, selectedDevice, selectedVersion);

  const {
    ports,
    selectedPort,
    setSelectedPort,
    isScanningPorts,
    refreshPorts,
  } = useSerialPorts(isFlashing);

  // set default selections when data loads
  useDefaultSelection(devices, selectedDevice, setSelectedDevice);
  useDefaultSelection(versions, selectedVersion, setSelectedVersion, v => v.version);

  // set default flash method when metadata loads
  useEffect(() => {
    if (metadata?.raw_flashmethod) {
      const methods = metadata.raw_flashmethod.split(',');
      // priorities: stlink, uart, dfu, appassthru
      // this order preference can be tweaked if needed
      if (methods.includes('stlink')) setFlashMethod('stlink');
      else if (methods.includes('uart')) setFlashMethod('uart');
      else if (methods.includes('dfu')) setFlashMethod('dfu');
      else if (methods.includes('appassthru')) setFlashMethod('appassthru');
      else setFlashMethod(methods[0]);
    } else {
      setFlashMethod('default');
    }
  }, [metadata]);

  const handleFlash = useCallback(() => {
    const file = firmwareFiles.find(f => f.filename === selectedFile);
    if (!file) return;

    // Check for port requirement
    // FIX: logic now allows selecting port for appassthru if needed, but appassthru usually needs it passed
    // the previous bug was that we didn't force port selection for appassthru in Python,
    // but the UI needs to let the user select it if the method is UART-based or appassthru
    const needsPort = (flashMethod === 'uart' || flashMethod === 'esptool' || flashMethod === 'appassthru' || metadata?.needsPort);
    
    if (needsPort && !selectedPort) {
      setError('Please select a COM port first.');
      return;
    }

    // clear any previous error before starting
    // clear any previous error before starting
    setError(null);

    // We no longer construct a complex programmer string here.
    // We pass the device and flash method to the backend, which resolves the details.
    
    // special case for appassthru that includes serial port info
    let programmer = 'auto'; // default
    if (flashMethod === 'appassthru') {
       // preserve legacy behavior for appassthru which might expect 'stm32 appassthru serialX'
       // actually, the backend refactor now handles 'serialX' via provided_programmer or separate arg?
       // Let's pass the serial info in the programmer string for now to be safe with the new backend logic
       // which checks provided_programmer for 'serial'
       programmer = `appassthru ${serialX.toLowerCase()}`;
    }

    onFlash({
      type: targetType,
      programmer: programmer, 
      device: selectedDevice,
      flashMethod: flashMethod,
      url: file.url,
      filename: file.filename,
      port: selectedPort || undefined,
      baudrate: (flashMethod === 'uart') ? 115200 : undefined,
      target: targetType === 'rx' ? 'receiver' : 'tx_module',
    });
  }, [firmwareFiles, selectedFile, flashMethod, selectedDevice, selectedPort, serialX, setError, onFlash, targetType]);

  const handleFlashWirelessBridge = useCallback(() => {
    const file = firmwareFiles.find(f => f.filename === selectedFile);
    if (!file) return;

    onFlash({
      type: targetType,
      programmer: 'esp wirelessbridge',
      url: file.url,
      filename: file.filename,
      port: selectedPort || undefined,
      target: 'wireless_bridge',
    });
  }, [firmwareFiles, selectedFile, selectedPort, onFlash, targetType]);

  const isDevVersion = selectedVersion?.includes('dev');

  return (
    <div className="panel">
      <h2 className="panel-title">{title}</h2>
      
      {error && (
        <div className="error-box">
          <strong>❌ Error:</strong> {error}
        </div>
      )}
      
      <div className="form-grid">
        <div className="form-group">
          <label>Device Type</label>
          <div className="select-wrapper">
            <select 
              value={selectedDevice} 
              onChange={(e) => setSelectedDevice(e.target.value)}
              disabled={isFlashing}
            >
              {devices.map(device => (
                <option key={device} value={device}>{device}</option>
              ))}
            </select>
          </div>
        </div>

        <div className="form-group">
          <label>Firmware Version</label>
          <div className="select-wrapper">
            <select 
              value={selectedVersion} 
              onChange={(e) => setSelectedVersion(e.target.value)}
              disabled={isFlashing}
            >
              {versions.map(v => (
                <option key={v.version} value={v.version}>{v.versionStr}</option>
              ))}
            </select>
          </div>
        </div>

        <div className="form-group full-width">
          <label>Firmware File</label>
          <div className="select-wrapper">
            <select 
              value={selectedFile} 
              onChange={(e) => setSelectedFile(e.target.value)}
              disabled={isFlashing || isLoadingFiles}
            >
              {isLoadingFiles ? (
                <option>Loading...</option>
              ) : firmwareFiles.length === 0 ? (
                <option>No files available</option>
              ) : (
                firmwareFiles.map(file => (
                  <option key={file.filename} value={file.filename}>{file.filename}</option>
                ))
              )}
            </select>
          </div>
        </div>

        {/* flash method and serialX row */}
        {metadata?.raw_flashmethod?.includes(',') && (
          <>
             {/* If we are in passthru mode and showing serialX, put them on same row */}
             {(showSerialX && flashMethod === 'appassthru') ? (
                <>
                  <div className="form-group">
                    <label>Flash Method</label>
                    <div className="select-wrapper">
                      <select 
                        value={flashMethod} 
                        onChange={(e) => setFlashMethod(e.target.value)}
                        disabled={isFlashing}
                      >
                        {metadata.raw_flashmethod.split(',').map(m => {
                          let label = m;
                          if (m === 'dfu') label = 'DFU (USB)';
                          if (m === 'stlink') label = 'STLink (SWD)';
                          if (m === 'uart') label = 'SystemBoot (UART)';
                          if (m === 'esptool') label = 'ESPTool (UART)';
                          if (m === 'appassthru') label = 'AP Passthru';
                          return <option key={m} value={m}>{label}</option>;
                        })}
                      </select>
                    </div>
                  </div>
                  
                  <div className="form-group">
                    <label>Passthrough Serial</label>
                    <div className="select-wrapper">
                      <select 
                        value={serialX} 
                        onChange={(e) => setSerialX(e.target.value)}
                        disabled={isFlashing}
                      >
                        {SERIAL_PORTS.map(p => (
                          <option key={p} value={p}>{p}</option>
                        ))}
                      </select>
                    </div>
                  </div>
                </>
             ) : (
                /* Standard full-width flash method if not combined */
                <div className="form-group full-width">
                  <label>Flash Method</label>
                  <div className="select-wrapper">
                    <select 
                      value={flashMethod} 
                      onChange={(e) => setFlashMethod(e.target.value)}
                      disabled={isFlashing}
                    >
                      {metadata.raw_flashmethod.split(',').map(m => {
                        let label = m;
                        if (m === 'dfu') label = 'DFU (USB)';
                        if (m === 'stlink') label = 'STLink (SWD)';
                        if (m === 'uart') label = 'SystemBoot (UART)';
                        if (m === 'esptool') label = 'ESPTool (UART)';
                        if (m === 'appassthru') label = 'AP Passthru';
                        return <option key={m} value={m}>{label}</option>;
                      })}
                    </select>
                  </div>
                </div>
             )}
          </>
        )}

        {/* COM port selection */}
        {/* FIX: Now shown for appassthru as well */}
        {(metadata?.needsPort || flashMethod === 'uart' || flashMethod === 'esptool' || flashMethod === 'appassthru') && (
          <div className="form-group port-group full-width">
            <label>COM Port</label>
            <div className="port-row">
              <div className="select-wrapper">
                <select 
                  value={selectedPort} 
                  onChange={(e) => setSelectedPort(e.target.value)}
                  disabled={isFlashing || isScanningPorts}
                >
                  {isScanningPorts ? (
                    <option>Scanning...</option>
                  ) : ports.length === 0 ? (
                    <option>No ports found</option>
                  ) : (
                    ports.map(port => (
                      <option key={port} value={port}>{port}</option>
                    ))
                  )}
                </select>
              </div>
              <button 
                className="btn-secondary" 
                onClick={refreshPorts}
                disabled={isFlashing || isScanningPorts}
              >
                {isScanningPorts ? 'Refreshing...' : 'Refresh'}
              </button>
            </div>
          </div>
        )}
      </div>

      {isDevVersion && (
        <div className="warning-box">
          <strong>⚠️ Warning:</strong> You are about to flash a 'dev' firmware version.
          Please ensure you understand the risks involved.
        </div>
      )}

      {metadata?.description && (
        <div className="description-box">
          <pre>{metadata.description}</pre>
        </div>
      )}

      <div className="button-row">
        <button 
          className="btn-primary btn-flash"
          onClick={handleFlash}
          disabled={isFlashing || !selectedFile || firmwareFiles.length === 0 || isLoadingFiles}
        >
          {isFlashing && (flashTarget === (targetType === 'rx' ? 'receiver' : 'tx_module')) ? 
            (progress > 0 ? `Flashing... ${progress}%` : 'Flashing...') : 
            (targetType === 'rx' ? 'Flash Receiver' : 'Flash Tx Module')}
        </button>

        {allowWirelessBridge && metadata?.hasWirelessBridge && (
           <button 
             className="btn-primary btn-flash"
             onClick={handleFlashWirelessBridge}
             disabled={isFlashing || !selectedFile || firmwareFiles.length === 0}
           >
             {isFlashing && flashTarget === 'wireless_bridge' ? (progress > 0 ? `Flashing... ${progress}%` : 'Flashing...') : 'Flash Wireless Bridge'}
           </button>
        )}

        {isFlashing && (
          <button 
            className="btn-secondary btn-cancel"
            onClick={() => window.api.cancelPython()}
          >
            Cancel
          </button>
        )}
      </div>
    </div>
  );
}

export default FirmwareFlasherPanel;
