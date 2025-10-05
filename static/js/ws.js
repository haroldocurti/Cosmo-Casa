/*
 Robust WebSocket client with reconnection, heartbeat, and JSON/text/binary support.
*/
(function () {
  // Build ws URL using hostname and configurable port (default 6789)
  const host = window.location.hostname;
  const port = (window.WS_PORT || 6789);
  const WS_URL = `ws://${host}:${port}/ws`;
  const TOKEN = window.WS_TOKEN || null; // Optional auth token

  let ws = null;
  let reconnectAttempts = 0;
  let manualClose = false;

  const maxReconnectDelay = 30000; // 30s cap
  const baseDelay = 1000; // 1s initial

  function connect() {
    manualClose = false;
    try {
      ws = new WebSocket(WS_URL);
      ws.binaryType = 'arraybuffer';
    } catch (e) {
      console.warn('[WS] Failed to create WebSocket:', e);
      scheduleReconnect();
      return;
    }

    ws.onopen = () => {
      console.log('[WS] Connected');
      reconnectAttempts = 0;
      // Optional token-based auth message
      if (TOKEN) {
        try {
          ws.send(JSON.stringify({ token: TOKEN }));
        } catch (e) {
          console.warn('[WS] Failed to send auth token:', e);
        }
      }
    };

    ws.onmessage = (ev) => {
      const data = ev.data;
      if (typeof data === 'string') {
        try {
          const json = JSON.parse(data);
          console.log('[WS] JSON', json);
        } catch (e) {
          console.log('[WS] Text', data);
        }
      } else if (data instanceof ArrayBuffer) {
        console.log('[WS] Binary received', data.byteLength, 'bytes');
      } else {
        console.log('[WS] Message', data);
      }
    };

    ws.onerror = (err) => {
      console.warn('[WS] Error', err);
    };

    ws.onclose = (ev) => {
      console.warn('[WS] Closed', ev.code, ev.reason);
      if (!manualClose) {
        scheduleReconnect();
      }
    };
  }

  function scheduleReconnect() {
    reconnectAttempts++;
    const delay = Math.min(baseDelay * Math.pow(2, reconnectAttempts - 1), maxReconnectDelay);
    console.log('[WS] Reconnecting in', delay, 'ms');
    setTimeout(connect, delay);
  }

  function sendJSON(obj) {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(obj));
    }
  }

  function sendText(text) {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(text);
    }
  }

  function sendBinary(bytes) {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(bytes);
    }
  }

  function close() {
    manualClose = true;
    if (ws) ws.close();
  }

  // Expose API
  window.AppWS = { connect, sendJSON, sendText, sendBinary, close };

  // Auto-connect on page load
  document.addEventListener('DOMContentLoaded', connect);
})();