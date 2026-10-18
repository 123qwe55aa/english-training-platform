import test from 'node:test';
import assert from 'node:assert/strict';
import {createRound} from '../courses/static/courses/practice.mjs';
test('a round has one unambiguous correct translation',()=>{const entries=[{en:'Hi',zh:'你好'},{en:'Hello',zh:'你好'},{en:'Bye',zh:'再见'},{en:'Thanks',zh:'谢谢'}];const round=createRound(entries,0);assert.equal(round.prompt,'Hi');assert.equal(new Set(round.choices).size,round.choices.length);assert.equal(round.choices.filter(x=>x===round.answer).length,1);assert.equal(round.choices.length,3);});
test('not enough distinct choices yields no quiz',()=>{assert.equal(createRound([{en:'Hi',zh:'你好'},{en:'Hello',zh:'你好'}],0),null);});
