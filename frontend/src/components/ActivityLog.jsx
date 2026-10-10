import React from 'react';

export default function ActivityLog({ logs, onClear }) {
  return (
    <div className="card-panel">
      <div className="card-header">
        <h2 className="card-title">
          <span>📜</span> System Activity &amp; Action Log
        </h2>
        {logs.length > 0 && (
          <button onClick={onClear} className="command-chip" style={{ fontSize: '11px' }}>
            Clear
          </button>
        )}
      </div>

      <div className="activity-log-list">
        {logs.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '20px', color: 'var(--text-dim)', fontSize: '13px' }}>
            No actions recorded yet. Trigger a gesture or voice command to view live activity.
          </div>
        ) : (
          logs.map((log) => (
            <div key={log.id} className={`log-item ${log.category || 'gesture'}`}>
              <div>
                <strong>{log.title}</strong>
                {log.detail && <span style={{ marginLeft: '8px', color: 'var(--text-muted)' }}>{log.detail}</span>}
              </div>
              <span className="log-time">{log.time}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
