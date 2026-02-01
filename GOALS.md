
# Phase 1 

[X] Write a socket client 
[X] Write the Logon Generator 
[X] Write the Heartbeat Loop 
[X] Write the listener 
[X] Write a socket server 
[X] Add outgoing_seq_num 
[] Add socket.retry() in a seperate thread 
[] Make heart_beat only send only if it didn't see any incoming message from server in last 1s 
[X] Session State Persistence 
[X] Add sending_time 
[X] Send logon message 
[] Handle gap fill 
[] Trigger shutdown if we are not able to logon after 100 attempts 
[] Handle repeating groups 

 ######## 

 How Production Systems differ from your Current Setup:

    Session State Persistence: In production, if you disconnect and reconnect, you must not reset your Sequence Number (Tag 34) to 1. You have to save it to a file or database. If the server expects sequence 500 and you send 1, they will kick you off immediately.

    The Gap Fill: If you were offline for 10 minutes, the server might have sent messages you missed. Production engines handle a Resend Request (35=2) to "fill the gap."

    Circuit Breakers: If the client fails to connect after 100 attempts, production systems usually trigger an alert (Slack/Email/PagerDuty) to a DevOps engineer.