import { Download, X } from 'lucide-react';
import '../styles/app.css';

function UpdateBanner({ version, releaseUrl, onClose }) {
  if (!version) return null;

  return (
    <div className="update-banner">
      <div className="update-content">
        <div className="update-icon">
          <Download size={20} />
        </div>
        <div className="update-text">
          <span className="update-title">New version available: {version}</span>
          <a 
            href={releaseUrl} 
            target="_blank" 
            rel="noopener noreferrer"
            className="update-link"
          >
            Download from GitHub
          </a>
        </div>
      </div>
      <button className="update-close" onClick={onClose} aria-label="Close">
        <X size={18} />
      </button>
    </div>
  );
}

export default UpdateBanner;
