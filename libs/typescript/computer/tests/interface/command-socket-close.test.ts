import { afterEach, describe, expect, it } from 'vitest';
import { WebSocketServer } from 'ws';
import { MacOSComputerInterface } from '../../src/interface/macos.ts';

describe('BaseComputerInterface.sendCommand when the socket drops', () => {
  let wss: WebSocketServer | undefined;
  let iface: MacOSComputerInterface | undefined;

  afterEach(() => {
    iface?.disconnect();
    wss?.close();
  });

  it('rejects the pending command and lets the next command run', async () => {
    let dropNext = true;
    wss = new WebSocketServer({ port: 0 });
    wss.on('connection', (ws) => {
      ws.on('message', (data) => {
        const message = JSON.parse(data.toString());
        if (dropNext) {
          // The server goes away mid-command without answering.
          dropNext = false;
          ws.terminate();
          return;
        }
        ws.send(JSON.stringify({ success: true, command: message.command }));
      });
    });
    const port = (wss.address() as { port: number }).port;
    iface = new MacOSComputerInterface(`localhost:${port}`, 'u', 'p');
    await iface.connect();

    const dropped = iface.sendCommand('left_click', { x: 1, y: 2 });
    await expect(
      Promise.race([
        dropped.then(
          () => 'resolved',
          () => 'rejected'
        ),
        new Promise((resolve) => setTimeout(() => resolve('still pending'), 2000)),
      ])
    ).resolves.toBe('rejected');

    const next = await Promise.race([
      iface.sendCommand('right_click', { x: 3, y: 4 }),
      new Promise((resolve) => setTimeout(() => resolve('still pending'), 4000)),
    ]);
    expect(next).toEqual({ success: true, command: 'right_click' });
  }, 10000);
});
