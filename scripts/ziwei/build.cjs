// Rebuild only: pnpm install --frozen-lockfile --ignore-scripts, then node build.cjs.
const esbuild = require('esbuild');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const sha = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const nodes = [path.join(__dirname, 'node_modules'), ...(process.env.NODE_PATH || '').split(path.delimiter).filter(Boolean)];
const result = esbuild.buildSync({
  absWorkingDir: __dirname, entryPoints: ['src/runner.ts'], outfile: 'engine.cjs',
  platform: 'node', target: 'node18', format: 'cjs', bundle: true,
  legalComments: 'inline', metafile: true, nodePaths: nodes, charset: 'utf8',
});
const packages = new Map();
for (const name of Object.keys(result.metafile.inputs)) {
  let dir = path.dirname(path.resolve(__dirname, name));
  while (dir !== path.dirname(dir)) {
    const file = path.join(dir, 'package.json');
    if (fs.existsSync(file)) {
      const pkg = JSON.parse(fs.readFileSync(file, 'utf8'));
      if (pkg.name && pkg.name !== 'bazi-ziwei-build') {
        const key = `${pkg.name}@${pkg.version}`;
        const licenseName = fs.readdirSync(dir).find(x => /^licen[cs]e(?:\.|$)/i.test(x));
        if (!licenseName) throw new Error(`Missing license: ${key}`);
        packages.set(key, { name: pkg.name, version: pkg.version, license: pkg.license,
          licenseText: fs.readFileSync(path.join(dir, licenseName), 'utf8') });
      }
      break;
    }
    dir = path.dirname(dir);
  }
}
const deps = [...packages.values()].sort((a, b) => a.name.localeCompare(b.name));
fs.writeFileSync(path.join(__dirname, 'THIRD_PARTY_NOTICES.txt'), deps.map(p => `${p.name}@${p.version} (${p.license})\n\n${p.licenseText}`).join('\n\n----------------\n\n'));
const file = path.join(__dirname, 'provenance.json');
const manifest = JSON.parse(fs.readFileSync(file, 'utf8'));
manifest.bundle_sha256 = sha(fs.readFileSync(path.join(__dirname, 'engine.cjs')));
manifest.runtime_packages = deps.map(({ licenseText, ...pkg }) => pkg);
manifest.local_sources_sha256 = {};
for (const name of ['src/runner.ts', 'src/upstream/algorithm.ts', 'src/upstream/types.ts', 'src/upstream/constants.ts', 'package.json', 'pnpm-lock.yaml', 'build.cjs'])
  manifest.local_sources_sha256[name] = sha(fs.readFileSync(path.join(__dirname, name)));
fs.writeFileSync(file, JSON.stringify(manifest, null, 2) + '\n');
console.log(`Built offline engine (${fs.statSync(path.join(__dirname, 'engine.cjs')).size} bytes); ${deps.length} dependency licenses retained.`);
