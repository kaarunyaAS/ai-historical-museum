const artifactGrid = document.getElementById('artifact-grid');
const detailPanel = document.getElementById('artifact-detail');
const chatHistory = document.getElementById('chat-history');
const chatForm = document.getElementById('chat-form');
const chatInput = document.getElementById('chat-input');
const activeArtifactLabel = document.getElementById('active-artifact-label');
const chatStatus = document.getElementById('chat-status');
const suggestionList = document.getElementById('suggestion-list');
const artifactCount = document.getElementById('artifact-count');

const artifactImages = {
  nataraja: 'https://images.unsplash.com/photo-1577083552431-6e5fd6740b57?auto=format&fit=crop&w=1200&q=80',
  dancing_girl: 'https://images.unsplash.com/photo-1517404215738-15263e9f9178?auto=format&fit=crop&w=1200&q=80',
  lion_capital: 'https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=1200&q=80',
  konark_wheel: 'https://images.unsplash.com/photo-1526481280695-3c4691b0d50c?auto=format&fit=crop&w=1200&q=80',
  gandharan_buddha: 'https://images.unsplash.com/photo-1524492412937-b28074a5d7da?auto=format&fit=crop&w=1200&q=80',
  sanchi_torana: 'https://images.unsplash.com/photo-1516589178581-6cd7833ae3b2?auto=format&fit=crop&w=1200&q=80',
  mughal_miniature: 'https://images.unsplash.com/photo-1460661419201-fd4cecdf8a8b?auto=format&fit=crop&w=1200&q=80',
  tipu_sword: 'https://images.unsplash.com/photo-1541961017774-22349e4a1262?auto=format&fit=crop&w=1200&q=80',
  harappan_figurine: 'https://images.unsplash.com/photo-1501785888041-af3ef285b470?auto=format&fit=crop&w=1200&q=80',
  elephanta_trimurti: 'https://images.unsplash.com/photo-1523800503107-5bc3ba2a6f81?auto=format&fit=crop&w=1200&q=80'
};

const languageConfig = {
  en: {
    label: 'English',
    suggestions: [
      'What is the artistic significance of the Nataraja?',
      'How did the Indus Valley tradition shape early urban art?',
      'Compare the Lion Capital and the Konark Wheel.',
      'Why is the Sanchi torana important in Buddhist art?'
    ]
  },
  ta: {
    label: 'தமிழ்',
    suggestions: [
      'நடராஜரின் கலை முக்கியத்துவம் என்ன?',
      'சிந்து வெளி நாகரிகம் ஆரம்பகால நகரக் கலையை எப்படி வடிவமைத்தது?',
      'சிங்கத் தலைப்பு மற்றும் கோனார்க் சக்கரம் எவ்வாறு ஒப்பிடப்படுகின்றன?',
      'பௌத்தக் கலையில் சாஞ்சி தோரணா ஏன் முக்கியமானது?'
    ]
  },
  hi: {
    label: 'हिन्दी',
    suggestions: [
      'नटराज की कलात्मक महत्ता क्या है?',
      'सिंधु घाटी की संस्कृति ने प्रारंभिक नगर कला को कैसे आकार दिया?',
      'सिंह शीर्ष और कोणार्क चक्र की तुलना करें।',
      'बौद्ध कला में सांची तोरणा क्यों महत्वपूर्ण है?'
    ]
  }
};

let selectedArtifact = null;
let language = 'en';
let conversationHistory = [];

function setStatus(message, isError = false) {
  chatStatus.textContent = message;
  chatStatus.classList.toggle('hidden', !message);
  chatStatus.classList.toggle('is-error', isError);
}

function updateSuggestions() {
  const suggestions = languageConfig[language]?.suggestions || languageConfig.en.suggestions;
  suggestionList.innerHTML = suggestions
    .map((question) => `<button class="suggestion-chip" type="button" data-question="${escapeHtml(question)}">${question}</button>`)
    .join('');

  suggestionList.querySelectorAll('.suggestion-chip').forEach((button) => {
    button.addEventListener('click', () => {
      const value = button.dataset.question;
      chatInput.value = value;
      chatForm.requestSubmit();
    });
  });
}

