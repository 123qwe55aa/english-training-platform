// Activity rewards are local encouragement, separate from teacher-assessed progress.
export const REWARD = 10;
export const STORAGE_KEY = 'hello-friends:jason:v1';
const taskId = /^(video|dialogue):[a-zA-Z0-9:_-]{1,100}$/;
const dayId = /^\d{4}-\d{2}-\d{2}$/;
export function beijingDay(date = new Date()) {
  return new Date(date.getTime() + 8 * 60 * 60 * 1000).toISOString().slice(0, 10);
}
export function normalizeJournal(raw) {
  const journal = {version: 1, days: {}};
  if (!raw || raw.version !== 1 || !raw.days || typeof raw.days !== 'object') return journal;
  for (const day of Object.keys(raw.days).filter(d => dayId.test(d)).sort().slice(-14)) {
    const rewards = raw.days[day];
    if (!rewards || typeof rewards !== 'object') continue;
    journal.days[day] = {};
    for (const [id, reward] of Object.entries(rewards)) {
      if (taskId.test(id) && reward && Number.isInteger(reward.points) && reward.points > 0 && reward.points <= 1000 && typeof reward.title === 'string') {
        journal.days[day][id] = {points: reward.points, title: reward.title.slice(0, 180)};
      }
    }
  }
  return journal;
}
export function dailyPoints(journal, day) {
  return Object.values(journal.days[day] || {}).reduce((sum,reward) => sum+reward.points,0);
}
export function awardTask(raw, day, id, title, points=REWARD) {
  const journal = normalizeJournal(raw);
  if (!Number.isInteger(points) || points < 1 || points > 1000 || !dayId.test(day) || !taskId.test(id) || journal.days[day]?.[id]) {
    return {journal, granted: false, total: dailyPoints(journal, day)};
  }
  journal.days[day] ||= {};
  journal.days[day][id] = {points, title: String(title).slice(0, 180)};
  return {journal, granted: true, total: dailyPoints(journal, day)};
}
export function meterState(rawPoints,goal=100,lowThreshold=20) {
  const points = Number.isFinite(rawPoints) ? Math.max(0, rawPoints) : 0;
  const level = points < lowThreshold ? 'low' : points < goal/2 ? 'building' : points < goal ? 'halfway' : points === goal ? 'reached' : 'charging';
  const labels = {low: '能量不足，先来一个小任务', building: '能量上升，每一步都算数', halfway: '已过半格，继续积攒小胜利', reached: '今日目标达成！', charging: '超额完成，持续充能中！'};
  return {points, percent: Math.min(points/goal*100, 100), level, label: labels[level]};
}
export function videoComplete(duration, playedRanges, ended) {
  if (!ended || !Number.isFinite(duration) || duration <= 0) return false;
  const ranges = playedRanges.filter(r => Array.isArray(r) && r.length === 2 && r.every(Number.isFinite) && r[1] > r[0])
    .map(([a,b]) => [Math.max(0,a), Math.min(duration,b)]).sort((a,b) => a[0]-b[0]);
  let watched = 0, end = 0;
  for (const [a,b] of ranges) {
    if (b > end) { watched += Math.max(0, b - Math.max(a,end)); end = b; }
  }
  return watched / duration >= 0.9;
}
// Each task has its own storage key: two tabs cannot overwrite each other's tasks.
export function readRewardStorage(storage,scope=STORAGE_KEY) {
  const days = {};
  const prefix = `${scope}:`;
  for (let i = 0; i < storage.length; i++) {
    const key = storage.key(i);
    if (!key?.startsWith(prefix)) continue;
    const suffix = key.slice(prefix.length), day = suffix.slice(0,10), id = suffix.slice(11);
    if (suffix[10] !== ':' || !dayId.test(day) || !taskId.test(id)) continue;
    let reward;
    try { reward = JSON.parse(storage.getItem(key)); } catch { continue; }
    days[day] ||= {};
    days[day][id] = reward;
  }
  return normalizeJournal({version:1, days});
}
export function storeReward(storage, day, id, title,points=REWARD,scope=STORAGE_KEY) {
  if (!dayId.test(day) || !taskId.test(id) || !Number.isInteger(points) || points<1 || points>1000) return;
  storage.setItem(`${scope}:${day}:${id}`, JSON.stringify({points, title:String(title).slice(0,180)}));
}

export class VideoWatchTracker {
  constructor() { this.ranges = new Map(); this.last = null; }
  addRange(day, start, end) {
    if (!(end > start)) return;
    const ranges = this.ranges.get(day) || [];
    const last = ranges.at(-1);
    if (last && start <= last[1] && end >= last[0]) { last[0] = Math.min(last[0],start); last[1] = Math.max(last[1],end); }
    else ranges.push([start,end]);
    this.ranges.set(day,ranges);
  }
  observe({position, at, rate=1, active=true, discontinuity=false}) {
    if (discontinuity || !Number.isFinite(position) || !Number.isFinite(at.getTime())) { this.last = null; return; }
    const day = beijingDay(at), epoch = at.getTime();
    const previous = this.last;
    if (previous?.active) {
      const elapsed = (epoch - previous.epoch) / 1000;
      const distance = position - previous.position;
      const possible = elapsed * Math.max(previous.rate,rate) + 0.75;
      if (elapsed >= 0 && distance > 0 && distance <= possible) {
        if (previous.day === day) this.addRange(day,previous.position,position);
        else {
          const midnight = Date.parse(`${day}T00:00:00+08:00`);
          const fraction = Math.max(0,Math.min(1,(midnight-previous.epoch)/(epoch-previous.epoch)));
          const boundary = previous.position + distance*fraction;
          this.addRange(previous.day,previous.position,boundary);
          this.addRange(day,boundary,position);
        }
      }
    }
    this.last = {position,epoch,rate,active,day};
  }
  complete(duration, day, ended) { return videoComplete(duration,this.ranges.get(day) || [],ended); }
}

export function migrateLegacyRewards(storage,scope,isLegacy=false) {
  if (!isLegacy) return;
  const old=readRewardStorage(storage);
  for (const [day,rewards] of Object.entries(old.days)) {
    for (const [id,reward] of Object.entries(rewards)) {
      if (!storage.getItem(`${scope}:${day}:${id}`)) storeReward(storage,day,id,reward.title,reward.points,scope);
    }
  }
}
