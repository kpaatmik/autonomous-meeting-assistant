const JitsiMeetJS = require("lib-jitsi-meet");
require("webrtc-adapter");

function joinMeeting(meetingURL, roomName, jwtToken) {

  // Step 1: Initialize Jitsi
  JitsiMeetJS.init();

  // Step 2: Extract domain
  const domain = meetingURL.replace("https://", "");

  // Step 3: Create connection
  const connection = new JitsiMeetJS.JitsiConnection(
    jwtToken,
    null,
    {
      serviceUrl: `wss://${domain}/xmpp-websocket`,
      hosts: {
        domain: domain,
        muc: `conference.${domain}`
      }
    }
  );

  // Step 4: Connect
  connection.connect();

  // Step 5: After connection success
  connection.addEventListener(
    JitsiMeetJS.events.connection.CONNECTION_ESTABLISHED,
    () => {
      console.log("Bot connected");

      // Step 6: Join meeting room
      const room = connection.initJitsiConference(roomName, {});
      room.join();

      // Step 7: Set bot name
      room.setDisplayName("AI Assistant");
    }
  );
}

module.exports = { joinMeeting };
