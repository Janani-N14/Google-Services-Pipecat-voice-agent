/**
 * WebRTC Client Manager for Pipecat Voice Agent
 * Handles SDP Offer/Answer exchange, ICE Candidate patching, Audio Tracks, and RTVI DataChannel.
 */

class WebRTCManager {
  constructor(options = {}) {
    this.options = Object.assign({
      apiUrl: '',
      onStateChange: (state) => {},
      onTranscription: (data) => {},
      onBotSpeaking: (isSpeaking) => {},
      onToolCall: (toolData) => {},
      onRemoteStream: (stream) => {},
      onError: (err) => {},
    }, options);

    this.peerConnection = null;
    this.localStream = null;
    this.remoteStream = null;
    this.dataChannel = null;
    this.pcId = this.generateId();
    this.isConnected = false;
    this.isMuted = false;
  }

  generateId() {
    return 'pc_' + Math.random().toString(36).substring(2, 11);
  }

  async connect() {
    try {
      this.options.onStateChange('connecting');
      this.pcId = this.generateId();

      // 1. Request user microphone
      this.localStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
        video: false,
      });

      // 2. Initialize RTCPeerConnection
      this.peerConnection = new RTCPeerConnection({
        iceServers: [
          { urls: 'stun:stun.l.google.com:19302' },
          { urls: 'stun:stun1.l.google.com:19302' },
        ],
      });

      // 3. Add local audio tracks to peer connection
      this.localStream.getTracks().forEach((track) => {
        this.peerConnection.addTrack(track, this.localStream);
      });

      // 4. Handle incoming remote audio track
      this.peerConnection.ontrack = (event) => {
        if (event.streams && event.streams[0]) {
          this.remoteStream = event.streams[0];
          this.options.onRemoteStream(this.remoteStream);
        }
      };

      // 5. Setup RTVI Data Channel
      this.setupDataChannel();

      // 6. Handle ICE candidates
      this.peerConnection.onicecandidate = (event) => {
        if (event.candidate) {
          this.sendIceCandidate(event.candidate);
        }
      };

      this.peerConnection.onconnectionstatechange = () => {
        const state = this.peerConnection.connectionState;
        console.log('[WebRTC] Connection state changed:', state);
        if (state === 'connected') {
          this.isConnected = true;
          this.options.onStateChange('connected');
        } else if (state === 'disconnected' || state === 'failed' || state === 'closed') {
          this.disconnect();
        }
      };

      // 7. Create Offer and Set Local Description
      const offer = await this.peerConnection.createOffer();
      await this.peerConnection.setLocalDescription(offer);

      // 8. Send Offer to Pipecat Backend
      const response = await fetch(`${this.options.apiUrl}/api/offer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sdp: this.peerConnection.localDescription.sdp,
          type: this.peerConnection.localDescription.type,
          pc_id: this.pcId,
          request_data: {},
        }),
      });

      if (!response.ok) {
        throw new Error(`Failed to exchange SDP offer (HTTP ${response.status})`);
      }

      const answer = await response.json();
      if (!answer || !answer.sdp) {
        throw new Error('Invalid SDP answer received from server');
      }

      // 9. Set Remote Description
      await this.peerConnection.setRemoteDescription(
        new RTCSessionDescription({
          sdp: answer.sdp,
          type: answer.type || 'answer',
        })
      );

      return true;
    } catch (err) {
      console.error('[WebRTC] Connection error:', err);
      this.disconnect();
      this.options.onError(err);
      return false;
    }
  }

  setupDataChannel() {
    try {
      this.dataChannel = this.peerConnection.createDataChannel('rtvi-events');
      this.dataChannel.onopen = () => {
        console.log('[WebRTC] DataChannel opened');
      };
      this.dataChannel.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          this.handleRtviMessage(msg);
        } catch (e) {
          console.debug('[WebRTC] Non-JSON DataChannel message:', event.data);
        }
      };
    } catch (e) {
      console.warn('[WebRTC] DataChannel setup warning:', e);
    }
  }

  handleRtviMessage(msg) {
    if (!msg) return;
    const type = msg.type || msg.event;

    if (type === 'user-transcription' || type === 'transcription') {
      this.options.onTranscription({
        sender: 'user',
        text: msg.data?.text || msg.text || '',
        isFinal: msg.data?.final !== false,
      });
    } else if (type === 'bot-transcription' || type === 'bot-llm-text' || type === 'llm-response') {
      this.options.onTranscription({
        sender: 'assistant',
        text: msg.data?.text || msg.text || '',
      });
    } else if (type === 'bot-speaking' || type === 'tts-started') {
      this.options.onBotSpeaking(true);
    } else if (type === 'bot-stopped-speaking' || type === 'tts-stopped') {
      this.options.onBotSpeaking(false);
    } else if (type === 'function-call' || type === 'tool-call') {
      this.options.onToolCall(msg.data || msg);
    }
  }

  async sendIceCandidate(candidate) {
    try {
      await fetch(`${this.options.apiUrl}/api/offer`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          pc_id: this.pcId,
          candidates: [
            {
              candidate: candidate.candidate,
              sdpMid: candidate.sdpMid,
              sdpMLineIndex: candidate.sdpMLineIndex,
            },
          ],
        }),
      });
    } catch (err) {
      console.warn('[WebRTC] Error patching ICE candidate:', err);
    }
  }

  toggleMute() {
    if (!this.localStream) return false;
    this.isMuted = !this.isMuted;
    this.localStream.getAudioTracks().forEach((track) => {
      track.enabled = !this.isMuted;
    });
    return this.isMuted;
  }

  disconnect() {
    this.isConnected = false;
    if (this.dataChannel) {
      try { this.dataChannel.close(); } catch (e) {}
      this.dataChannel = null;
    }
    if (this.localStream) {
      this.localStream.getTracks().forEach((track) => track.stop());
      this.localStream = null;
    }
    if (this.peerConnection) {
      try { this.peerConnection.close(); } catch (e) {}
      this.peerConnection = null;
    }
    this.remoteStream = null;
    this.options.onStateChange('disconnected');
  }
}

window.WebRTCManager = WebRTCManager;
