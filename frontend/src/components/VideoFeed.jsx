import React, { useState, useEffect } from 'react';
import { getVideoFeedUrl } from '../api';

export default function VideoFeed({ telemetry, isOnline }) {
  const [streamError, setStreamError] = useState(false);
  const [streamKey, setStreamKey] = useState(Date.now());

  // Automatically reset and reload stream when backend status is online
  useEffect(() => {
    if (isOnline) {
      setStreamError(false);
      setStreamKey(Date.now());
    }
  }, [isOnline]);

  const handleReload = () => {
    setStreamError(false);
    setStreamKey(Date.now());
  };

  const handleStreamError = () => {
    setStreamError(true);
    // Auto-retry connection after 2 seconds
    setTimeout(() => {
      setStreamError(false);
      setStreamKey(Date.now());
    }, 2000);
  };

  const gesture = telemetry?.gesture || 'NONE';
  const fps = telemetry?.fps || 0;
  const handsCount = telemetry?.hands_count || 0;
  const action = telemetry?.action || 'idle';

  return (
    <div className="card-panel">
      <div className="card-header">
        <h2 className="card-title">
          <span>📹</span> Live Camera Pipeline &amp; MediaPipe HUD
        </h2>
        <button 
          onClick={handleReload} 
          className="command-chip"
          title="Reload Stream"
        >
          🔄 Refresh Stream
        </button>
      </div>

      <div className="video-feed-wrapper">
        {isOnline && !streamError ? (
          <img
            key={streamKey}
            src={`${getVideoFeedUrl()}?t=${streamKey}`}
            alt="Gesture Live Camera Feed"
            className="video-feed-img"
            onLoad={() => setStreamError(false)}
            onError={handleStreamError}
          />
        ) : (
          <div className="feed-fallback">
            <span className="feed-fallback-icon">📷</span>
            <h3>Camera Feed Connecting / Synchronizing</h3>
            <p>
              {!isOnline 
                ? 'Backend server is offline. Run uvicorn on port 8000.'
                : 'Waiting for camera frame pipeline or auto-reconnecting...'}
            </p>
            <button onClick={handleReload} className="btn btn-secondary" style={{ marginTop: '12px' }}>
              Reconnect Feed
            </button>
          </div>
        )}

        {/* HUD Overlay Badges */}
        {isOnline && !streamError && (
          <div className="feed-hud-overlay">
            <div className="hud-tag">
              FPS: <strong>{fps}</strong> | Hands: <strong>{handsCount}</strong>
            </div>
            <div className={`hud-tag ${gesture !== 'NONE' ? 'active' : ''}`}>
              Gesture: <strong>{gesture}</strong>
            </div>
          </div>
        )}
      </div>

      {/* Real-time Telemetry Bar */}
      <div className="telemetry-grid">
        <div className="telemetry-stat">
          <div className="stat-label">Recognized Gesture</div>
          <div className="stat-value highlight">{gesture}</div>
        </div>
        <div className="telemetry-stat">
          <div className="stat-label">Dispatched Action</div>
          <div className="stat-value">{action}</div>
        </div>
        <div className="telemetry-stat">
          <div className="stat-label">Tracked Hands</div>
          <div className="stat-value">{handsCount}</div>
        </div>
        <div className="telemetry-stat">
          <div className="stat-label">Processing Rate</div>
          <div className="stat-value">{fps} FPS</div>
        </div>
      </div>
    </div>
  );
}
