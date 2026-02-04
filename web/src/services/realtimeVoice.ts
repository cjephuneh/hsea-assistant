import { LowLevelRTClient } from 'rt-client';
import type { SessionUpdateMessage, Voice } from 'rt-client';
import { api } from '../api';

export class RealtimeVoiceService {
  private client: LowLevelRTClient | null = null;
  private audioContext: AudioContext | null = null;
  private mediaStream: MediaStream | null = null;
  private audioPlayer: AudioWorkletNode | null = null;
  private playerContext: AudioContext | null = null;
  private recordingActive = false;
  private audioBuffer: Uint8Array = new Uint8Array();
  private workletNode: AudioWorkletNode | null = null;
  private connectionOpen = false;
  private messageHandlerRunning = false;
  private shouldStop = false;

  private onTranscript: ((text: string) => void) | null = null;
  private onResponse: ((text: string, isDelta?: boolean) => void) | null = null;
  private onError: ((error: string) => void) | null = null;
  private onTaskExecuted: ((result: any) => void) | null = null;
  private currentResponse: string = '';

  constructor(
    onTranscript?: (text: string) => void,
    onResponse?: (text: string, isDelta?: boolean) => void,
    onError?: (error: string) => void,
    onTaskExecuted?: (result: any) => void
  ) {
    this.onTranscript = onTranscript || null;
    this.onResponse = onResponse || null;
    this.onError = onError || null;
    this.onTaskExecuted = onTaskExecuted || null;
    this.currentResponse = '';
  }

  async start(
    apiKey: string,
    options: {
      model?: string;
      azureEndpoint?: string;
      deployment?: string;
    } = {}
  ) {
    // Reset stop flag when starting
    this.shouldStop = false;
    const { model = 'gpt-4o-realtime-preview-2024-10-01', azureEndpoint, deployment } = options;
    try {
      // Initialize Realtime API client (Azure or OpenAI)
      if (azureEndpoint && deployment) {
        const url = new URL(azureEndpoint);
        if (url.protocol === 'https:') url.protocol = 'wss:';
        else if (url.protocol === 'http:') url.protocol = 'ws:';
        this.client = new LowLevelRTClient(url, { key: apiKey }, { deployment });
      } else {
        this.client = new LowLevelRTClient({ key: apiKey }, { model });
      }

      // Create session config with system instructions for task execution
      const config: SessionUpdateMessage = {
        type: 'session.update',
        session: {
          turn_detection: {
            type: 'server_vad',
          },
          input_audio_transcription: {
            model: 'whisper-1',
            language: 'en',  // Force English only
          },
          instructions: `You are HSEA Assistant, a helpful voice assistant for task management and communication. 

IMPORTANT: When the user asks about tasks, meetings, or any data, you MUST use ONLY the actual data returned from the backend commands. NEVER make up or invent tasks, meetings, or data. If no data is returned, say so honestly.

You can help users with comprehensive task management:
- CREATE tasks: "Create a task for [name] to [description]" or "Add a task for Caleb to review the report"
- VIEW tasks: "What tasks do I have?", "Show me my tasks", "List my pending tasks", "What tasks are completed?"
- UPDATE task status: "Mark task 5 as completed", "Start task 3", "Move task 2 to in progress", "Set task Review report as pending"
- DELETE tasks: "Delete task 5", "Remove task Review report", "Cancel task 3"
- MOVE tasks between statuses: "Move task 5 from pending to completed", "Change task 3 to in progress"
- Check meetings: "What meetings do I have?" or "Show me my meetings"
- Schedule meetings: "Schedule a meeting with [name] tomorrow at 2pm"
- Get reports: "Show me my task completion rate"
- Send emails: "Send email to [email] subject [subject] body [message]" or "Email [name] about [topic]"

When the user asks about their tasks or meetings, wait for the backend to return the actual data, then read it back to them accurately. Do not invent or make up information. Be conversational and helpful, but always truthful about what data exists.

For task operations, you can reference tasks by number (e.g., "task 5") or by title (e.g., "task Review report"). Always confirm actions clearly.`,
          temperature: 0.8,
          voice: 'alloy' as Voice,
        },
      };

      // Send config immediately - this establishes the WebSocket connection
      // The rt-client library handles connection establishment when send() is called
      try {
        await this.client.send(config);
        // Mark as open optimistically - will be confirmed by session.created message
        this.connectionOpen = true;
      } catch (error) {
        // If send fails, wait briefly and retry once
        await new Promise(resolve => setTimeout(resolve, 300));
        try {
          await this.client.send(config);
          this.connectionOpen = true;
        } catch (retryError) {
          this.connectionOpen = false;
          throw new Error('Failed to send session config: ' + (retryError instanceof Error ? retryError.message : String(retryError)));
        }
      }

      // Start message handler AFTER sending config
      // This ensures we're listening for session.created confirmation
      this.messageHandlerRunning = true;
      const messageHandlerPromise = this.handleMessages();

      // Setup audio after connection is established
      await this.setupAudio();

      // Message handler runs in background
      messageHandlerPromise.catch(err => {
        // Only report error if we're not intentionally stopping
        if (!this.shouldStop) {
          console.error('Message handler error:', err);
          const errorMsg = err instanceof Error ? err.message : String(err);
          
          // Check if this is a recoverable error
          const recoverableErrors = ['network', 'timeout', 'temporary', 'closed'];
          const isRecoverable = recoverableErrors.some(e => errorMsg.toLowerCase().includes(e));
          
          if (!isRecoverable) {
            this.connectionOpen = false;
            this.messageHandlerRunning = false;
            this.recordingActive = false;
            this.onError?.('Connection error. Please try again.');
          } else {
            // For recoverable errors, try to reconnect
            this.connectionOpen = false;
            console.log('Connection temporarily closed, will attempt to reconnect');
          }
        }
      });

      return true;
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : 'Failed to start voice assistant';
      this.onError?.(errorMsg);
      return false;
    }
  }

