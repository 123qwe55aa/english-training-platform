import {STORAGE_KEY, beijingDay, normalizeJournal, awardTask, dailyPoints, meterState, readRewardStorage, storeReward, VideoWatchTracker, migrateLegacyRewards} from './jason-core.mjs?v=20261018-students1';
const dock = document.querySelector('[data-jason-meter]');
if (dock) {
  let config=JSON.parse(document.querySelector('#reward-config').textContent);
  const scope=`hello-friends:rewards:v2:student-${config.studentId}`;
  let journal = normalizeJournal(null);
  let storageAvailable = true;
  const warning = dock.querySelector('[data-jason-storage-warning]');
  function storageWarning() {
    storageAvailable = false;
    warning.hidden = false;
    warning.textContent = '浏览器暂时无法保存奖励，本页仍可累计；离开页面后可能丢失。';
  }
  function readJournal() {
    if (!storageAvailable) return;
    try {
      journal = readRewardStorage(window.localStorage,scope);
    } catch { storageWarning(); }
  }
  function saveReward(day, id, title, points) {
    if (!storageAvailable) return;
    try { storeReward(window.localStorage, day, id, title, points, scope); readJournal(); }
    catch { storageWarning(); }
  }
  const dialogueButtons = [...document.querySelectorAll('[data-jason-dialogue]')];
  const videoBadges = [...document.querySelectorAll('[data-jason-video-status]')];
  function render() {
    const day = beijingDay();
    const state = meterState(dailyPoints(journal, day)+(config.date===day?config.teacherPoints:0),config.goal,config.lowThreshold);
    dock.dataset.level = state.level;
    dock.style.setProperty('--jason-percent', `${state.percent}%`);
    dock.style.setProperty('--jason-low-position',`${config.lowThreshold/config.goal*100}%`);
    dock.querySelector('[data-jason-goal]').textContent=config.goal;
    dock.querySelector('[data-jason-label]').textContent = state.label;
    dock.querySelector('[data-jason-points]').textContent = state.points;
    const progress = dock.querySelector('[data-jason-progress]');
    progress.setAttribute('aria-valuenow', state.points > config.goal ? config.goal : state.points);
    progress.setAttribute('aria-valuemax',config.goal);
    dock.querySelector('[data-jason-teacher-points]').textContent=`老师奖励 ${config.date===day?config.teacherPoints:0} 点 · 此设备练习 ${dailyPoints(journal,day)} 点`;
    progress.setAttribute('aria-valuetext', `${state.points} 点，今日目标 ${config.goal} 点。${state.label}`);
    for (const button of dialogueButtons) {
      const done = Boolean(journal.days[day]?.[button.dataset.jasonDialogue]);
      button.disabled = done;
      button.textContent = done ? `✓ 今日已完成 · +${journal.days[day][button.dataset.jasonDialogue].points} 已获得` : button.dataset.jasonButtonLabel;
    }
    for (const badge of videoBadges) {
      const done = Boolean(journal.days[day]?.[badge.dataset.jasonVideoStatus]);
      badge.textContent = done ? `✓ 今日已看完 · +${journal.days[day][badge.dataset.jasonVideoStatus].points} 已获得` : `看完视频 +${config.videoPoints} ${config.label}`;
      badge.classList.toggle('earned', done);
    }
  }
  const dialog = document.querySelector('[data-jason-dialog]');
  const celebrations = [];
  function showNextCelebration() {
    if (!dialog || dialog.open || !celebrations.length) return;
    const item = celebrations.shift();
    dialog.querySelector('[data-jason-reward-title]').textContent = item.title;
    dialog.querySelector('[data-jason-reward-total]').textContent = item.total;
    dialog.querySelector('[data-jason-gain]').textContent=item.points;
    dialog.querySelector('[data-jason-reward-message]').textContent = item.total > config.goal ? '，超额完成，持续充能！' : item.total === config.goal ? '，今天的目标达成了！' : '，每一点努力都算数。';
    dialog.showModal();
  }
  dialog?.addEventListener('close', showNextCelebration);
  function award(id, title) {
    // Refresh the saved journal before awarding so another tab's completed tasks persist.
    readJournal();
    const day = beijingDay();
    const points=id.startsWith('video:')?config.videoPoints:config.dialoguePoints;
    const result = awardTask(journal, day, id, title,points);
    journal = result.journal;
    if (result.granted) {
      saveReward(day, id, title, points);
      celebrations.push({title, points,total: Math.max(0,dailyPoints(journal, day)+(config.date===day?config.teacherPoints:0))});
      showNextCelebration();
    }
    render();
  }
  for (const button of dialogueButtons) {
    button.dataset.jasonButtonLabel = button.textContent.trim();
    button.addEventListener('click', () => award(button.dataset.jasonDialogue, button.dataset.jasonTitle || '完成了一轮对话练习'));
  }
  for (const video of document.querySelectorAll('video[data-jason-video]')) {
    const tracker = new VideoWatchTracker();
    const observe = () => tracker.observe({position:video.currentTime,at:new Date(),rate:video.playbackRate,active:!video.paused && !video.seeking});
    for (const event of ['play','playing','timeupdate','pause','ratechange','seeked']) video.addEventListener(event,observe);
    video.addEventListener('seeking', () => tracker.observe({position:video.currentTime,at:new Date(),discontinuity:true}));
    video.addEventListener('emptied', () => { tracker.last = null; tracker.ranges.clear(); });
    video.addEventListener('ended', () => {
      observe();
      if (tracker.complete(video.duration, beijingDay(), video.ended)) {
        award(video.dataset.jasonVideo, `看完了：${video.getAttribute('aria-label') || '一段视频'}`);
      } else {
        const badge = videoBadges.find(b => b.dataset.jasonVideoStatus === video.dataset.jasonVideo);
        if (badge) badge.textContent = `还有片段没看完，补看后再获得 +${config.videoPoints}。`;
      }
    });
  }
  window.addEventListener('storage', event => { if (event.key?.startsWith(`${scope}:`) || event.key === null) { readJournal(); render(); } });
  document.addEventListener('visibilitychange', () => { if (!document.hidden) { readJournal(); render(); } });
  async function refreshTeacherRewards() {
    try {
      const response=await fetch(config.summaryUrl,{cache:'no-store'});
      if (response.ok) { config=await response.json(); render(); }
    } catch { /* Keep the last confirmed teacher award while offline. */ }
  }
  window.setInterval(() => { readJournal(); render(); refreshTeacherRewards(); }, 30000);
  try { migrateLegacyRewards(window.localStorage,scope,config.legacyJason); } catch { storageWarning(); }
  readJournal(); render();
}
