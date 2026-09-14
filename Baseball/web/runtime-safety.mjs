import { AsyncLocalStorage } from 'node:async_hooks';
import { spawn } from 'node:child_process';

export const requestWork = new AsyncLocalStorage();

export class HttpFailure extends Error {
  constructor(status, code, message) { super(message); this.status = status; this.code = code; }
}

export function requestSignal(timeoutMs) {
  const parent = requestWork.getStore()?.signal;
  parent?.throwIfAborted();
  return parent ? AbortSignal.any([parent, AbortSignal.timeout(timeoutMs)]) : AbortSignal.timeout(timeoutMs);
}

export function runJsonCommand(command, args, { input, cwd, signal = requestWork.getStore()?.signal,
  timeoutMs = 30_000, stdoutLimit = 16 * 1024 * 1024, stderrLimit = 64 * 1024 } = {}) {
  signal?.throwIfAborted();
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, { cwd, windowsHide: true, stdio: ['pipe','pipe','pipe'] });
    const chunks = [];
    let stdoutBytes = 0, stderrBytes = 0, failure, finished = false;
    const stop = error => {
      if (finished || failure) return;
      failure = error;
      child.kill('SIGKILL');
    };
    const aborted = () => stop(signal.reason ?? new DOMException('Request cancelled', 'AbortError'));
    const timer = setTimeout(() => stop(new HttpFailure(504, 'worker-timeout', 'The serving query timed out.')), timeoutMs);
    timer.unref();
    const finish = (error, payload) => {
      if (finished) return;
      finished = true; clearTimeout(timer); signal?.removeEventListener('abort', aborted);
      error ? reject(error) : resolve(payload);
    };
    signal?.addEventListener('abort', aborted, { once: true });
    if (signal?.aborted) aborted();
    child.stdout.on('data', chunk => {
      if (failure) return;
      stdoutBytes += chunk.length;
      if (stdoutBytes > stdoutLimit) stop(new HttpFailure(502, 'worker-output-limit', 'The serving response exceeds its limit.'));
      else chunks.push(chunk);
    });
    child.stderr.on('data', chunk => {
      if (failure) return;
      stderrBytes += chunk.length;
      if (stderrBytes > stderrLimit) stop(new HttpFailure(502, 'worker-error-limit', 'The serving worker exceeded its error-output limit.'));
    });
    child.on('error', () => finish(new HttpFailure(503, 'worker-unavailable', 'The serving worker could not start.')));
    child.stdin.on('error', () => stop(new HttpFailure(502, 'worker-input-failed', 'The serving worker could not read its request.')));
    child.on('close', code => {
      if (failure) return finish(failure);
      if (code !== 0) return finish(new HttpFailure(503, 'serving-unavailable', 'The materialized serving query is unavailable.'));
      try {
        const payload = JSON.parse(Buffer.concat(chunks).toString('utf8'));
        if (!payload || typeof payload !== 'object' || payload.status === 'unavailable') {
          return finish(new HttpFailure(503, 'serving-unavailable', 'The materialized serving query is unavailable.'));
        }
        finish(null, payload);
      } catch { finish(new HttpFailure(502, 'invalid-worker-response', 'The serving worker returned an invalid response.')); }
    });
    try { child.stdin.end(JSON.stringify(input)); }
    catch { stop(new HttpFailure(400, 'invalid-worker-input', 'The serving request could not be serialized.')); }
  });
}

export async function boundedResponseJson(response, limit = 32 * 1024 * 1024) {
  const reader = response.body?.getReader();
  if (!reader) throw new HttpFailure(502, 'empty-upstream-response', 'The graph database returned an empty response.');
  const chunks = []; let size = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > limit) {
        await reader.cancel();
        throw new HttpFailure(502, 'upstream-response-limit', 'The graph response is too large. Narrow the selection.');
      }
      chunks.push(value);
    }
    try { return JSON.parse(Buffer.concat(chunks).toString('utf8')); }
    catch { throw new HttpFailure(502, 'invalid-upstream-response', 'The graph database returned an invalid response.'); }
  } finally { reader.releaseLock(); }
}

export function validateLocalRequest(request) {
  // Reject DNS rebinding and browser requests from other sites. Do not trust
  // forwarding headers; reverse-proxy exposure needs an explicit deployment policy.
  const host = request.headers.host;
  if (typeof host !== 'string' || !/^(?:localhost|127\.0\.0\.1|\[::1\])(?::\d{1,5})?$/i.test(host)) {
    throw new HttpFailure(403, 'untrusted-host', 'This service accepts local hostnames only.');
  }
  const origin = request.headers.origin;
  if (origin !== undefined && origin !== `http://${host}`) {
    throw new HttpFailure(403, 'untrusted-origin', 'Cross-origin requests are not permitted.');
  }
  if (request.headers['sec-fetch-site'] === 'cross-site') {
    throw new HttpFailure(403, 'cross-site-request', 'Cross-site requests are not permitted.');
  }
  if (!request.url?.startsWith('/') || request.url.startsWith('//')) {
    throw new HttpFailure(400, 'invalid-request-target', 'An origin-form request target is required.');
  }
}

export function boundedRequestHandler(handler, sendError, { maxActive = 4, deadlineMs = 45_000 } = {}) {
  if (!Number.isInteger(maxActive) || maxActive < 1 || maxActive > 32 ||
      !Number.isInteger(deadlineMs) || deadlineMs < 50 || deadlineMs > 120_000) throw new Error('Invalid request limits');
  let active = 0, draining = false;
  const controllers = new Set();
  const wrapped = async (request, response) => {
    let admitted = false, controller, timer;
    const cancel = () => controller?.abort(new DOMException('Client disconnected', 'AbortError'));
    try {
      validateLocalRequest(request);
      if (draining) throw new HttpFailure(503, 'service-draining', 'The service is restarting.');
      const pathname = new URL(request.url, 'http://127.0.0.1').pathname;
      const expensive = pathname.startsWith('/api/') || pathname === '/health/ready';
      if (expensive && active >= maxActive) {
        response.setHeader('Retry-After', '2');
        throw new HttpFailure(503, 'service-busy', 'The service is busy. Please retry shortly.');
      }
      if (expensive) { active++; admitted = true; }
      controller = new AbortController(); controllers.add(controller);
      response.on('close', cancel);
      timer = setTimeout(() => {
        const error = new HttpFailure(504, 'request-timeout', 'The request timed out. Narrow the selection and retry.');
        controller.abort(error); sendError(response, error);
      }, deadlineMs);
      timer.unref();
      await requestWork.run({ signal: controller.signal }, () => handler(request, response));
    } catch (error) { sendError(response, error); }
    finally {
      clearTimeout(timer); response.removeListener('close', cancel);
      if (controller) controllers.delete(controller);
      if (admitted) active--;
    }
  };
  wrapped.drain = () => { draining = true; };
  wrapped.abortAll = () => { for (const controller of controllers) controller.abort(new DOMException('Service shutdown', 'AbortError')); };
  return wrapped;
}