function escapeHtml(value) {
  return value
    .replace(/&/g, '&amp;')
    .replace(/"/g, '&quot;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/'/g, '&#039;');
}

function renderArtifactCard(artifact) {
  const card = document.createElement('button');
  card.type = 'button';
  card.className = 'artifact-card';
  card.dataset.slug = artifact.slug;

  const imageUrl = artifactImages[artifact.slug] || 'https://images.unsplash.com/photo-1518998053901-5348d8a0e3d6?auto=format&fit=crop&w=900&q=80';
  const isSelected = artifact.slug === selectedArtifact;
  if (isSelected) {
    card.classList.add('active');
  }

  card.innerHTML = `
    <img src="${imageUrl}" alt="${artifact.name}" loading="lazy" />
    <div class="card-copy">
      <div class="card-meta">
        <span class="card-id">${artifact.id}</span>
      </div>
      <h3>${artifact.name}</h3>
      <p>${artifact.description}</p>
    </div>
  `;

  card.addEventListener('click', () => selectArtifact(artifact.slug));
  artifactGrid.appendChild(card);
}

function showEmptyDetail(message = 'Select an artifact to review its history, timeline, and sources.') {
  detailPanel.classList.add('empty');
  detailPanel.innerHTML = `
    <div class="empty-state">
      <h3>No artifact selected</h3>
      <p>${message}</p>
    </div>
  `;
}

function renderTimeline(sections) {
  return `
    <div class="timeline">
      <h3>Historical timeline</h3>
      <ul class="timeline-list">
        ${sections
          .map(
            (section, index) => `
              <li class="timeline-item">
                <div class="timeline-node">${index + 1}</div>
                <div class="timeline-copy">
                  <h4>${section.title}</h4>
                  <p>${section.text}</p>
                </div>
              </li>
            `
          )
          .join('')}
      </ul>
    </div>
  `;
}

function renderSources(sources) {
  return `
    <div class="sources">
      <h3>Source citations</h3>
      <ul class="source-list">
        ${sources
          .map(
            (source) => `
              <li>
                <strong>${source.source_type || 'Reference'}:</strong>
                <a href="${source.url || '#'}" target="_blank" rel="noreferrer">${source.title}</a>
              </li>
            `
          )
          .join('')}
      </ul>
    </div>
  `;
}

async function selectArtifact(slug) {
  if (!slug) {
    selectedArtifact = null;
    activeArtifactLabel.textContent = 'All artifacts';
    showEmptyDetail();
    return;
  }

  selectedArtifact = slug;
  activeArtifactLabel.textContent = `Artifact: ${slug}`;

  document.querySelectorAll('.artifact-card').forEach((card) => {
    card.classList.toggle('active', card.dataset.slug === slug);
  });

  try {
    setStatus('Loading artifact details...');
    const response = await fetch(`/api/artifacts/${slug}`);
    if (!response.ok) {
      throw new Error('Artifact request failed');
    }
    const artifact = await response.json();

    const timelineMarkup = renderTimeline(artifact.sections || []);
    const sourcesMarkup = renderSources(artifact.sources || []);
    detailPanel.classList.remove('empty');
    detailPanel.innerHTML = `
      <div class="detail-header">
        <img class="detail-image" src="${artifactImages[slug] || 'https://images.unsplash.com/photo-1518998053901-5348d8a0e3d6?auto=format&fit=crop&w=1200&q=80'}" alt="${artifact.name}" />
        <div class="detail-meta">
          <p class="section-kicker">Artifact profile</p>
          <h2>${artifact.name}</h2>
          <p class="detail-summary">${artifact.description}</p>
          <div class="detail-tags">
            <span class="detail-tag">${artifact.id}</span>
            <span class="detail-tag">${(artifact.sources || []).length} sources</span>
            <span class="detail-tag">${(artifact.sections || []).length} sections</span>
          </div>
        </div>
      </div>
      <div class="detail-sections">
        ${((artifact.sections || []).map((section) => `
          <article class="section-card">
            <h3>${section.title}</h3>
            <p>${section.text}</p>
          </article>
        `)).join('')}
      </div>
      ${timelineMarkup}
      ${sourcesMarkup}
    `;

    setStatus('');
  } catch (error) {
    setStatus('Unable to load this artifact. Please try another selection.', true);
    showEmptyDetail('The historical record for this object could not be loaded.');
  }
}

function renderMessageText(text) {
  const value = String(text ?? '').replace(/\r\n/g, '\n');
  const escaped = escapeHtml(value)
    .replace(/\n{2,}/g, '</p><p>')
    .replace(/\n/g, '<br>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/• /g, '<br>• ');

  return `<p>${escaped}</p>`;
}

function appendMessage(role, text, citations = []) {
  const message = document.createElement('div');
  message.className = `message ${role}`;
  const label = role === 'user' ? 'You' : 'MuseumAI';
  const citationsMarkup = citations.length
    ? `<div class="message-citations">Sources: ${citations.map((item) => item.title || item.source_id).join(', ')}</div>`
    : '';

  message.innerHTML = `
    <span class="message-header">${label}</span>
    <div>${renderMessageText(text)}</div>
    ${citationsMarkup}
  `;

  chatHistory.appendChild(message);
  chatHistory.scrollTop = chatHistory.scrollHeight;
}

async function askQuestion(question) {
  if (!question || !question.trim()) {
    return;
  }

  const trimmed = question.trim();
  conversationHistory.push({ role: 'user', text: trimmed });
  appendMessage('user', trimmed);
  chatInput.value = '';
  setStatus('Thinking with the museum archive...');

  try {
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        question: trimmed,
        artifact_id: selectedArtifact,
        language,
        conversation_history: conversationHistory.slice(-6)
      })
    });

    if (!response.ok) {
      throw new Error('Chat request failed');
    }

    const payload = await response.json();
    const answer = payload.answer || 'No answer returned from the archive yet.';
    const citations = payload.citations || payload.sources || [];
    conversationHistory.push({ role: 'bot', text: answer });
    appendMessage('bot', answer, citations);
    setStatus('');
  } catch (error) {
    conversationHistory.push({ role: 'bot', text: 'The museum guide is temporarily unavailable. Please try another question or select a different artifact.' });
    appendMessage('bot', 'The museum guide is temporarily unavailable. Please try another question or select a different artifact.');
    setStatus('The AI guide could not answer that request. Please try again.', true);
  }
}

