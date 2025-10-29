// Cross-platform wrapper to run `serve -s build` with a sensible default port.
// Works on Windows cmd/PowerShell and *nix shells.

const { spawn } = require('child_process');

const port = process.env.PORT || '3000';
const args = ['serve', '-s', 'build', '-l', port];

const cmd = process.platform === 'win32' ? 'npx.cmd' : 'npx';
const child = spawn(cmd, args, { stdio: 'inherit', shell: true });

child.on('close', (code) => process.exit(code));
