export function createRound(entries,index){
 const unique=entries.filter((e,i,a)=>e&&typeof e.en==='string'&&typeof e.zh==='string'&&a.findIndex(x=>x.zh===e.zh)===i);
 if(unique.length<2)return null;
 const target=unique[index%unique.length];
 const choices=[target.zh,...unique.filter(e=>e.zh!==target.zh).slice(0,2).map(e=>e.zh)];
 const offset=index%choices.length;
 return {prompt:target.en,answer:target.zh,choices:[...choices.slice(offset),...choices.slice(0,offset)]};
}
if(typeof document!=='undefined'){
 const root=document.querySelector('[data-practice]');
 if(root){
 const entries=JSON.parse(document.querySelector('#practice-data').textContent);
 const prompt=root.querySelector('[data-question]'),choices=root.querySelector('[data-choices]'),feedback=root.querySelector('[data-feedback]'),next=root.querySelector('[data-next]');
 let index=0;
 function render(){const round=createRound(entries,index);if(!round){root.hidden=true;return;}prompt.textContent=round.prompt;choices.replaceChildren();feedback.textContent='选出这句话的意思。选错也没关系，再试一次。';next.hidden=true;
 for(const text of round.choices){const button=document.createElement('button');button.type='button';button.className='quiz-choice';button.textContent=text;button.addEventListener('click',()=>{if(text===round.answer){feedback.textContent='✓ 连上了！现在试着把英文说给老师听。';button.classList.add('correct');next.hidden=false;choices.querySelectorAll('button').forEach(b=>b.disabled=true);}else{feedback.textContent='这一次还没连上。可以先看句卡，听老师示范，再试一次。';button.classList.add('retry');button.disabled=true;}});choices.append(button);}}
 next.addEventListener('click',()=>{index++;render();});render();
 }
}
