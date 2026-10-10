import React, { useState } from 'react';
import { toggleControl, emergencyStop } from '../api';

export default function ControlPanel({ controlEnabled, emergencyStopped, onStatusChange, onError }) {
  const [loading, setLoading] = useState(false);

  const handleToggle = async (desiredState) => {
    setLoading(true);
    try {
      const res = await toggleControl(desiredState);
      onStatusChange({
        control_enabled: res.control_enabled,
        emergency_stopped: false
      });
    } catch (err) {
      onError(`Failed to update control state: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleEmergencyStop = async () => {
    setLoading(true);
    try {
      const res = await emergencyStop();
      onStatusChange({
        control_enabled: false,
        emergency_stopped: true
      });
    } catch (err) {
      onError(`Emergency stop failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card-panel">
      <div className="card-header">
        <h2 className="card-title">
          <span>🎮</span> System Controls &amp; Fail-Safe
        </h2>
        <span className={`status-pill ${emergencyStopped ? 'danger' : (controlEnabled ? 'success' : 'warning')}`}>
          {emergencyStopped ? 'HALTED' : (controlEnabled ? 'ENABLED' : 'PAUSED')}
        </span>
      </div>

      <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
        Toggle touchless cursor control or trigger the immediate fail-safe lock to stop simulated mouse events.
      </p>

      <div className="control-buttons-row">
        {/* Toggle Control Button */}
        {controlEnabled && !emergencyStopped ? (
          <button
            onClick={() => handleToggle(false)}
            disabled={loading}
            className="btn btn-warning"
          >
            ⏸️ Pause Control
          </button>
        ) : (
          <button
            onClick={() => handleToggle(true)}
            disabled={loading}
            className="btn btn-primary"
          >
            ▶️ Start Control
          </button>
        )}

        {/* Emergency Stop Button */}
        <button
          onClick={handleEmergencyStop}
          disabled={loading || emergencyStopped}
          className="btn btn-danger"
          title="Halts all mouse and system simulation instantly"
        >
          🛑 EMERGENCY SAFE STOP
        </button>
      </div>

      {emergencyStopped && (
        <div style={{
          padding: '12px 16px',
          background: 'rgba(255, 0, 84, 0.1)',
          border: '1px solid rgba(255, 0, 84, 0.3)',
          borderRadius: '8px',
          fontSize: '13px',
          color: '#ff85a2',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <span>⚠️ Safe Stop engaged. Cursor simulation is locked.</span>
          <button 
            onClick={() => handleToggle(true)} 
            className="command-chip"
            style={{ color: '#fff', borderColor: '#ff0054' }}
          >
            Unlock &amp; Resume
          </button>
        </div>
      )}
    </div>
  );
}
