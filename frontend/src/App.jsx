import React, { useState, useEffect, useCallback, useRef } from 'react';
import Header from './components/Header';
import VideoFeed from './components/VideoFeed';
import ControlPanel from './components/ControlPanel';
import VoiceController from './components/VoiceController';
import ActivityLog from './components/ActivityLog';
import { getSystemStatus, getWebSocketUrl } from './api';

export default function App() {
  const [isOnline, setIsOnline] = useState(false);
  const [controlEnabled, setControlEnabled] = useState(true);
  const [emergencyStopped, setEmergencyStopped] = useState(false);
  const [cameraConnected, setCameraConnected] = useState(false);
  const [resolution, setResolution] = useState(null);
  const [telemetry, setTelemetry] = useState(null);
  const [alert, setAlert] = useState(null);
  const [logs, setLogs] = useState([]);

  const wsRef = useRef(null);
  const pollIntervalRef = useRef(null);

  // Helper to add activity log entries
  const addLog = useCallback((category, title, detail) => {
    const newEntry = {
      id: Date.now() + Math.random(),
      category,
      title,
      detail,
      time: new Date().toLocaleTimeString()
    };
    setLogs((prev) => [newEntry, ...prev.slice(0, 49)]); // keep latest 50
  }, []);

  // Helper to show dismissible alerts
  const showAlert = useCallback((message, type = 'error') => {
    setAlert({ message, type });
  }, []);

  const dismissAlert = () => {
    setAlert(null);
  };

  // Sync state from status response
  const handleStatusUpdate = useCallback((statusData) => {
    setIsOnline(true);
    if (statusData.control_enabled !== undefined) {
      setControlEnabled(statusData.control_enabled);
    }
    if (statusData.emergency_stopped !== undefined) {
      setEmergencyStopped(statusData.emergency_stopped);
    }
    if (statusData.camera_connected !== undefined) {
      setCameraConnected(statusData.camera_connected);
    }
    if (statusData.screen_resolution) {
      setResolution(statusData.screen_resolution);
    }
    if (statusData.latest_telemetry) {
      setTelemetry(statusData.latest_telemetry);
    }
  }, []);

  // Periodic REST poll fallback to ensure robust sync
  const pollStatus = useCallback(async () => {
    try {
      const data = await getSystemStatus();
      handleStatusUpdate(data);
    } catch (err) {
      setIsOnline(false);
    }
  }, [handleStatusUpdate]);

  // Connect WebSocket for live telemetry stream
  useEffect(() => {
    let ws;
    let reconnectTimer;

    const connectWs = () => {
      try {
        ws = new WebSocket(getWebSocketUrl());
        wsRef.current = ws;

        ws.onopen = () => {
          setIsOnline(true);
          addLog('system', 'Telemetry WebSocket Connected', 'Port 8000');
        };

        ws.onmessage = (event) => {
          try {
            const msg = JSON.parse(event.data);
            if (msg.type === 'telemetry' && msg.data) {
              setTelemetry(msg.data);
              if (msg.data.camera_connected !== undefined) {
                setCameraConnected(msg.data.camera_connected);
              }
              if (msg.data.emergency_stopped !== undefined) {
                setEmergencyStopped(msg.data.emergency_stopped);
              }
            } else if (msg.type === 'control_status') {
              if (msg.control_enabled !== undefined) {
                setControlEnabled(msg.control_enabled);
              }
              if (msg.emergency_stopped !== undefined) {
                setEmergencyStopped(msg.emergency_stopped);
              }
            }
          } catch (e) {
            console.error('WS parse error:', e);
          }
        };

        ws.onerror = () => {
          // On error, fallback to REST
        };

        ws.onclose = () => {
          reconnectTimer = setTimeout(connectWs, 3000);
        };
      } catch (err) {
        reconnectTimer = setTimeout(connectWs, 3000);
      }
    };

    connectWs();
    pollStatus();
    pollIntervalRef.current = setInterval(pollStatus, 2000);

    return () => {
      if (ws) ws.close();
      clearTimeout(reconnectTimer);
      clearInterval(pollIntervalRef.current);
    };
  }, [pollStatus, addLog]);

  // Handle control state updates from ControlPanel
  const handleControlStateChange = ({ control_enabled, emergency_stopped }) => {
    setControlEnabled(control_enabled);
    setEmergencyStopped(emergency_stopped);
    if (emergency_stopped) {
      addLog('stop', 'EMERGENCY STOP TRIGGERED', 'All controls safely locked');
      showAlert('Emergency Safe Stop triggered. Controls halted.', 'error');
    } else if (control_enabled) {
      addLog('system', 'Controls Resumed', 'Gesture and voice simulation active');
      showAlert('System controls active.', 'success');
    } else {
      addLog('system', 'Controls Paused', 'Standby mode');
      showAlert('System controls paused.', 'info');
    }
  };

  // Handle voice commands from VoiceController
  const handleVoiceCommand = (transcript, response) => {
    if (response?.success) {
      addLog('voice', `Voice Command: "${transcript}"`, `Action: ${response.action}`);
      showAlert(`Executed voice command: "${transcript}"`, 'success');
      // If voice command toggled stop/start control
      if (response.action === 'stop_control') {
        setControlEnabled(false);
      } else if (response.action === 'start_control') {
        setControlEnabled(true);
        setEmergencyStopped(false);
      }
    } else {
      addLog('voice', `Voice Rejected: "${transcript}"`, response?.error || 'Disallowed');
      showAlert(response?.error || `Command "${transcript}" is not permitted.`, 'error');
    }
  };

  return (
    <div className="app-container">
      {/* Top Header */}
      <Header
        isOnline={isOnline}
        controlEnabled={controlEnabled}
        emergencyStopped={emergencyStopped}
        cameraConnected={cameraConnected}
        resolution={resolution}
      />

      {/* Dismissible Alert Banner */}
      {alert && (
        <div className={`alert-banner ${alert.type}`}>
          <span>{alert.message}</span>
          <button onClick={dismissAlert} className="alert-close" aria-label="Close">
            ✕
          </button>
        </div>
      )}

      {/* Main Grid Section */}
      <main className="main-dashboard-grid">
        {/* Left Column: Live Video Feed & Voice Recognition */}
        <section className="dashboard-column">
          <VideoFeed
            telemetry={telemetry}
            isOnline={isOnline}
          />
          <VoiceController
            onCommandExecuted={handleVoiceCommand}
            onError={(msg) => showAlert(msg, 'error')}
          />
        </section>

        {/* Right Column: Controls, Fail-safe & Activity Logs */}
        <aside className="dashboard-column">
          <ControlPanel
            controlEnabled={controlEnabled}
            emergencyStopped={emergencyStopped}
            onStatusChange={handleControlStateChange}
            onError={(msg) => showAlert(msg, 'error')}
          />
          <ActivityLog
            logs={logs}
            onClear={() => setLogs([])}
          />
        </aside>
      </main>
    </div>
  );
}
