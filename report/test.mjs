import test from 'node:test';
import assert from 'node:assert/strict';
import {project,smallest,durationText} from './math.js';
test('projections convert seconds/bytes consistently',()=>{const row=project({bytes:1073741824,encode_seconds:40},20,10);assert.equal(row.gib,30);assert.equal(row.minutes,20);});
test('winner must meet target, not merely be closest',()=>{assert.equal(smallest([{bytes:1,vmaf:90},{bytes:2,vmaf:96}],95).bytes,2);assert.equal(smallest([{bytes:1,vmaf:90}],95),null);});
test('duration formatting',()=>{assert.equal(durationText(100),'1h 40m');});
