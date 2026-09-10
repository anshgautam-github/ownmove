import { api } from './client';
import { endpoints } from './endpoints';

/**
 * The only file that knows the AI Coach dashboard talks to FastAPI.
 * Mirrors services/api/careerSimulation.js's shape — conversations and
 * messages are a parent/child pair, not a single resource per user.
 */

/** Start a brand-new coaching conversation with its first message.
 * Resolves to `{ conversation, user_message, assistant_message }`. */
export async function startConversation(message) {
  return api.post(endpoints.careerAi.aiCoachConversations, { message });
}

/** Continue an existing conversation. Resolves to the same shape as
 * `startConversation`. */
export async function sendMessage(conversationId, message) {
  return api.post(endpoints.careerAi.aiCoachMessages(conversationId), { message });
}

/** Every conversation's headline, most recently active first. Resolves to
 * `[]` when there's no history yet. */
export async function getConversations() {
  return api.get(endpoints.careerAi.aiCoachConversations);
}

/** Fetch one conversation with its full message history. */
export async function getConversation(conversationId) {
  return api.get(endpoints.careerAi.aiCoachConversation(conversationId));
}

/** Delete a conversation (and its messages, via cascade). */
export async function deleteConversation(conversationId) {
  return api.delete(endpoints.careerAi.aiCoachConversation(conversationId));
}
