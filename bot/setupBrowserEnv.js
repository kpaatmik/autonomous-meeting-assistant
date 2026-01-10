const wrtc = require("wrtc");

/**
 * Minimal browser-like environment for lib-jitsi-meet
 * (No jsdom, no ESM, Node-safe)
 */

// ---- navigator ----
global.navigator = {
  userAgent:
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " +
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
  mediaDevices: {
    enumerateDevices: async () => [],
    addEventListener: () => {},
  },
};

// ---- document ----
global.document = {
  readyState: "complete",
  createElement: (tag) => {
    if (tag === "audio" || tag === "video") {
      return {
        setSinkId: () => Promise.resolve(),
        play: () => {},
        pause: () => {},
        style: {},
      };
    }

    return {
      style: {},
      appendChild: () => {},
      setAttribute: () => {},
    };
  },
  body: {
    appendChild: () => {},
    removeChild: () => {},
  },
  addEventListener: () => {},
};

// ---- window ----
global.window = {
  navigator: global.navigator,
  document: global.document,
  location: { protocol: "https:" },
  addEventListener: () => {},
  removeEventListener: () => {},
  setTimeout,
  clearTimeout,
};

// ---- WebRTC ----
global.RTCPeerConnection = wrtc.RTCPeerConnection;
global.RTCSessionDescription = wrtc.RTCSessionDescription;
global.RTCIceCandidate = wrtc.RTCIceCandidate;

// Some Jitsi code checks these directly
global.window.RTCPeerConnection = global.RTCPeerConnection;
global.window.RTCSessionDescription = global.RTCSessionDescription;
global.window.RTCIceCandidate = global.RTCIceCandidate;
