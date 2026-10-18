document.querySelectorAll('[data-official-quiz]').forEach(card => {
  card.querySelector('[data-check-answer]').addEventListener('click', () => {
    const selected = card.querySelector('input:checked');
    const feedback = card.querySelector('[data-official-feedback]');
    if (!selected) { feedback.textContent = '先选一个答案，再核对。'; return; }
    const correct = selected.value === card.dataset.answer;
    feedback.textContent = correct ? '答对了！再说一句你听到的内容。' : '再听一次，留意问题里的关键词。';
    card.querySelector('.official-explanation').hidden = !correct;
    card.querySelectorAll('.official-option').forEach(label => label.classList.toggle('chosen-correct', correct && label.querySelector('input').checked));
  });
});
