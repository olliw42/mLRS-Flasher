import { Radio, Cpu, FileCode, Terminal } from 'lucide-react';
import './navigation.css';
import logo from '../assets/logo.png';

function Navigation({ activeTab, onTabChange }) {
  const tabs = [
    { id: 'tx_ext', label: 'Tx Module (External)', icon: <Radio size={18} /> },
    { id: 'receiver', label: 'Receiver', icon: <Cpu size={18} /> },
    { id: 'tx_int', label: 'Tx Module (Internal)', icon: <Radio size={18} /> },
    { id: 'lua', label: 'Lua Script', icon: <FileCode size={18} /> },
  ];

  return (
    <nav className="navigation">
      <div className="nav-header">
        <img
          src={logo}
          alt="mLRS Logo"
          className="nav-logo"
        />
        <h1 className="nav-title">mLRS Flasher</h1>
      </div>

      <div className="nav-tabs">
        {tabs.map(tab => (
          <button
            key={tab.id}
            className={`nav-tab ${activeTab === tab.id ? 'active' : ''}`}
            onClick={() => onTabChange(tab.id)}
          >
            <span className="tab-icon">{tab.icon}</span>
            <span className="tab-label">{tab.label}</span>
            {activeTab === tab.id && <div className="active-glow" />}
          </button>
        ))}
      </div>

      <div className="nav-footer">
        <span className="version">v0.3.0</span>
      </div>
    </nav>
  );
}

export default Navigation;
