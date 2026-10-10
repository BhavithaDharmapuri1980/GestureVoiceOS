/**
 * GestureVoice OS - Frontend API Service
 * Interacts with FastAPI backend at http://127.0.0.1:8000
 */

const API_BASE_URL = 'http://127.0.0.1:8000';

export const getVideoFeedUrl = () => `${API_BASE_URL}/api/video_feed`;

export const getWebSocketUrl = () => {
  return `${API_BASE_URL.replace(/^http/, 'ws')}/ws/telemetry`;
};

/**
 * Fetch system and telemetry status
 * GET /api/status
 */
export async function getSystemStatus() {
  const response = await fetch(`${API_BASE_URL}/api/status`, {
    headers: { 'Accept': 'application/json' }
  });
  if (!response.ok) {
    throw new Error(`Status request failed: ${response.status} ${response.statusText}`);
  }
  return await response.json();
}

/**
 * Toggle computer controls on/off
 * POST /api/control/toggle
 */
export async function toggleControl(enabled) {
  const response = await fetch(`${API_BASE_URL}/api/control/toggle`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json'
    },
    body: JSON.stringify({ enabled: Boolean(enabled) })
  });
  if (!response.ok) {
    throw new Error(`Control toggle failed: ${response.status} ${response.statusText}`);
  }
  return await response.json();
}

/**
 * Trigger immediate emergency safe stop
 * POST /api/control/stop
 */
export async function emergencyStop() {
  const response = await fetch(`${API_BASE_URL}/api/control/stop`, {
    method: 'POST',
    headers: { 'Accept': 'application/json' }
  });
  if (!response.ok) {
    throw new Error(`Emergency stop failed: ${response.status} ${response.statusText}`);
  }
  return await response.json();
}

/**
 * Execute a whitelisted voice command
 * POST /api/voice/command
 */
export async function sendVoiceCommand(transcript) {
  const response = await fetch(`${API_BASE_URL}/api/voice/command`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json'
    },
    body: JSON.stringify({ transcript })
  });
  if (!response.ok) {
    throw new Error(`Voice command failed: ${response.status} ${response.statusText}`);
  }
  return await response.json();
}

/**
 * Fetch allowed voice command definitions
 * GET /api/voice/allowed
 */
export async function getAllowedVoiceCommands() {
  const response = await fetch(`${API_BASE_URL}/api/voice/allowed`, {
    headers: { 'Accept': 'application/json' }
  });
  if (!response.ok) {
    throw new Error(`Allowed voice commands request failed: ${response.status}`);
  }
  return await response.json();
}
