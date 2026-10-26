# Forwarding lifecycle

`postman webhook forward <webhookId> <port>` runs until stopped. To stop a
background forwarding process, use
`pkill -INT -f "webhook forward <webhookId>"`. `kill $!` may reach only the
`postman` launcher and leave forwarding running.

Stopping forwarding leaves the webhook available to record deliveries. Start
forwarding again when the local service is ready, then replay a captured
request when the task needs it.
