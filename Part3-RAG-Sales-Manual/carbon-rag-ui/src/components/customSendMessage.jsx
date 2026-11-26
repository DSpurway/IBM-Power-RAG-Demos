import { UserType } from '@carbon/ai-chat';
import { buildRequestBody, mapResponse } from '../responseMapper.js';

const RESPONSE_USER_PROFILE = {
  id: 'assistant',
  nickname: 'Sales Manual Assistant',
  user_type: UserType.BOT,
};

// When the user picks a clarification option we show their choice as a normal chat
// message, but the backend needs the ORIGINAL question plus the chosen value.
let pendingClarification = null;

export function sendClarification(instance, { prompt, param, value, label }) {
  pendingClarification = { prompt, param, value };
  return instance.send(label || value);
}

function botMessage(generic) {
  return {
    output: { generic },
    message_options: { response_user_profile: RESPONSE_USER_PROFILE },
  };
}

function errorText(err, status) {
  if (status === 429) return 'The server is busy. Please try again shortly.';
  if (status >= 500) {
    return 'The Sales Manual service hit an error. Please try again, or contact the administrator if it persists.';
  }
  return `Could not reach the Sales Manual service (${err.message}).`;
}

export async function customSendMessage(request, options, instance) {
  const text = (request.input?.text || '').trim();
  if (!text) return;

  const pending = pendingClarification;
  pendingClarification = null;
  const body = buildRequestBody(text, pending);

  let loading = true;
  instance.updateIsMessageLoadingCounter('increase');
  const stopLoading = () => {
    if (loading) {
      loading = false;
      instance.updateIsMessageLoadingCounter('decrease');
    }
  };

  try {
    const res = await fetch('/api/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal: options?.signal,
    });
    if (!res.ok) {
      const err = new Error(`HTTP ${res.status}`);
      err.status = res.status;
      throw err;
    }
    const data = await res.json();
    stopLoading();
    await instance.messaging.addMessage(
      botMessage(mapResponse(data, body.prompt)),
    );
  } catch (err) {
    stopLoading();
    if (err.name === 'AbortError') return;
    await instance.messaging.addMessage(
      botMessage([
        { response_type: 'text', text: errorText(err, err.status) },
      ]),
    );
  } finally {
    stopLoading();
  }
}
