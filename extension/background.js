const WS_URL = 'ws://127.0.0.1:18765/extension';
let socket = null;
let reconnectInterval = 1000;

function connect() {
  console.log(`[Pygent] Attempting to connect to ${WS_URL}...`);
  socket = new WebSocket(WS_URL);

  socket.onopen = () => {
    console.log('[Pygent] WebSocket connected');
    reconnectInterval = 1000; // Reset interval
  };

  socket.onmessage = async (event) => {
    try {
      const msg = JSON.parse(event.data);
      if (msg.type === 'request') {
        try {
          const response = await handleRequest(msg);
          if (socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({
              type: 'response',
              id: msg.id,
              payload: response
            }));
          }
        } catch (err) {
          if (socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({
              type: 'response',
              id: msg.id,
              error: err.message
            }));
          }
        }
      }
    } catch (err) {
      console.error('[Pygent] Error handling message:', err);
    }
  };

  socket.onclose = () => {
    console.log('[Pygent] WebSocket closed, retrying...');
    setTimeout(connect, reconnectInterval);
    reconnectInterval = Math.min(reconnectInterval * 1.5, 30000);
  };

  socket.onerror = (err) => {
    console.error('[Pygent] WebSocket error:', err);
  };
}

// Connect immediately
connect();

// Keep service worker alive
chrome.alarms.create("keepAlive", { periodInMinutes: 1 });
chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === "keepAlive") {
    // Just a wake up event to keep SW alive
    console.log("[Pygent] KeepAlive alarm fired");
  }
});

// Forward CDP events
chrome.debugger.onEvent.addListener((source, method, params) => {
  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({
      type: 'cdp_event',
      payload: {
        tabId: source.tabId,
        method: method,
        params: params
      }
    }));
  }
});

async function handleRequest(msg) {
  const { command, args } = msg.payload || {};
  
  switch (command) {
    case 'enumerate_tabs':
      return await chrome.tabs.query(args || {});
      
    case 'switch_tab':
      if (!args || typeof args.tabId === 'undefined') throw new Error("Missing tabId");
      const tab = await chrome.tabs.update(args.tabId, { active: true });
      if (tab && tab.windowId) {
        await chrome.windows.update(tab.windowId, { focused: true });
      }
      return tab;
      
    case 'create_tab':
      return await chrome.tabs.create({ url: args?.url });
      
    case 'execute_script':
      if (!args || typeof args.tabId === 'undefined') throw new Error("Missing tabId");
      if (!args.files || args.files.length === 0) throw new Error("Missing files array");
      return await chrome.scripting.executeScript({
        target: { tabId: args.tabId },
        files: args.files
      });
      
    case 'debugger_attach':
      if (!args || typeof args.tabId === 'undefined') throw new Error("Missing tabId");
      await chrome.debugger.attach({ tabId: args.tabId }, "1.3");
      return { success: true };
      
    case 'debugger_detach':
      if (!args || typeof args.tabId === 'undefined') throw new Error("Missing tabId");
      await chrome.debugger.detach({ tabId: args.tabId });
      return { success: true };
      
    case 'debugger_send_command':
      if (!args || typeof args.tabId === 'undefined') throw new Error("Missing tabId");
      if (!args.method) throw new Error("Missing method");
      
      return await new Promise((resolve, reject) => {
        chrome.debugger.sendCommand(
          { tabId: args.tabId },
          args.method,
          args.commandParams || {},
          (result) => {
            if (chrome.runtime.lastError) {
              reject(new Error(chrome.runtime.lastError.message));
            } else {
              resolve(result);
            }
          }
        );
      });
      
    default:
      throw new Error(`Unknown command: ${command}`);
  }
}