  private async setupAudio() {
    try {
      // Setup audio recording
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      this.mediaStream = stream;

      // Keep at 24kHz for Realtime API compatibility, but optimize for quality
      this.audioContext = new AudioContext({ 
        sampleRate: 24000,  // Must be 24kHz for Realtime API
        latencyHint: 'interactive'  // Lower latency
      });
      await this.audioContext.audioWorklet.addModule('/audio-worklet-processor.js');

      const source = this.audioContext.createMediaStreamSource(stream);
      // Create worklet node with larger buffer to reduce crackling
      this.workletNode = new AudioWorkletNode(this.audioContext, 'audio-worklet-processor', {
        processorOptions: {
          bufferSize: 4096  // Larger buffer to reduce audio artifacts
        }
      });

      this.workletNode.port.onmessage = (event) => {
        if (this.recordingActive && this.client && event.data?.buffer) {
          this.processAudioBuffer(event.data.buffer);
        }
      };

      source.connect(this.workletNode);
      this.recordingActive = true;

      // Setup audio playback with better buffer handling to reduce crackling
      this.playerContext = new AudioContext({ 
        sampleRate: 24000,  // Keep at 24kHz for Realtime API compatibility
        latencyHint: 'playback'  // Optimize for playback
      });
      await this.playerContext.audioWorklet.addModule('/playback-worklet.js');
      this.audioPlayer = new AudioWorkletNode(this.playerContext, 'playback-worklet', {
        numberOfInputs: 0,
        numberOfOutputs: 1,
        processorOptions: {
          bufferSize: 4096  // Larger buffer to reduce crackling
        }
      });
      
      // Connect with gain node to smooth audio
      const gainNode = this.playerContext.createGain();
      gainNode.gain.value = 1.0;
      this.audioPlayer.connect(gainNode);
      gainNode.connect(this.playerContext.destination);
      
      // Resume audio context if suspended (required by some browsers)
      if (this.playerContext.state === 'suspended') {
        await this.playerContext.resume();
      }
      
      // Also resume recording context
      if (this.audioContext.state === 'suspended') {
        await this.audioContext.resume();
      }
    } catch (error) {
      console.error('Audio setup error:', error);
      this.onError?.('Failed to setup audio. Please check microphone permissions.');
      throw error;
    }
  }

