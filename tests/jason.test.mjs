import test from 'node:test';
import assert from 'node:assert/strict';
import {beijingDay, normalizeJournal, awardTask, dailyPoints, meterState, videoComplete} from '../courses/static/courses/jason-core.mjs';

test('daily rewards roll over at midnight in Beijing, independently of browser timezone',()=>{
 assert.equal(beijingDay(new Date('2026-10-18T15:59:59Z')),'2026-10-18');
 assert.equal(beijingDay(new Date('2026-10-18T16:00:00Z')),'2026-10-19');
});
test('one task earns ten once per day, while a different task and next day earn again',()=>{
 let journal=normalizeJournal(null);
 let result=awardTask(journal,'2026-10-18','video:lesson1-main','Lesson 1');
 assert.equal(result.granted,true);assert.equal(result.total,10);journal=result.journal;
 result=awardTask(journal,'2026-10-18','video:lesson1-main','Lesson 1');
 assert.equal(result.granted,false);assert.equal(result.total,10);
 result=awardTask(journal,'2026-10-18','dialogue:lesson-1','角色对话');
 assert.equal(result.total,20);journal=result.journal;
 result=awardTask(journal,'2026-10-19','video:lesson1-main','Lesson 1');
 assert.equal(result.total,10);assert.equal(dailyPoints(result.journal,'2026-10-18'),20);
});
test('stored rewards survive serialization and invalid or inflated records are discarded',()=>{
 const result=awardTask(normalizeJournal(null),'2026-10-18','dialogue:lesson-1','Hello');
 assert.equal(dailyPoints(normalizeJournal(JSON.parse(JSON.stringify(result.journal))),'2026-10-18'),10);
 const bad={version:1,days:{'2026-10-18':{'video:main':{points:9999,title:'Fake'},'bad-id':{points:10,title:'Fake'}}}};
 assert.equal(dailyPoints(normalizeJournal(bad),'2026-10-18'),0);
});
test('meter shows the requested low, half, full and continuously charging thresholds',()=>{
 assert.deepEqual([0,10,19].map(n=>meterState(n).level),['low','low','low']);
 assert.equal(meterState(20).level,'building');
 assert.equal(meterState(50).percent,50);assert.equal(meterState(50).level,'halfway');
 assert.equal(meterState(100).level,'reached');
 assert.equal(meterState(110).level,'charging');assert.equal(meterState(110).percent,100);assert.equal(meterState(110).points,110);
});
test('video must end with at least 90 percent watched; seeking to end and repeat overlap do not count',()=>{
 assert.equal(videoComplete(100,[[0,95]],true),true);
 assert.equal(videoComplete(100,[[99,100]],true),false);
 assert.equal(videoComplete(100,[[0,60],[0,60]],true),false);
 assert.equal(videoComplete(100,[[0,45],[44,92]],true),true);
 assert.equal(videoComplete(100,[[0,95]],false),false);
 assert.equal(videoComplete(Infinity,[[0,100]],true),false);
});

test('independent task storage preserves rewards from two tabs even with stale starting snapshots',async()=>{
 const {readRewardStorage,storeReward}=await import('../courses/static/courses/jason-core.mjs');
 const map=new Map();const storage={get length(){return map.size;},key:i=>[...map.keys()][i],getItem:key=>map.get(key)??null,setItem:(key,value)=>map.set(key,value)};
 const tabA=readRewardStorage(storage),tabB=readRewardStorage(storage);
 assert.equal(dailyPoints(tabA,'2026-10-18'),0);assert.equal(dailyPoints(tabB,'2026-10-18'),0);
 storeReward(storage,'2026-10-18','video:one','One');storeReward(storage,'2026-10-18','dialogue:lesson-1','Dialogue');
 assert.equal(dailyPoints(readRewardStorage(storage),'2026-10-18'),20);
 storeReward(storage,'2026-10-18','video:one','One');
 assert.equal(dailyPoints(readRewardStorage(storage),'2026-10-18'),20);
});

