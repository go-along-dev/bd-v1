# =============================================================================
# tests/test_chat.py — Chat Tests
# =============================================================================
# See: system-design/06-chat.md for chat architecture
# See: system-design/10-api-contracts.md §8 "Chat Endpoints"
#
# TODO: test_websocket_connect_success
#       Connect with valid JWT and valid booking_id → connection accepted
#
# TODO: test_websocket_connect_invalid_booking
#       Connect with booking_id user is not part of → connection rejected
#
# TODO: test_websocket_message_persisted
#       Send message over WebSocket → verify in MongoDB chat_messages
#
# TODO: test_chat_history_pagination
#       Insert 60 messages → GET /chat/{id}/history?limit=20
#       → 20 messages returned, has_more=True
#       → Fetch next page with cursor → next 20 messages
#
# TODO: test_unread_counts
#       Insert messages from other user → GET /chat/unread
#       → correct unread count per booking
#
# TODO: test_mark_as_read
#       Open chat → unread count drops to 0
#
# work by adolf.