  private processAudioBuffer(buffer: ArrayBuffer) {
    // Only process if connection is open and recording is active
    // Keep connection alive even if temporarily closed - don't stop recording
    if (!this.client || !this.recordingActive) {
      return;
    }
    
    // If connection is temporarily closed, wait a bit but don't stop recording
    if (!this.connectionOpen) {
      // Connection might be re-establishing, don't process audio yet
      return;
    }

    const uint8Array = new Uint8Array(buffer);
    const newBuffer = new Uint8Array(this.audioBuffer.length + uint8Array.length);
    newBuffer.set(this.audioBuffer);
    newBuffer.set(uint8Array, this.audioBuffer.length);
    this.audioBuffer = newBuffer;

    // Send chunks of 4800 bytes (200ms at 24kHz)
    // Use consistent chunk size to reduce audio artifacts
    const chunkSize = 4800;
    if (this.audioBuffer.length >= chunkSize && this.client && this.connectionOpen) {
      const toSend = this.audioBuffer.slice(0, chunkSize);
      this.audioBuffer = this.audioBuffer.slice(chunkSize);

      try {
        const base64 = btoa(String.fromCharCode(...toSend));
        // Send audio - catch and suppress socket errors silently
        this.client.send({
          type: 'input_audio_buffer.append',
          audio: base64,
        }).catch((error) => {
          // Silently handle socket errors - connection might be temporarily closed
          const errorMsg = error instanceof Error ? error.message : String(error);
          if (errorMsg.includes('Socket is not open') || errorMsg.includes('not open')) {
            // Mark connection as closed but keep recording active
            // The message handler will handle reconnection
            this.connectionOpen = false;
            // Don't stop recording - buffer audio until connection re-establishes
          }
        });
      } catch (error) {
        // Handle encoding errors - should be rare
        this.connectionOpen = false;
        this.recordingActive = false;
      }
    }
  }