async function loadArtifacts() {
  try {
    setStatus('Loading museum collection...');
    const response = await fetch('/api/artifacts');
    if (!response.ok) {
      throw new Error('Artifact listing failed');
    }

    const payload = await response.json();
    const list = payload.artifacts || [];
    artifactGrid.innerHTML = '';
    artifactCount.textContent = String(list.length || 0);

    if (!list.length) {
      artifactGrid.innerHTML = '<div class="empty-state"><h3>No artifacts available</h3><p>The collection is empty.</p></div>';
      showEmptyDetail('The MuseumAI archive is empty right now.');
      setStatus('No artifacts available in the archive.', true);
      return;
    }

    list.forEach((artifact) => renderArtifactCard(artifact));
    const firstArtifact = list[0].slug;
    selectArtifact(firstArtifact);
    setStatus('');
  } catch (error) {
    artifactGrid.innerHTML = '<div class="empty-state"><h3>Collection unavailable</h3><p>The museum archive could not be reached.</p></div>';
    showEmptyDetail('The museum archive could not be reached. Please refresh the page.');
    setStatus('The museum archive could not be reached.', true);
  }
}

chatForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const question = chatInput.value.trim();
  if (!question) {
    chatInput.focus();
    return;
  }

  await askQuestion(question);
});

document.querySelectorAll('.lang').forEach((button) => {
  button.addEventListener('click', () => {
    document.querySelectorAll('.lang').forEach((item) => item.classList.toggle('active', item === button));
    language = button.dataset.language;
    updateSuggestions();
    appendMessage('bot', `Language switched to ${languageConfig[language]?.label || 'English'}.`);
    setStatus('');
  });
});

updateSuggestions();
showEmptyDetail();
loadArtifacts();
