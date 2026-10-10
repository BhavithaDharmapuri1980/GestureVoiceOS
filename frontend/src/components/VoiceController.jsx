import React, { useState, useEffect, useRef } from 'react';
import { sendVoiceCommand, getAllowedVoiceCommands } from '../api';

export default function VoiceController({ onCommandExecuted, onError }) {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [manualText, setManualText] = useState('');
  const [lastResponse, setLastResponse] = useState(null);
  const [allowedCommands, setAllowedCommands] = useState([]);
  const [micSupported, setMicSupported] = useState(true);
  const recognitionRef = useRef(null);

  // Load allowed commands list from backend
  useEffect(() => {
    getAllowedVoiceCommands()
      .then((data) => {
        if (data?.allowed_commands) {
          setAllowedCommands(Object.keys(data.allowed_commands));
        }
      })
      .catch((err) => {
        console.warn('Could not fetch allowed commands list:', err);
        setAllowedCommands([
          'click', 'double click', 'right click', 'scroll up', 
          'scroll down', 'zoom in', 'zoom out', 'open browser', 
          'stop control', 'start control'
        ]);
      });
  }, []);

  // Initialize Web Speech API
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setMicSupported(false);
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-US';

    recognition.onresult = (event) => {
      const recognized = event.results[0][0].transcript;
      setTranscript(recognized);
      handleExecuteCommand(recognized);
    };

    recognition.onerror = (event) => {
      console.error('Speech recognition error:', event.error);
      setIsListening(false);
      if (event.error !== 'no-speech') {
        onError(`Microphone recognition error: ${event.error}`);
      }
    };

    recognition.onend = () => {
      setIsListening(false);
    };

    recognitionRef.current = recognition;
  }, []);

  const toggleListening = () => {
    if (!recognitionRef.current) {
      onError('Browser does not support the Web Speech API. Use the manual input or chips below.');
      return;
    }

    if (isListening) {
      recognitionRef.current.stop();
      setIsListening(false);
    } else {
      setTranscript('');
      setLastResponse(null);
      try {
        recognitionRef.current.start();
        setIsListening(true);
      } catch (err) {
        console.error('Failed to start recognition:', err);
        setIsListening(false);
      }
    }
  };

  const handleExecuteCommand = async (cmdText) => {
    if (!cmdText || !cmdText.trim()) return;
    try {
      const res = await sendVoiceCommand(cmdText.trim());
      setLastResponse(res);
      if (onCommandExecuted) {
        onCommandExecuted(cmdText, res);
      }
      if (!res.success) {
        onError(res.error || 'Voice command was not recognized in safe whitelist.');
      }
    } catch (err) {
      onError(`Voice execution failed: ${err.message}`);
    }
  };

  const handleManualSubmit = (e) => {
    e.preventDefault();
    if (manualText.trim()) {
      setTranscript(manualText);
      handleExecuteCommand(manualText);
      setManualText('');
    }
  };

  return (
    <div className="card-panel">
      <div className="card-header">
        <h2 className="card-title">
          <span>🎙️</span> Browser Voice Controls
        </h2>
        <span className="status-pill">
          {micSupported ? (isListening ? 'LISTENING...' : 'READY') : 'KEYBOARD ONLY'}
        </span>
      </div>

      <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
        Speak natural instructions using your browser microphone or click quick action buttons.
      </p>

      {/* Mic Activation Button */}
      <div className="voice-mic-box">
        <button
          onClick={toggleListening}
          className={`mic-toggle-btn ${isListening ? 'listening' : ''}`}
          title={isListening ? 'Stop listening' : 'Start voice recognition'}
        >
          {isListening ? '⏹️' : '🎙️'}
        </button>
        <span className="mic-status-text">
          {isListening 
            ? 'Listening for command... (speak now)' 
            : 'Click microphone to speak a command'}
        </span>

        {/* Live / Last Transcript Display */}
        <div className="transcript-preview">
          {transcript ? `"${transcript}"` : 'Spoken command will appear here...'}
        </div>

        {/* Execution Response Notice */}
        {lastResponse && (
          <div style={{
            fontSize: '12px',
            fontFamily: 'var(--font-mono)',
            color: lastResponse.success ? 'var(--accent-green)' : 'var(--accent-red)'
          }}>
            {lastResponse.success 
              ? `✓ ${lastResponse.message || 'Executed action: ' + lastResponse.action}` 
              : `✗ ${lastResponse.error || 'Command rejected'}`}
          </div>
        )}
      </div>

      {/* Quick Action Chips */}
      <div>
        <div className="stat-label" style={{ marginBottom: '8px' }}>
          Allowed Safe Whitelist Commands (Click to test):
        </div>
        <div className="commands-chip-grid">
          {allowedCommands.map((cmd) => (
            <button
              key={cmd}
              onClick={() => {
                setTranscript(cmd);
                handleExecuteCommand(cmd);
              }}
              className="command-chip"
            >
              {cmd}
            </button>
          ))}
        </div>
      </div>

      {/* Manual Input Fallback */}
      <form onSubmit={handleManualSubmit} className="manual-input-row">
        <input
          type="text"
          value={manualText}
          onChange={(e) => setManualText(e.target.value)}
          placeholder="Type command (e.g. 'scroll up', 'zoom in')..."
          className="text-input"
        />
        <button type="submit" className="btn btn-secondary" style={{ flex: 'none' }}>
          Execute
        </button>
      </form>
    </div>
  );
}
