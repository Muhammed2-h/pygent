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
      if (msg.cmd) {
        try {
          const response = await handleRequest(msg);
          if (socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({
              id: msg.id,
              ok: true,
              data: response
            }));
          }
        } catch (err) {
          if (socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({
              id: msg.id,
              ok: false,
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


function waitForTabLoad(tabId) {
    return new Promise((resolve) => {
        chrome.tabs.get(tabId, (tab) => {
            if (!tab || tab.status === 'complete') {
                resolve();
            } else {
                const listener = (tid, changeInfo) => {
                    if (tid === tabId && changeInfo.status === 'complete') {
                        chrome.tabs.onUpdated.removeListener(listener);
                        resolve();
                    }
                };
                chrome.tabs.onUpdated.addListener(listener);
            }
        });
    });
}

async function handleRequest(msg) {
  const command = msg.cmd;
  const args = msg.payload || {};
  const tabId = typeof msg.tabId !== 'undefined' ? msg.tabId : args.tabId;
  
  switch (command) {
    case 'enumerate_tabs':
      return await chrome.tabs.query(args || {});
      
    case 'switch_tab':
      if (typeof tabId === 'undefined') throw new Error("Missing tabId");
      const tab = await chrome.tabs.update(tabId, { active: true });
      if (tab && tab.windowId) {
        await chrome.windows.update(tab.windowId, { focused: true });
      }
      return tab;
      
    case 'create_tab':
      return await chrome.tabs.create({ url: args?.url });
      
    
    case 'execute': {
      if (typeof tabId === 'undefined') throw new Error("Missing tabId");
      if (!args.script) throw new Error("Missing script");

      const wrapperCode = `
      (async () => {
          function serializeNode(node) {
              if (!node) return null;
              if (node.nodeType === 3) return { nodeType: 3, nodeValue: node.nodeValue };
              if (node.nodeType !== 1) return { nodeType: node.nodeType };
              let obj = {
                  nodeType: 1,
                  tagName: node.tagName.toLowerCase(),
                  attributes: {},
                  textContent: node.textContent
              };
              if (node.attributes) {
                  for (let attr of node.attributes) {
                      obj.attributes[attr.name] = attr.value;
                  }
              }
              return obj;
          }
          
          function serialize(val) {
              if (val === null || val === undefined) return val;
              if (val instanceof Node) return { __pygent_type: 'node', ...serializeNode(val) };
              if (val instanceof NodeList || val instanceof HTMLCollection) {
                  return { __pygent_type: 'nodelist', length: val.length, items: Array.from(val).map(serializeNode) };
              }
              if (Array.isArray(val)) {
                  return val.map(item => serialize(item));
              }
              if (typeof val === 'object') {
                  let out = {};
                  for (let k in val) {
                      out[k] = serialize(val[k]);
                  }
                  return out;
              }
              return val;
          }

          try {
              const result = await (async function() {
                  ${args.script}
              })();
              // Add a small delay so that context destruction can be caught if navigating
              await new Promise(r => setTimeout(r, 50));
              return serialize(result);
          } catch (err) {
              return { __pygent_error: true, message: err.message, stack: err.stack };
          }
      })()
      `;

      return await new Promise((resolve, reject) => {
          let navigationStarted = false;
          let createdTabs = [];
          
          const navListener = (details) => {
              if (details.tabId === tabId && details.frameId === 0) {
                  navigationStarted = true;
              }
          };
          const tabCreatedListener = (tab) => {
              createdTabs.push(tab.id);
          };
          
          chrome.webNavigation.onBeforeNavigate.addListener(navListener);
          chrome.tabs.onCreated.addListener(tabCreatedListener);
          
          const cleanupAndResolve = async (res) => {
              // Wait a bit to ensure events are processed
              await new Promise(r => setTimeout(r, 50));
              chrome.webNavigation.onBeforeNavigate.removeListener(navListener);
              chrome.tabs.onCreated.removeListener(tabCreatedListener);
              
              if (navigationStarted || (res && typeof res === 'object' && res.__pygent_error && (res.message.includes('Execution context was destroyed') || res.message.includes('unknown context')))) {
                  await waitForTabLoad(tabId);
              }
              for (const tid of createdTabs) {
                  await waitForTabLoad(tid);
              }
              resolve(res);
          };

          const runCDP = () => {
              chrome.debugger.getTargets((targets) => {
                  if (chrome.runtime.lastError) {
                      return cleanupAndResolve({ __pygent_error: true, message: chrome.runtime.lastError.message });
                  }
                  
                  const target = targets.find(t => t.tabId === tabId && t.attached);
                  const needsDetach = !target;
                  
                  const run = () => {
                      chrome.debugger.sendCommand({ tabId }, "Runtime.evaluate", {
                          expression: wrapperCode,
                          awaitPromise: true,
                          returnByValue: true,
                          userGesture: true
                      }, (res) => {
                          const err = chrome.runtime.lastError ? chrome.runtime.lastError.message : null;
                          
                          const complete = () => {
                              if (err) {
                                  cleanupAndResolve({ __pygent_error: true, message: err });
                              } else if (res && res.exceptionDetails) {
                                  cleanupAndResolve({
                                      __pygent_error: true,
                                      message: res.exceptionDetails.exception?.description || res.exceptionDetails.text,
                                      stack: null
                                  });
                              } else if (res && res.result) {
                                  cleanupAndResolve(res.result.value);
                              } else {
                                  cleanupAndResolve(null);
                              }
                          };
                          
                          if (needsDetach) {
                              chrome.debugger.detach({ tabId }, complete);
                          } else {
                              complete();
                          }
                      });
                  };
                  
                  if (needsDetach) {
                      chrome.debugger.attach({ tabId }, "1.3", () => {
                          if (chrome.runtime.lastError) {
                              return cleanupAndResolve({ __pygent_error: true, message: chrome.runtime.lastError.message });
                          }
                          run();
                      });
                  } else {
                      run();
                  }
              });
          };

          chrome.scripting.executeScript({
              target: { tabId },
              world: "MAIN",
              func: (code) => {
                  try {
                      return eval(code);
                  } catch (err) {
                      return { __pygent_fallback_cdp: true, message: err.toString() };
                  }
              },
              args: [wrapperCode]
          }, (injectionResults) => {
              if (chrome.runtime.lastError) {
                  runCDP();
              } else if (!injectionResults || injectionResults.length === 0) {
                  runCDP();
              } else {
                  const res = injectionResults[0].result;
                  if (res && typeof res === 'object' && res.__pygent_fallback_cdp) {
                      runCDP();
                  } else {
                      cleanupAndResolve(res);
                  }
              }
          });
      });
    }

    case 'execute_script':
      if (typeof tabId === 'undefined') throw new Error("Missing tabId");
      if (!args.files || args.files.length === 0) throw new Error("Missing files array");
      return await chrome.scripting.executeScript({
        target: { tabId: tabId },
        files: args.files
      });
      
    case 'debugger_attach':
      if (typeof tabId === 'undefined') throw new Error("Missing tabId");
      await chrome.debugger.attach({ tabId: tabId }, "1.3");
      return { success: true };
      
    case 'debugger_detach':
      if (typeof tabId === 'undefined') throw new Error("Missing tabId");
      await chrome.debugger.detach({ tabId: tabId });
      return { success: true };
    case 'batch': {
      if (typeof tabId === 'undefined') throw new Error("Missing tabId");
      if (!args.commands || !Array.isArray(args.commands)) throw new Error("Missing commands array");

      const targets = await new Promise(r => chrome.debugger.getTargets(r));
      const target = targets.find(t => t.tabId === tabId && t.attached);
      const needsDetach = !target;

      if (needsDetach) {
          await new Promise((resolve, reject) => {
              chrome.debugger.attach({ tabId }, "1.3", () => {
                  if (chrome.runtime.lastError) reject(new Error(chrome.runtime.lastError.message));
                  else resolve();
              });
          });
      }

      const results = [];
      const resolveRefs = (obj) => {
          if (typeof obj === 'string' && obj.startsWith('$ref:')) {
              const path = obj.slice(5).split('.');
              let current = results;
              for (const part of path) {
                  if (current === undefined || current === null) break;
                  current = current[part];
              }
              return current;
          } else if (Array.isArray(obj)) {
              return obj.map(item => resolveRefs(item));
          } else if (obj !== null && typeof obj === 'object') {
              const newObj = {};
              for (const key in obj) {
                  newObj[key] = resolveRefs(obj[key]);
              }
              return newObj;
          }
          return obj;
      };

      try {
          for (let i = 0; i < args.commands.length; i++) {
              const cmd = args.commands[i];
              if (!cmd.method) {
                  throw new Error(`Command at index ${i} is missing 'method'`);
              }
              const resolvedParams = resolveRefs(cmd.params || {});
              const res = await new Promise((resolve, reject) => {
                  chrome.debugger.sendCommand(
                      { tabId },
                      cmd.method,
                      resolvedParams,
                      (result) => {
                          if (chrome.runtime.lastError) reject(new Error(chrome.runtime.lastError.message));
                          else resolve(result);
                      }
                  );
              });
              
              if (res && res.exceptionDetails) {
                  throw new Error(`Command at index ${i} failed semantically: ${res.exceptionDetails.exception?.description || res.exceptionDetails.text}`);
              }
              
              results.push(res);
          }
      } finally {
          if (needsDetach) {
              await new Promise(r => {
                  chrome.debugger.detach({ tabId }, () => {
                      const _ = chrome.runtime.lastError;
                      r();
                  });
              });
          }
      }
      return results;
    }
      
    case 'debugger_send_command':
      if (typeof tabId === 'undefined') throw new Error("Missing tabId");
      if (!args.method) throw new Error("Missing method");
      
      return await new Promise((resolve, reject) => {
        chrome.debugger.sendCommand(
          { tabId: tabId },
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
