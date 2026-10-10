import React from 'react';

export default function Header({ isOnline, controlEnabled, emergencyStopped, cameraConnected, resolution }) {
  return (
    <header className="app-header">
      <div className="brand-section">
        <div className="logo-badge">
          <span>⚡</span>
        </div>
        <div className="brand-text">
          <h1>
            GestureVoice OS
            <span className="team-badge">TEAM NOVATRIX</span>
          </h1>
          <p>Touchless Hand Gesture &amp; Voice Operating System Interface</p>
        </div>
      </div>

      <div className="header-status-group">
        {/* Backend Connectivity Status */}
        <div className="status-pill">
          <span className={`pulse-dot ${isOnline ? 'online' : 'offline'}`} />
          <span>Backend: {isOnline ? 'Connected (8000)' : 'Offline'}</span>
        </div>

        {/* Camera Hardware Status */}
        <div className="status-pill">
          <span className={`pulse-dot ${cameraConnected ? 'online' : 'warning'}`} />
          <span>Camera: {cameraConnected ? 'Active' : 'Standby'}</span>
        </div>

        {/* System Control Status */}
        <div className="status-pill">
          <span className={`pulse-dot ${emergencyStopped ? 'offline' : (controlEnabled ? 'online' : 'warning')}`} />
          <span>
            {emergencyStopped 
              ? 'EMERGENCY STOPPED' 
              : (controlEnabled ? 'Control: ACTIVE' : 'Control: PAUSED')}
          </span>
        </div>

        {/* Screen Resolution */}
        {resolution && (
          <div className="status-pill">
            <span>📺 {resolution.width} × {resolution.height}</span>
          </div>
        )}
      </div>
    </header>
  );
}
