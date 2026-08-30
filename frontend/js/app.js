/**
 * Main Frontend Application Logic
 * Integrates WebRTCManager, AudioVisualizer, UI Controls, Transcript Feed, and Tool Execution Cards.
 */

document.addEventListener('DOMContentLoaded', () => {
  // Elements
  const btnConnect = document.getElementById('btn-connect');
  const btnMute = document.getElementById('btn-mute');
  const orbContainer = document.getElementById('orb-container');
  const statusBadge = document.getElementById('status-badge');
  const statusSubtext = document.getElementById('status-subtext');
  const transcriptFeed = document.getElementById('transcript-feed');
  const remoteAudio = document.getElementById('remote-audio');
  const tabTranscript = document.getElementById('tab-transcript');
  const tabTools = document.getElementById('tab-tools');
  const chatInput = document.getElementById('chat-input');
  const btnSend = document.getElementById('btn-send');

  // Visualizer Instance
  const visualizer = new AudioVisualizer('audio-visualizer');

  // WebRTC Instance
  let webrtc = null;
  let activeTab = 'transcript';

  function initWebRTC() {
    webrtc = new WebRTCManager({
      onStateChange: handleStateChange,
      onTranscription: handleTranscription,
      onBotSpeaking: handleBotSpeaking,
      onToolCall: handleToolCall,
      onRemoteStream: (stream) => {
        if (remoteAudio) {
          remoteAudio.srcObject = stream;
          remoteAudio.play().catch((e) => console.warn('Audio autoplay prevented:', e));
        }
        visualizer.connectStream(stream);
      },
      onError: (err) => {
        addTranscriptMessage('system', `Connection notice: ${err.message || err}`);
      },
    });
  }

  initWebRTC();

  // State Handler
  function handleStateChange(state) {
    if (state === 'connected') {
      orbContainer.className = 'orb-container listening';
      statusBadge.className = 'status-badge listening';
      statusBadge.textContent = 'Active & Listening';
      statusSubtext.textContent = 'Speak naturally to your voice assistant';
      btnConnect.innerHTML = `
        <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>
        Disconnect
      `;
      btnConnect.classList.add('btn-disconnect');
      addTranscriptMessage('system', 'Voice session established. Assistant is ready.');
    } else if (state === 'connecting') {
      orbContainer.className = 'orb-container';
      statusBadge.className = 'status-badge';
      statusBadge.textContent = 'Connecting...';
      statusSubtext.textContent = 'Establishing secure WebRTC audio stream';
      btnConnect.disabled = true;
    } else {
      // Disconnected
      orbContainer.className = 'orb-container disconnected';
      statusBadge.className = 'status-badge';
      statusBadge.textContent = 'Disconnected';
      statusSubtext.textContent = 'Click connect or tap the orb to start';
      btnConnect.innerHTML = `
        <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"/><path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/></svg>
        Start Voice Session
      `;
      btnConnect.classList.remove('btn-disconnect');
      btnConnect.disabled = false;
      visualizer.stop();
    }
  }

  function handleBotSpeaking(isSpeaking) {
    if (!webrtc || !webrtc.isConnected) return;
    if (isSpeaking) {
      orbContainer.className = 'orb-container speaking';
      statusBadge.className = 'status-badge speaking';
      statusBadge.textContent = 'Assistant Speaking...';
    } else {
      orbContainer.className = 'orb-container listening';
      statusBadge.className = 'status-badge listening';
      statusBadge.textContent = 'Active & Listening';
    }
  }

  function handleTranscription(data) {
    if (!data || !data.text) return;
    addTranscriptMessage(data.sender, data.text);
  }

  function handleToolCall(tool) {
    const toolName = tool.name || tool.function?.name || 'Workspace Tool';
    const toolArgs = tool.arguments || tool.args || tool.function?.arguments || {};
    addToolExecutionCard(toolName, toolArgs);
  }

  // Add Message to Transcript
  function addTranscriptMessage(sender, text) {
    if (!transcriptFeed) return;

    // Check if duplicate of last message
    const lastMsg = transcriptFeed.lastElementChild;
    if (lastMsg && lastMsg.dataset.sender === sender && lastMsg.dataset.text === text) {
      return;
    }

    const bubble = document.createElement('div');
    bubble.className = `message-bubble ${sender}`;
    bubble.dataset.sender = sender;
    bubble.dataset.text = text;

    const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    const avatarLetter = sender === 'user' ? 'YOU' : sender === 'assistant' ? 'AI' : 'SYS';
    const senderTitle = sender === 'user' ? 'You' : sender === 'assistant' ? 'Voice Assistant' : 'System';

    bubble.innerHTML = `
      <div class="message-avatar">${avatarLetter}</div>
      <div class="message-content-wrapper">
        <div class="message-header">
          <span class="message-sender">${senderTitle}</span>
          <span class="message-time">${timeStr}</span>
        </div>
        <div class="message-body">${escapeHtml(text)}</div>
      </div>
    `;

    transcriptFeed.appendChild(bubble);
    transcriptFeed.scrollTop = transcriptFeed.scrollHeight;
  }

  // Add Tool Card
  function addToolExecutionCard(name, args) {
    if (!transcriptFeed) return;

    let parsedArgs = args;
    if (typeof args === 'string') {
      try { parsedArgs = JSON.parse(args); } catch (e) {}
    }

    const card = document.createElement('div');
    card.className = 'tool-execution-card';

    let propsHtml = '';
    for (const [k, v] of Object.entries(parsedArgs || {})) {
      propsHtml += `
        <div class="tool-prop-row">
          <span class="tool-prop-key">${escapeHtml(k)}:</span>
          <span class="tool-prop-val">${escapeHtml(typeof v === 'object' ? JSON.stringify(v) : String(v))}</span>
        </div>
      `;
    }

    const isEmail = name.includes('email');
    const iconSvg = isEmail ? '📧' : '🗓️';
    const titleText = isEmail ? 'Gmail Dispatch' : 'Google Calendar Event';

    card.innerHTML = `
      <div class="tool-card-header">
        <div class="tool-card-title">
          <span>${iconSvg}</span>
          <span>${titleText} (${escapeHtml(name)})</span>
        </div>
        <div class="tool-card-badge">EXECUTED</div>
      </div>
      <div class="tool-card-body">
        ${propsHtml || '<div>Tool invoked with parameters.</div>'}
      </div>
    `;

    transcriptFeed.appendChild(card);
    transcriptFeed.scrollTop = transcriptFeed.scrollHeight;
  }

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  // Event Listeners
  btnConnect.addEventListener('click', () => {
    if (webrtc && webrtc.isConnected) {
      webrtc.disconnect();
    } else {
      if (!webrtc) initWebRTC();
      webrtc.connect();
    }
  });

  orbContainer.addEventListener('click', () => {
    if (webrtc && webrtc.isConnected) {
      webrtc.disconnect();
    } else {
      if (!webrtc) initWebRTC();
      webrtc.connect();
    }
  });

  btnMute.addEventListener('click', () => {
    if (webrtc) {
      const isMuted = webrtc.toggleMute();
      btnMute.classList.toggle('active', isMuted);
      btnMute.title = isMuted ? 'Unmute Microphone' : 'Mute Microphone';
      addTranscriptMessage('system', isMuted ? 'Microphone muted.' : 'Microphone active.');
    }
  });

  // Tab Switching
  tabTranscript.addEventListener('click', () => {
    tabTranscript.classList.add('active');
    tabTools.classList.remove('active');
    activeTab = 'transcript';
  });

  tabTools.addEventListener('click', () => {
    tabTools.classList.add('active');
    tabTranscript.classList.remove('active');
    activeTab = 'tools';
  });

  // Text Chat Fallback
  function handleSendMessage() {
    const text = chatInput.value.trim();
    if (!text) return;
    addTranscriptMessage('user', text);
    chatInput.value = '';

    // If connected via DataChannel, send text event
    if (webrtc && webrtc.dataChannel && webrtc.dataChannel.readyState === 'open') {
      webrtc.dataChannel.send(JSON.stringify({
        type: 'user-text-input',
        text: text,
      }));
    } else {
      // Fallback REST call
      fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text }),
      })
      .then(res => res.json())
      .then(data => {
        if (data.response) {
          addTranscriptMessage('assistant', data.response);
        }
        if (data.tool_calls) {
          data.tool_calls.forEach(tc => {
            addToolExecutionCard(tc.function.name, JSON.parse(tc.function.arguments));
          });
        }
      })
      .catch(err => {
        console.warn('REST chat fallback notice:', err);
      });
    }
  }

  btnSend.addEventListener('click', handleSendMessage);
  chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      handleSendMessage();
    }
  });
});
