// Minimal WebSocket helper. Opens a socket to the API (proxied by Vite in dev),
// parses each JSON message, and hands it to onMessage.
export function openWS(
  path: string,
  onMessage: (m: any) => void,
  onOpen?: (ws: WebSocket) => void,
  onClose?: () => void
): WebSocket {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${proto}://${location.host}${path}`);
  ws.onopen = () => onOpen?.(ws);
  ws.onmessage = (e) => onMessage(JSON.parse(e.data));
  ws.onclose = () => onClose?.();
  return ws;
}
