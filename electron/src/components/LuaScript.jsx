import { useState, useEffect } from 'react';
// 2026-01-09
import './panel.css';

function LuaScript({ versions }) {
  const [files, setFiles] = useState([]);
  const [selectedFile, setSelectedFile] = useState('');
  const [isDownloading, setIsDownloading] = useState(false);
  const [error, setError] = useState(null);

  // fetch lua files from main branch on mount
  useEffect(() => {
    const fetchFiles = async () => {
      try {
        const res = await window.api.listFirmware({ 
          type: 'lua', 
          version: 'main' 
        });
        
        const fileList = res.files || [];
        setFiles(fileList);
        
        // default to first file or empty
        if (fileList.length > 0) {
          setSelectedFile(fileList[0].filename);
        } else {
          setSelectedFile('');
        }
      } catch (err) {
        console.error('Failed to fetch Lua files:', err);
      }
    };

    fetchFiles();
  }, []);

  const handleDownload = async () => {
    try {
      const path = await window.api.pickDirectory();
      if (!path) return; // user cancelled

      setIsDownloading(true);
      setError(null);
      
      // trigger download via IPC
      window.api.downloadLua({
        version: 'main',
        output: path,
        filename: selectedFile === 'all' ? null : selectedFile
      });
    } catch (err) {
      console.error('Failed to download Lua scripts:', err);
      setError(`Failed to start download: ${err.message || err}`);
      setIsDownloading(false);
    }
  };

  // listen for completion
  useEffect(() => {
    const cleanup = window.api.onComplete(() => {
      setIsDownloading(false);
    });
    return cleanup;
  }, []);

  return (
    <div className="panel">
      <h2 className="panel-title">Lua Script</h2>
      
      {error && (
        <div className="error-box">
          <strong>❌ Error:</strong> {error}
        </div>
      )}
      
      <div className="form-grid">
        <div className="form-group full-width">
          <label>Lua Script (from Main branch)</label>
          <div className="select-wrapper">
            <select 
              value={selectedFile} 
              onChange={(e) => setSelectedFile(e.target.value)}
              disabled={isDownloading || files.length === 0}
            >
              {files.length > 0 && (
                <option value="all">All Scripts</option>
              )}
              {files.map(f => (
                <option key={f.filename} value={f.filename}>{f.filename}</option>
              ))}
            </select>
          </div>
        </div>
      </div>



      <div className="description-box">
        <p>
          Download the Lua configuration scripts for your radio. 
          These scripts allow you to configure mLRS parameters directly from your radio's interface.
        </p>
        <p>
          After downloading, copy the scripts to your radio's SD card:
        </p>
        <ul>
          <li><strong>EdgeTX/OpenTX:</strong> Copy to <code>/SCRIPTS/TOOLS/</code></li>
        </ul>
      </div>

      <div className="button-row">
        <button 
          className="btn-primary"
          onClick={handleDownload}
          disabled={isDownloading}
        >
          {isDownloading ? 'Downloading...' : selectedFile === 'all' || !selectedFile ? 'Download All Scripts' : 'Download Script'}
        </button>

        {isDownloading && (
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

export default LuaScript;
