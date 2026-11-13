import { build } from 'esbuild';
import { mkdir, copyFile, writeFile, readFile, rm } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('../', import.meta.url));
process.chdir(root);
// Only this build's generated frontend directory; never panel/project data.
await rm('dist/frontend', { recursive: true, force: true });
await mkdir('dist/frontend', { recursive: true });
const result = await build({
  entryPoints: {
    app: 'frontend/app.mjs',
    'editor.worker': 'node_modules/monaco-editor/esm/vs/editor/editor.worker.js',
  },
  outdir: 'dist/frontend', bundle: true, format: 'esm', splitting: true,
  minify: true, sourcemap: false, target: ['chrome120', 'firefox120', 'safari17'],
  loader: { '.ttf': 'file' }, assetNames: '[name]-[hash]',
  chunkNames: 'chunks/[name]-[hash]', legalComments: 'eof', logLevel: 'info',
  metafile: true,
  plugins: [{
    name: 'fixed-dompurify',
    setup(builder) {
      // Monaco also vendors a copy. npm overrides alone do NOT replace it.
      builder.onResolve({ filter: /dompurify\/dompurify\.js$/ }, () => ({
        path: fileURLToPath(new URL('../node_modules/dompurify/dist/purify.es.mjs', import.meta.url)),
      }));
    },
  }],
});
const inputs = Object.keys(result.metafile.inputs);
if (!inputs.includes('node_modules/dompurify/dist/purify.es.mjs')
    || inputs.some((name) => name.endsWith('/dompurify/dompurify.js'))) {
  throw new Error('Build must use the fixed DOMPurify implementation');
}
await copyFile('node_modules/monaco-editor/LICENSE', 'dist/frontend/MONACO-LICENSE.txt');
await copyFile('frontend/frame.html', 'dist/frontend/frame.html');
await copyFile('node_modules/monaco-editor/ThirdPartyNotices.txt', 'dist/frontend/ThirdPartyNotices.txt');
await copyFile('node_modules/dompurify/LICENSE', 'dist/frontend/DOMPURIFY-LICENSE.txt');
await copyFile('node_modules/marked/LICENSE.md', 'dist/frontend/MARKED-LICENSE.txt');
const lock = JSON.parse(await readFile('package-lock.json', 'utf8'));
const versions = Object.fromEntries(['monaco-editor', 'dompurify', 'marked'].map((name) =>
  [name, lock.packages[`node_modules/${name}`].version]));
await writeFile('dist/frontend/dependency-versions.json', JSON.stringify(versions, null, 2) + '\n');