test('yesterday watched ranges cannot earn today by replaying only the ending',async()=>{
 const {VideoWatchTracker}=await import('../courses/static/courses/jason-core.mjs');
 const tracker=new VideoWatchTracker();
 const observe=(position,iso,active=true,discontinuity=false)=>tracker.observe({position,at:new Date(iso),active,discontinuity});
 observe(0,'2026-10-18T10:00:00Z');observe(100,'2026-10-18T10:01:40Z',false);
 assert.equal(tracker.complete(100,'2026-10-18',true),true);
 observe(99,'2026-10-19T01:00:00Z',false,true);observe(99,'2026-10-19T01:00:01Z');observe(100,'2026-10-19T01:00:02Z',false);
 assert.equal(tracker.complete(100,'2026-10-19',true),false);
 observe(0,'2026-10-19T01:01:00Z',false,true);observe(0,'2026-10-19T01:01:01Z');observe(100,'2026-10-19T01:02:41Z',false);
 assert.equal(tracker.complete(100,'2026-10-19',true),true);
});
test('video time crossing Beijing midnight is divided between the two dates',async()=>{
 const {VideoWatchTracker}=await import('../courses/static/courses/jason-core.mjs');
 const tracker=new VideoWatchTracker();
 tracker.observe({position:0,at:new Date('2026-10-18T15:59:30Z')});
 tracker.observe({position:60,at:new Date('2026-10-18T16:00:30Z')});
 tracker.observe({position:100,at:new Date('2026-10-18T16:01:10Z'),active:false});
 assert.equal(tracker.complete(100,'2026-10-18',true),false);
 assert.equal(tracker.complete(100,'2026-10-19',true),false);
 assert.equal(tracker.ranges.get('2026-10-18')[0][1],30);
 assert.equal(tracker.ranges.get('2026-10-19')[0][0],30);
});
test('a large playback-time jump does not count as real watch time',async()=>{
 const {VideoWatchTracker}=await import('../courses/static/courses/jason-core.mjs');
 const tracker=new VideoWatchTracker();
 tracker.observe({position:0,at:new Date('2026-10-18T10:00:00Z')});
 tracker.observe({position:100,at:new Date('2026-10-18T10:00:01Z'),active:false});
 assert.equal(tracker.complete(100,'2026-10-18',true),false);
});

test('custom task points and goals are retained, while student storage stays isolated',async()=>{
 const core=await import('../courses/static/courses/jason-core.mjs');
 const map=new Map();const storage={get length(){return map.size;},key:i=>[...map.keys()][i],getItem:k=>map.get(k)??null,setItem:(k,v)=>map.set(k,v)};
 core.storeReward(storage,'2026-10-18','video:one','One',5,'student-lily');
 core.storeReward(storage,'2026-10-18','dialogue:one','Talk',15,'student-lily');
 core.storeReward(storage,'2026-10-18','video:one','One',10,'student-jason');
 assert.equal(core.dailyPoints(core.readRewardStorage(storage,'student-lily'),'2026-10-18'),20);
 assert.equal(core.dailyPoints(core.readRewardStorage(storage,'student-jason'),'2026-10-18'),10);
 assert.equal(core.meterState(30,60,10).percent,50);
 assert.equal(core.awardTask(core.normalizeJournal(null),'2026-10-18','video:new','New',5).total,5);
});
test('only Jason imports old unscoped rewards, once without deleting the originals',async()=>{
 const core=await import('../courses/static/courses/jason-core.mjs');
 const map=new Map();const storage={get length(){return map.size;},key:i=>[...map.keys()][i],getItem:k=>map.get(k)??null,setItem:(k,v)=>map.set(k,v)};
 core.storeReward(storage,'2026-10-18','video:one','Legacy');
 core.migrateLegacyRewards(storage,'new-lily',false);
 assert.equal(core.dailyPoints(core.readRewardStorage(storage,'new-lily'),'2026-10-18'),0);
 core.migrateLegacyRewards(storage,'new-jason',true);core.migrateLegacyRewards(storage,'new-jason',true);
 assert.equal(core.dailyPoints(core.readRewardStorage(storage,'new-jason'),'2026-10-18'),10);
 assert.equal(core.dailyPoints(core.readRewardStorage(storage),'2026-10-18'),10);
});