  private async handleMessages() {
    if (!this.client) return;

    try {
      for await (const message of this.client.messages()) {
        // Mark connection as open when we receive messages
        this.connectionOpen = true;

        try {
          switch (message.type) {
          case 'session.created':
            // Connection confirmed - mark as open
            this.connectionOpen = true;
            this.currentResponse = '';
            // Don't send initial message - let AI handle it naturally
            break;

          case 'response.audio_transcript.delta':
            if ('delta' in message) {
              this.currentResponse += message.delta;
              // Send delta to response handler for display
              this.onResponse?.(message.delta, true);
            }
            break;
          
          case 'response.audio_transcript.done':
            // Don't clear response here - let it accumulate for better context
            // Only clear when starting a new response
            break;

          case 'response.audio.delta':
            if ('delta' in message && this.audioPlayer && this.playerContext) {
              try {
                // Ensure audio context is running
                if (this.playerContext.state === 'suspended') {
                  await this.playerContext.resume();
                }
                
                const binary = atob(message.delta);
                const bytes = Uint8Array.from(binary, (c) => c.charCodeAt(0));
                const pcmData = new Int16Array(bytes.buffer);
                
                // Send audio data in smaller chunks to reduce crackling
                const chunkSize = 1024;  // Smaller chunks for smoother playback
                for (let i = 0; i < pcmData.length; i += chunkSize) {
                  const chunk = pcmData.slice(i, i + chunkSize);
                  this.audioPlayer.port.postMessage(chunk);
                }
              } catch (error) {
                console.error('[Voice] Audio playback error:', error);
                // Don't break the conversation on audio errors
              }
            }
            break;

          case 'input_audio_buffer.speech_started':
            // Don't clear response here - keep context
            this.onTranscript?.('Listening...');
            // Pause audio playback when user starts speaking to avoid overlap
            if (this.audioPlayer) {
              // Send null to clear any buffered audio
              this.audioPlayer.port.postMessage(null);
            }
            break;

          case 'conversation.item.input_audio_transcription.completed':
            if ('transcript' in message) {
              const transcript = message.transcript;
              
              // Filter out non-English transcripts
              // Check if transcript contains mostly English characters
              const englishPattern = /^[a-zA-Z0-9\s.,!?'"\-:;()]+$/;
              const isEnglish = englishPattern.test(transcript) && transcript.length > 0;
              
              // Also check if it's mostly non-ASCII (likely another language)
              const nonAsciiCount = (transcript.match(/[^\x00-\x7F]/g) || []).length;
              const isLikelyEnglish = nonAsciiCount < transcript.length * 0.3; // Less than 30% non-ASCII
              
              if (!isEnglish || !isLikelyEnglish) {
                console.log('[Voice] Skipping non-English transcript:', transcript);
                // Don't process non-English input
                break;
              }
              
              this.onTranscript?.(transcript);
              
              // ULTRA-SIMPLIFIED APPROACH: Send ALL user input to backend
              // Backend will intelligently detect if it's a command or just conversation
              // This is the most reliable approach - no frontend detection needed
              const lowerTranscript = transcript.toLowerCase().trim();
              
              // Skip very short inputs or just greetings
              const skipPatterns = ['hi', 'hello', 'hey', 'thanks', 'thank you', 'ok', 'okay', 'yes', 'no'];
              if (lowerTranscript.length < 10 && skipPatterns.includes(lowerTranscript)) {
                console.log('[Voice] Skipping short greeting:', transcript);
                break;
              }
              
              // Send everything else to backend - backend will decide what to do
              console.log('[Voice] Sending to backend:', transcript);
              this.executeTaskCommand(transcript).catch(err => {
                console.error('[Voice] Command execution error:', err);
              });
            }
            break;

          case 'response.done':
            // Response complete
            break;

          case 'input_audio_buffer.speech_stopped':
          case 'input_audio_buffer.committed':
          case 'conversation.item.created':
          case 'response.created':
          case 'response.output_item.added':
          case 'response.content_part.added':
          case 'response.audio.done':
          case 'response.content_part.done':
          case 'response.output_item.done':
            // These are normal flow messages, no action needed
            break;

          case 'error':
            const errorMsg = 'error' in message ? String(message.error) : 'Unknown error';
            // Only stop on critical errors - don't stop for transient issues
            const criticalErrors = ['session.error', 'connection.error', 'authentication'];
            const isCritical = criticalErrors.some(err => errorMsg.toLowerCase().includes(err));
            
            if (isCritical) {
              this.connectionOpen = false;
              this.recordingActive = false;
              this.onError?.(errorMsg);
            } else {
              // For non-critical errors, just mark connection as closed
              // Recording continues, connection may recover
              this.connectionOpen = false;
            }
            break;

          default:
            // Silently ignore unknown message types to avoid console spam
            break;
          }
        } catch (messageError) {
          // Handle errors in individual message processing without breaking the loop
          console.error('Error processing message:', messageError);
          // Continue processing other messages
        }
      }
    } catch (error) {
      // Only log connection-level errors, don't stop if it's just a temporary issue
      const errorMsg = error instanceof Error ? error.message : String(error);
      
      // Check if this is a recoverable error
      const recoverableErrors = ['network', 'timeout', 'temporary'];
      const isRecoverable = recoverableErrors.some(err => errorMsg.toLowerCase().includes(err));
      
      if (!isRecoverable) {
        console.error('Message handling error:', error);
        this.connectionOpen = false;
        this.recordingActive = false;
        this.messageHandlerRunning = false;
        this.onError?.('Connection error. Please try again.');
      } else {
        // For recoverable errors, just mark connection as closed but keep trying
        this.connectionOpen = false;
        console.log('Temporary connection issue, will retry:', errorMsg);
      }
    } finally {
      // Only mark as closed if we're intentionally stopping
      // Don't set these if recording is still active (might be reconnecting)
      if (this.shouldStop || !this.recordingActive) {
        this.connectionOpen = false;
        this.messageHandlerRunning = false;
      }
    }
  }

  private async executeTaskCommand(transcript: string) {
    if (!transcript || !transcript.trim()) {
      return; // Skip empty transcripts
    }

    try {
      console.log('[Voice] Executing command:', transcript.trim());
      
      // Send command to backend for processing
      const { data, status } = await api.voice.command(transcript.trim());
      
      console.log('[Voice] Command response:', { status, data });
      
      if (status === 200 || status === 201) {
        this.onTaskExecuted?.(data);
        
        // If task was created/updated, provide voice feedback
        if ('task' in data && data.task) {
          const task = data.task as any;
          if (task.id) {
            // Don't clear current response - let AI continue naturally
            // The backend message will be used by the AI
            console.log('[Voice] Task created successfully:', task.id);
            // Don't send separate message - let the AI handle it from the backend response
          } else {
            console.warn('[Voice] Task object missing ID:', data);
          }
        } else if ('tasks' in data && Array.isArray(data.tasks)) {
          const tasks = data.tasks as any[];
          // Don't clear current response - let AI continue naturally
          // The backend message will be used by the AI
          console.log('[Voice] Tasks retrieved:', tasks.length);
        } else if ('meetings' in data && Array.isArray(data.meetings)) {
          const meetings = data.meetings as any[];
          // Don't clear current response - let AI continue naturally
          // The backend message will be used by the AI
          console.log('[Voice] Meetings retrieved:', meetings.length);
        } else if (data.message) {
          // IMPORTANT: Send backend message back to AI so it can read it to the user
          // This ensures the AI knows what actually happened
          console.log('[Voice] Backend message:', data.message);
          
          // Send the backend response as a user message to the AI so it can respond
          // This way the AI knows what tasks were created/retrieved
          if (this.client && this.connectionOpen) {
            // Add the backend response to the conversation context
            // The AI will see this and can respond appropriately
            this.onResponse?.(`\n[System: ${data.message}]\n`, false);
          }
        } else {
          console.warn('[Voice] Unexpected response format:', data);
        }
      } else if (status === 400) {
        // Handle validation errors gracefully - don't interrupt conversation
        const errorMsg = (data as any)?.error || 'Could not process command';
        console.warn('[Voice] Command validation error:', errorMsg, data);
        // Silently log - don't show to user or interrupt conversation flow
        // The AI will handle the conversation naturally
      } else if (status === 404) {
        // User not found - provide helpful feedback
        const errorMsg = (data as any)?.error || 'User not found';
        const availableUsers = (data as any)?.available_users || [];
        console.warn('[Voice] User not found:', errorMsg, 'Available users:', availableUsers);
        
        // Provide feedback to user about the error
        if (availableUsers.length > 0) {
          this.onResponse?.(`User not found. Available users: ${availableUsers.join(', ')}`, false);
        } else {
          this.onResponse?.(`User not found. ${errorMsg}`, false);
        }
      } else {
        console.error('[Voice] Command failed with status:', status, data);
      }
    } catch (error) {
      console.error('[Voice] Task execution error:', error);
      // Don't show error to user, let them continue conversation
    }
  }

  stop() {
    this.shouldStop = true;
    this.recordingActive = false;
    this.connectionOpen = false;
    this.messageHandlerRunning = false;
    
    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach(track => track.stop());
      this.mediaStream = null;
    }

    if (this.workletNode) {
      this.workletNode.disconnect();
      this.workletNode = null;
    }

    if (this.audioContext) {
      this.audioContext.close();
      this.audioContext = null;
    }

    if (this.audioPlayer) {
      this.audioPlayer.port.postMessage(null);
      this.audioPlayer.disconnect();
      this.audioPlayer = null;
    }

    if (this.playerContext) {
      this.playerContext.close();
      this.playerContext = null;
    }

    if (this.client) {
      try {
        this.client.close();
      } catch (e) {
        // Ignore errors when closing
      }
      this.client = null;
    }

    this.audioBuffer = new Uint8Array();
  }
}
