import test from 'node:test';
import assert from 'node:assert/strict';
import { buildTagPairs, tagPairAt } from '../frontend/tag-pairs.mjs';

function tokens(line) {
  const result=[];
  for (const match of line.matchAll(/(<\/?)([\w:-]+)([^>]*)(>)/g)) {
    const start=match.index, name=start+match[1].length;
    result.push({offset:start,type:'delimiter.html'},{offset:name,type:'tag.html'});
    const end=start+match[0].length-1, attributes=name+match[2].length;
    if (attributes<end) result.push({offset:attributes,type:'attribute.value.html'});
    result.push({offset:end,type:'delimiter.html'},{offset:end+1,type:''});
  }
  return result;
}
test('nested HTML names pair without confusing void tags or repeated names', () => {
  const lines=['<head>','<meta charset="utf-8">','<div><div>x</div></div>','</head>'];
  const index=buildTagPairs(lines,lines.map(tokens));
  const pair=tagPairAt(index,2);assert.equal(pair.length,2);assert.equal(pair[1].nameStart,lines.slice(0,3).join('\n').length+3);
  assert.equal(tagPairAt(index,lines[0].length+4).length,0);
  assert.equal(index.pairs.size,6);
});
test('only syntax tokens participate; PHP strings and comments cannot add fake pairs', () => {
  const lines=['<head>','echo "</head>";','</head>'];
  const index=buildTagPairs(lines,[tokens(lines[0]),[{offset:0,type:'string.php'}],tokens(lines[2])]);
  const pair=tagPairAt(index,2);assert.equal(pair[1].start,lines[0].length+lines[1].length+2);
  assert.equal(tagPairAt(index,lines[0].length+6).length,0);
});
test('unmatched tags are not highlighted; CRLF offsets and closing selection remain exact', () => {
  const lines=['<head>','</head>','<header>'];const index=buildTagPairs(lines,lines.map(tokens),'\r\n');
  assert.equal(tagPairAt(index,lines[0].length+4)[1].start,0);
  assert.equal(tagPairAt(index,lines.join('\r\n').length-2).length,0);
});
test('very dense markup disables decorations at the bounded tag count', () => {
  const line='<p></p>'.repeat(10001);
  const index=buildTagPairs([line],[tokens(line)]);
  assert.equal(index.tags.length,0);assert.equal(index.pairs.size,0);
});
