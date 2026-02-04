import { useState, useRef, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { RealtimeVoiceService } from './services/realtimeVoice';
import { api } from './api';
import type { Task } from './api';

export function Voice() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [listening, setListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [response, setResponse] = useState('');
  const [error, setError] = useState('');
  const [taskResult, setTaskResult] = useState<{ message: string; task?: Task; tasks?: Task[] } | null>(null);
  const [apiKey, setApiKey] = useState('');
  const [model, setModel] = useState('gpt-4o-realtime-preview-2024-10-01');
  const [useAzure, setUseAzure] = useState(false);
  const [azureEndpoint, setAzureEndpoint] = useState('');
  const [deployment, setDeployment] = useState('gpt-4o-realtime-preview');
  const [gmailConnected, setGmailConnected] = useState(false);
  const [connectingGmail, setConnectingGmail] = useState(false);
  const voiceServiceRef = useRef<RealtimeVoiceService | null>(null);

  // Load API key and Azure settings from localStorage (no hardcoded secrets)
  useEffect(() => {
    const savedKey = localStorage.getItem('openai_api_key');
    if (savedKey) setApiKey(savedKey);

    const savedEndpoint = localStorage.getItem('azure_realtime_endpoint');
    if (savedEndpoint) setAzureEndpoint(savedEndpoint);
    const savedDeployment = localStorage.getItem('azure_realtime_deployment');
    if (savedDeployment) setDeployment(savedDeployment);
    const savedUseAzure = localStorage.getItem('voice_use_azure');
    if (savedUseAzure === '1') {
      setUseAzure(true);
    } else if (savedUseAzure === null) {
      // Default to Azure if not set
      setUseAzure(true);
      localStorage.setItem('voice_use_azure', '1');
    }
  }, []);

  const handleTranscript = (text: string) => {
    setTranscript(text);
    setError('');
  };

  const handleResponse = (text: string, isDelta: boolean = false) => {
    if (isDelta) {
      // Append delta text
      setResponse(prev => prev + text);
    } else {
      // Replace with new complete response
      setResponse(text);
    }
  };

  const handleError = (errorMsg: string) => {
    setError(errorMsg);
    setListening(false);
  };

  const handleTaskExecuted = (result: any) => {
    setTaskResult(result);
    // Don't clear response - let it accumulate
  };

  const startListening = async () => {
    if (!apiKey) {
      const key = prompt('Enter your OpenAI API key:');
      if (!key) {
        setError('API key is required');
        return;
      }
      setApiKey(key);
      localStorage.setItem('openai_api_key', key);
    }

    setError('');
    setTranscript('');
    setResponse('');
    setTaskResult(null);

    const service = new RealtimeVoiceService(
      handleTranscript,
      handleResponse,
      handleError,
      handleTaskExecuted
    );

    voiceServiceRef.current = service;

    const options = useAzure && azureEndpoint && deployment
      ? { azureEndpoint, deployment }
      : { model };
    const started = await service.start(apiKey, options);
    if (started) {
      setListening(true);
    }
  };

  const stopListening = () => {
    if (voiceServiceRef.current) {
      voiceServiceRef.current.stop();
      voiceServiceRef.current = null;
    }
    setListening(false);
    setTranscript('');
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (voiceServiceRef.current) {
        voiceServiceRef.current.stop();
      }
    };
  }, []);

  return (
    <div className="page voice-page">
      <header className="page-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '1rem', flexWrap: 'wrap' }}>
          <div>
            <h1>Voice Assistant</h1>
            <p className="page-subtitle">Real-time voice interaction with task execution and email</p>
          </div>
          {!gmailConnected && (
            <button
              type="button"
              className="btn"
              onClick={async () => {
                setConnectingGmail(true);
                try {
                  const { data, status } = await api.gmail.authorize();
                  if (status === 200 && data.auth_url) {
                    window.location.href = data.auth_url;
                  }
                } catch (error) {
                  console.error('Failed to initiate Gmail connection:', error);
                  setConnectingGmail(false);
                }
              }}
              disabled={connectingGmail}
            >
              {connectingGmail ? 'Connecting...' : 'Connect Gmail'}
            </button>
          )}
        </div>
      </header>

      {gmailConnected && (
        <div style={{
          padding: '1rem',
          background: 'var(--bg-card)',
          border: '1.5px solid var(--border)',
          borderRadius: 'var(--radius)',
          marginBottom: '1.5rem',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <div>
            <strong style={{ color: '#22c55e' }}>✓ Gmail Connected</strong>
            <p className="muted" style={{ margin: '0.25rem 0 0', fontSize: '0.85rem' }}>
              You can send emails via voice commands
            </p>
          </div>
        </div>
      )}

      <div style={{
        padding: '1.5rem',
        background: 'var(--bg-card)',
        border: '1.5px solid var(--border)',
        borderRadius: 'var(--radius)',
        marginBottom: '1.5rem'
      }}>
        <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem', fontWeight: 500 }}>
          <input
            type="checkbox"
            checked={useAzure}
            onChange={(e) => {
              setUseAzure(e.target.checked);
              localStorage.setItem('voice_use_azure', e.target.checked ? '1' : '0');
            }}
          />
          Use Azure OpenAI Realtime
        </label>
        {useAzure ? (
          <>
            <label style={{ display: 'block', marginBottom: '0.75rem', fontWeight: 500 }}>
              Azure Realtime endpoint URL:
            </label>
            <input
              type="url"
              value={azureEndpoint}
              onChange={(e) => {
                setAzureEndpoint(e.target.value);
                localStorage.setItem('azure_realtime_endpoint', e.target.value);
              }}
              placeholder="https://....openai.azure.com/openai/realtime?api-version=2024-10-01-preview&deployment=..."
              style={{
                width: '100%',
                padding: '0.75rem',
                border: '1.5px solid var(--border)',
                borderRadius: 'var(--radius-sm)',
                background: 'var(--bg)',
                color: 'var(--text)',
                marginBottom: '0.75rem'
              }}
            />
            <label style={{ display: 'block', marginBottom: '0.75rem', fontWeight: 500 }}>
              Deployment name:
            </label>
            <input
              type="text"
              value={deployment}
              onChange={(e) => {
                setDeployment(e.target.value);
                localStorage.setItem('azure_realtime_deployment', e.target.value);
              }}
              placeholder="gpt-4o-realtime-preview"
              style={{
                width: '100%',
                padding: '0.75rem',
                border: '1.5px solid var(--border)',
                borderRadius: 'var(--radius-sm)',
                background: 'var(--bg)',
                color: 'var(--text)',
                marginBottom: '0.75rem'
              }}
            />
          </>
        ) : (
          <>
            <label style={{ display: 'block', marginBottom: '0.75rem', fontWeight: 500 }}>
              OpenAI model:
            </label>
            <input
              type="text"
              value={model}
              onChange={(e) => setModel(e.target.value)}
              placeholder="gpt-4o-realtime-preview-2024-10-01"
              style={{
                width: '100%',
                padding: '0.75rem',
                border: '1.5px solid var(--border)',
                borderRadius: 'var(--radius-sm)',
                background: 'var(--bg)',
                color: 'var(--text)',
                marginBottom: '0.75rem'
              }}
            />
          </>
        )}
        <label style={{ display: 'block', marginBottom: '0.75rem', fontWeight: 500 }}>
          {useAzure ? 'Azure API Key:' : 'OpenAI API Key:'}
        </label>
        <input
          type="password"
          value={apiKey}
          onChange={(e) => {
            setApiKey(e.target.value);
            localStorage.setItem('openai_api_key', e.target.value);
          }}
          placeholder={useAzure ? 'Your Azure API key' : 'sk-...'}
          style={{
            width: '100%',
            padding: '0.75rem',
            border: '1.5px solid var(--border)',
            borderRadius: 'var(--radius-sm)',
            background: 'var(--bg)',
            color: 'var(--text)',
            marginBottom: '0.5rem'
          }}
        />
        <p className="muted" style={{ fontSize: '0.85rem', margin: 0 }}>
          Your API key is stored locally and never sent to our servers.
        </p>
      </div>

      <div className="voice-card">
        <div className={`voice-circle ${listening ? 'listening' : ''}`}>
          <button
            type="button"
            className="voice-btn"
            onClick={listening ? stopListening : startListening}
            disabled={(!apiKey || (useAzure && (!azureEndpoint || !deployment))) && !listening}
            aria-label={listening ? 'Stop listening' : 'Start listening'}
          >
            {listening ? (
              <>
                <span style={{ fontSize: '2rem', display: 'block', marginBottom: '0.5rem' }}>⏹</span>
                <span>Stop</span>
              </>
            ) : (
              <>
                <span style={{ fontSize: '2rem', display: 'block', marginBottom: '0.5rem' }}>🎤</span>
                <span>Start</span>
              </>
            )}
          </button>
        </div>

        {transcript && (
          <div className="voice-transcript">
            <strong style={{ color: '#c4c4d0', display: 'block', marginBottom: '0.5rem' }}>You said:</strong>
            {transcript}
          </div>
        )}

        {response && (
          <div className="voice-transcript" style={{ marginTop: '1rem', background: 'rgba(99, 102, 241, 0.1)' }}>
            <strong style={{ color: '#c4c4d0', display: 'block', marginBottom: '0.5rem' }}>Assistant:</strong>
            {response}
          </div>
        )}

        {error && <p className="voice-error">{error}</p>}

        {taskResult && (
          <div className="voice-result">
            <p className="voice-message">✓ {taskResult.message}</p>
            {taskResult.task && (
              <div style={{
                padding: '1rem',
                background: 'var(--bg)',
                borderRadius: 'var(--radius-sm)',
                marginTop: '0.75rem'
              }}>
                <strong>Task:</strong> {taskResult.task.title}
                <span className="task-badge" style={{ marginLeft: '0.5rem' }}>
                  {taskResult.task.status}
                </span>
              </div>
            )}
            {taskResult.tasks && taskResult.tasks.length > 0 && (
              <ul className="voice-task-list">
                {taskResult.tasks.map((t) => (
                  <li key={t.id} style={{
                    padding: '0.75rem',
                    background: 'var(--bg)',
                    borderRadius: 'var(--radius-sm)',
                    marginBottom: '0.5rem',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center'
                  }}>
                    <span>{t.title}</span>
                    <span className="task-badge">{t.status}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>

      <div className="voice-hint">
        <strong>Try saying:</strong>
        <ul style={{ marginTop: '0.75rem', paddingLeft: '1.5rem', listStyle: 'disc' }}>
          <li>&quot;Create a task for Caleb: review the report&quot;</li>
          <li>&quot;Mark task 5 as completed&quot;</li>
          <li>&quot;What tasks are due today?&quot;</li>
          <li>&quot;Show me my task completion rate&quot;</li>
          <li>&quot;Schedule a meeting with Scott tomorrow at 2pm&quot;</li>
          {gmailConnected && (
            <>
              <li>&quot;Send email to john@example.com subject Meeting reminder body Don't forget our meeting tomorrow&quot;</li>
              <li>&quot;Email Caleb about the project update&quot;</li>
            </>
          )}
        </ul>
      </div>
    </div>
  );
}
