// MediKiosk Client Application Logic

const API_BASE = window.location.origin;

const state = {
  currentLanguage: 'hi', // default to Hindi per SIH demo
  audioNarration: true,
  isRecording: false,
  recognition: null,
  activeView: 'kiosk',
  kioskStep: 'welcome',
  patient: {
    id: 'p_001',
    name: 'Smt. Shanti Devi',
    age: 62,
    gender: 'Female',
    abha_id: '91-8822-1144-5566',
    phone: '+919876543210'
  },
  sessionId: null,
  currentQuestion: null,
  selectedAnswers: [],
  activeSummaryId: 'sum_demo_01',
  doctorQueue: []
};

// Initialize App
document.addEventListener('DOMContentLoaded', () => {
  initSpeechRecognition();
  updateLanguageDisplay();
  refreshDoctorQueue();
  lucide.createIcons();
});

// ==================== SPEECH API (VOICE INPUT & OUTPUT) ====================

function initSpeechRecognition() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    console.warn('Web Speech API not supported in this browser. Falling back to tactile cards.');
    const micBtn = document.getElementById('btnMicInput');
    if (micBtn) micBtn.title = 'Speech recognition not available on this browser';
    return;
  }

  state.recognition = new SpeechRecognition();
  state.recognition.continuous = false;
  state.recognition.interimResults = true;

  state.recognition.onstart = () => {
    state.isRecording = true;
    const micBtn = document.getElementById('btnMicInput');
    if (micBtn) micBtn.classList.add('recording-pulse');
    setLiveTranscript('Listening... Speak now (कृपया बोलें)...');
  };

  state.recognition.onresult = (event) => {
    let transcript = '';
    for (let i = event.resultIndex; i < event.results.length; ++i) {
      transcript += event.results[i][0].transcript;
    }
    setLiveTranscript(transcript);

    if (event.results[0].isFinal) {
      handleFinalVoiceTranscript(transcript);
    }
  };

  state.recognition.onerror = (event) => {
    console.warn('Speech recognition error:', event.error);
    stopRecordingUI();
    setLiveTranscript('Voice input stopped. You can tap options above.');
  };

  state.recognition.onend = () => {
    stopRecordingUI();
  };
}

function stopRecordingUI() {
  state.isRecording = false;
  const micBtn = document.getElementById('btnMicInput');
  if (micBtn) micBtn.classList.remove('recording-pulse');
}

function toggleVoiceInput() {
  if (!state.recognition) {
    alert('Speech recognition is not supported in this browser. Please tap the options on screen.');
    return;
  }

  if (state.isRecording) {
    state.recognition.stop();
  } else {
    // Set speech recognition language
    state.recognition.lang = state.currentLanguage === 'hi' ? 'hi-IN' : 'en-IN';
    try {
      state.recognition.start();
    } catch (e) {
      console.warn('Recognition start error:', e);
    }
  }
}

function setLiveTranscript(txt) {
  const el = document.getElementById('txtLiveTranscript');
  if (el) el.innerText = txt;
}

function speakText(text, lang = null) {
  if (!state.audioNarration || !('speechSynthesis' in window)) return;
  window.speechSynthesis.cancel(); // clear previous
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = lang || (state.currentLanguage === 'hi' ? 'hi-IN' : 'en-IN');
  utterance.rate = 0.95; // Clear pace for elderly patients
  window.speechSynthesis.speak(utterance);
}

function toggleAudioNarration() {
  state.audioNarration = !state.audioNarration;
  const btn = document.getElementById('btnTtsToggle');
  if (state.audioNarration) {
    btn.classList.add('text-sky-600', 'bg-sky-50');
    speakText(state.currentLanguage === 'hi' ? 'आवाज मार्गदर्शन चालू है।' : 'Voice guidance enabled.');
  } else {
    btn.classList.remove('text-sky-600', 'bg-sky-50');
    window.speechSynthesis.cancel();
  }
}

// ==================== ACCESSIBILITY & LOCALIZATION ====================

function toggleLanguage() {
  state.currentLanguage = state.currentLanguage === 'hi' ? 'en' : 'hi';
  updateLanguageDisplay();
  if (state.currentQuestion) {
    renderQuestion(state.currentQuestion);
  }
}

function updateLanguageDisplay() {
  const lbl = document.getElementById('lblLang');
  if (lbl) {
    lbl.innerText = state.currentLanguage === 'hi' ? 'हिन्दी (Hindi)' : 'English';
  }
  const welcomeTitle = document.getElementById('txtWelcomeTitle');
  const welcomeSub = document.getElementById('txtWelcomeSubtitle');
  if (welcomeTitle && welcomeSub) {
    if (state.currentLanguage === 'hi') {
      welcomeTitle.innerText = 'मेडीकियोस्क (MediKiosk) में आपका स्वागत है';
      welcomeSub.innerText = 'डॉक्टर से मिलने से पहले बोलकर या छूकर आसान सवालों के जवाब दें। अपनी पुरानी पर्चियां अपलोड करें और तुरंत सहायता पाएं।';
    } else {
      welcomeTitle.innerText = 'Welcome to MediKiosk';
      welcomeSub.innerText = 'Answer simple questions by voice or touch before meeting the doctor. Upload old prescriptions and get instant priority triage.';
    }
  }
}

function toggleHighContrast() {
  document.body.classList.toggle('high-contrast');
}

function toggleLargeFont() {
  document.body.classList.toggle('large-text');
}

// ==================== VIEW SWITCHING ====================

function switchView(viewName) {
  state.activeView = viewName;

  document.getElementById('viewKiosk').classList.add('hidden');
  document.getElementById('viewDoctor').classList.add('hidden');
  document.getElementById('viewPatient').classList.add('hidden');

  document.getElementById('navKiosk').classList.remove('bg-white', 'text-sky-700', 'shadow-sm');
  document.getElementById('navDoctor').classList.remove('bg-white', 'text-sky-700', 'shadow-sm');
  document.getElementById('navPatient').classList.remove('bg-white', 'text-sky-700', 'shadow-sm');

  if (viewName === 'kiosk') {
    document.getElementById('viewKiosk').classList.remove('hidden');
    document.getElementById('navKiosk').classList.add('bg-white', 'text-sky-700', 'shadow-sm');
  } else if (viewName === 'doctor') {
    document.getElementById('viewDoctor').classList.remove('hidden');
    document.getElementById('navDoctor').classList.add('bg-white', 'text-sky-700', 'shadow-sm');
    refreshDoctorQueue();
    selectDoctorPatient(state.activeSummaryId);
  } else if (viewName === 'patient') {
    document.getElementById('viewPatient').classList.remove('hidden');
    document.getElementById('navPatient').classList.add('bg-white', 'text-sky-700', 'shadow-sm');
    loadPatientPhr();
  }
  lucide.createIcons();
}

function goToKioskStep(step) {
  state.kioskStep = step;
  ['Welcome', 'Consent', 'Interview', 'Documents', 'Confirm'].forEach(s => {
    const el = document.getElementById(`kioskStep${s}`);
    if (el) el.classList.add('hidden');
  });

  const target = document.getElementById(`kioskStep${step.charAt(0).toUpperCase() + step.slice(1)}`);
  if (target) target.classList.remove('hidden');
  lucide.createIcons();
}

// ==================== KIOSK AUTH & SCENARIOS ====================

async function loginAbha() {
  const abhaId = document.getElementById('inpAbhaId').value.trim();
  const otp = document.getElementById('inpAbhaOtp').value.trim();

  try {
    const res = await fetch(`${API_BASE}/auth/abha-login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ abha_id: abhaId, otp: otp })
    });
    const data = await res.json();
    if (res.ok) {
      state.patient = {
        id: data.user_id,
        name: data.name,
        abha_id: data.abha_id,
        age: data.age || 62,
        gender: data.gender || 'Female'
      };
      goToKioskStep('consent');
      speakConsent();
    } else {
      alert(data.detail || 'ABHA login failed');
    }
  } catch (err) {
    console.error(err);
    goToKioskStep('consent');
  }
}

function startDirectKiosk() {
  goToKioskStep('consent');
  speakConsent();
}

function loadScenario(type) {
  if (type === 'chest_pain') {
    state.patient = { id: 'p_001', name: 'Smt. Shanti Devi', abha_id: '91-8822-1144-5566', age: 62, gender: 'Female' };
    state.currentLanguage = 'hi';
  } else if (type === 'fever') {
    state.patient = { id: 'p_002', name: 'Rajesh Kumar', abha_id: '91-9933-2255-7788', age: 28, gender: 'Male' };
    state.currentLanguage = 'en';
  } else {
    state.patient = { id: 'p_003', name: 'Meera Bai', abha_id: '91-7711-3366-9900', age: 45, gender: 'Female' };
    state.currentLanguage = 'hi';
  }
  updateLanguageDisplay();
  goToKioskStep('consent');
  speakConsent();
}

// ==================== CONSENT SCREEN ====================

function speakConsent() {
  const text = state.currentLanguage === 'hi'
    ? 'कृपया ध्यान दें: यह प्रणाली आपकी बीमारी का प्राथमिक विवरण तैयार करने के लिए आपके लक्षणों को दर्ज करती है। क्या आप डॉक्टर को यह विवरण दिखाने की अनुमति देते हैं?'
    : 'Notice: This kiosk records your symptoms to prepare a clinical summary for your doctor under the DPDP Act. Do you consent to proceed?';
  speakText(text);
}

async function submitConsentAndProceed() {
  try {
    await fetch(`${API_BASE}/consent`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        patient_id: state.patient.id,
        storage_consent: document.getElementById('chkStorageConsent').checked,
        doctor_access: document.getElementById('chkDoctorAccess').checked,
        research_consent: document.getElementById('chkResearchConsent').checked
      })
    });
  } catch (e) {
    console.warn('Consent save offline:', e);
  }

  // Start Interview
  startInterviewSession();
}

// ==================== INTERVIEW WORKFLOW ====================

async function startInterviewSession() {
  try {
    const res = await fetch(`${API_BASE}/interview/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        patient_id: state.patient.id,
        language: state.currentLanguage,
        mode: 'standard_and_ayush'
      })
    });
    const data = await res.json();
    state.sessionId = data.session_id;
    state.currentQuestion = data.first_question;
    goToKioskStep('interview');
    renderQuestion(data.first_question);
  } catch (err) {
    console.error(err);
    alert('Failed to start interview session. Ensure backend is running.');
  }
}

function renderQuestion(q) {
  if (!q) {
    // Interview finished -> proceed to document upload
    goToKioskStep('documents');
    return;
  }

  state.currentQuestion = q;
  state.selectedAnswers = [];

  const isHi = state.currentLanguage === 'hi';
  const qText = isHi ? (q.text_hi || q.text_en) : q.text_en;
  const qSection = q.section ? q.section.toUpperCase().replace('_', ' ') : 'CLINICAL INTAKE';

  document.getElementById('lblQuestionSection').innerText = qSection;
  document.getElementById('txtQuestionText').innerText = qText;
  document.getElementById('lblPatientNameDisplay').innerText = `Patient: ${state.patient.name}`;

  // Render Options
  const container = document.getElementById('optionsContainer');
  container.innerHTML = '';

  const options = q.options || [];
  options.forEach(opt => {
    const label = isHi ? (opt.label_hi || opt.label_en) : opt.label_en;
    const card = document.createElement('button');
    card.className = `option-card p-4 rounded-2xl border-2 border-slate-200 hover:border-sky-500 bg-white hover:bg-sky-50/50 text-left transition-all flex items-center space-x-3.5 shadow-sm`;
    card.onclick = () => selectOption(opt.value, card, q.type === 'multi_choice');

    card.innerHTML = `
      <span class="text-2xl">${opt.icon || '🔹'}</span>
      <div class="flex-1">
        <span class="font-bold text-slate-800 text-sm block">${label}</span>
      </div>
    `;
    container.appendChild(card);
  });

  // Automatically read aloud if audio narration is active
  speakCurrentQuestion();
  lucide.createIcons();
}

function speakCurrentQuestion() {
  if (!state.currentQuestion) return;
  const isHi = state.currentLanguage === 'hi';
  const audioText = isHi
    ? (state.currentQuestion.audio_prompt_hi || state.currentQuestion.text_hi)
    : (state.currentQuestion.audio_prompt_en || state.currentQuestion.text_en);
  speakText(audioText);
}

function selectOption(value, cardElement, isMulti) {
  if (isMulti) {
    if (state.selectedAnswers.includes(value)) {
      state.selectedAnswers = state.selectedAnswers.filter(v => v !== value);
      cardElement.classList.remove('border-sky-600', 'bg-sky-50', 'ring-2', 'ring-sky-500');
    } else {
      state.selectedAnswers.push(value);
      cardElement.classList.add('border-sky-600', 'bg-sky-50', 'ring-2', 'ring-sky-500');
    }
  } else {
    // Single choice: select and highlight
    state.selectedAnswers = [value];
    document.querySelectorAll('.option-card').forEach(c => {
      c.classList.remove('border-sky-600', 'bg-sky-50', 'ring-2', 'ring-sky-500');
    });
    cardElement.classList.add('border-sky-600', 'bg-sky-50', 'ring-2', 'ring-sky-500');

    // Auto-advance for rapid touch intake on single choice cards
    setTimeout(() => {
      submitCurrentAnswer();
    }, 400);
  }
}

async function submitCurrentAnswer(voiceText = null) {
  if (!state.sessionId || !state.currentQuestion) return;

  const isMulti = state.currentQuestion.type === 'multi_choice';
  const payloadValue = isMulti ? state.selectedAnswers : state.selectedAnswers[0];

  try {
    const res = await fetch(`${API_BASE}/interview/answer`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: state.sessionId,
        question_id: state.currentQuestion.id,
        answer_value: payloadValue || null,
        voice_transcript: voiceText
      })
    });
    const data = await res.json();

    // Check for Red Flags Alert
    if (data.red_flags && data.red_flags.length > 0) {
      showEmergencyBanner(data.red_flags[0]);
    }

    if (data.completed || !data.next_question) {
      goToKioskStep('documents');
    } else {
      // Update Progress
      const progress = Math.min(100, Math.round((data.current_step / 10) * 100));
      document.getElementById('barInterviewProgress').style.width = `${progress}%`;
      document.getElementById('lblInterviewProgress').innerText = `Step ${data.current_step} of ~10`;
      renderQuestion(data.next_question);
    }
  } catch (err) {
    console.error(err);
  }
}

function handleFinalVoiceTranscript(transcript) {
  setLiveTranscript(`" ${transcript} "`);
  // Attempt intent answer submission
  submitCurrentAnswer(transcript);
}

function showEmergencyBanner(flag) {
  const banner = document.getElementById('globalEmergencyBanner');
  const txt = document.getElementById('txtEmergencyBanner');
  const isHi = state.currentLanguage === 'hi';
  txt.innerText = isHi ? flag.message_hi : flag.message_en;
  banner.classList.remove('hidden');

  // Audible alert
  speakText(isHi ? 'कृपया ध्यान दें: आपके लक्षण गंभीर हैं। तुरंत आपातकालीन काउंटर पर जाएं।' : 'Emergency Alert: Critical symptoms detected. Please report to triage desk.');
}

function dismissEmergencyBanner() {
  document.getElementById('globalEmergencyBanner').classList.add('hidden');
}

// ==================== DOCUMENT AI & UPLOAD ====================

async function loadDemoDoc(docType) {
  const docIdMap = {
    cardiology: 'doc_demo_chest_pain_01',
    lab: 'doc_demo_lab_diabetic_02',
    ayush: 'doc_demo_ayush_slip_03'
  };

  try {
    const res = await fetch(`${API_BASE}/documents/preloaded`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        patient_id: state.patient.id,
        demo_doc_id: docIdMap[docType]
      })
    });
    const data = await res.json();
    renderExtractedDocCard(data.extracted_data);
  } catch (err) {
    console.error(err);
  }
}

async function handleFileUpload(event) {
  const file = event.target.files[0];
  if (!file) return;

  const formData = new FormData();
  formData.append('patient_id', state.patient.id);
  formData.append('file', file);

  try {
    const res = await fetch(`${API_BASE}/documents/upload`, {
      method: 'POST',
      body: formData
    });
    const data = await res.json();
    renderExtractedDocCard(data.extracted_data);
  } catch (err) {
    console.error(err);
  }
}

function renderExtractedDocCard(doc) {
  const container = document.getElementById('extractedDocResults');
  const card = document.createElement('div');
  card.className = 'bg-slate-50 border border-slate-200 rounded-2xl p-4 space-y-3';

  // Badges for abnormal labs
  let labsHtml = '';
  if (doc.lab_tests && doc.lab_tests.length > 0) {
    labsHtml = doc.lab_tests.map(l => `
      <span class="inline-flex items-center space-x-1 px-2.5 py-1 rounded-lg text-xs font-semibold ${l.is_abnormal ? 'bg-red-100 text-red-800 border border-red-200' : 'bg-slate-200 text-slate-700'}">
        <span>${l.name}: ${l.value} ${l.unit}</span>
        ${l.is_abnormal ? '<span class="text-red-600 font-bold ml-1">[' + l.status + ']</span>' : ''}
      </span>
    `).join(' ');
  }

  // Drug Interactions
  let drugInteractionsHtml = '';
  if (doc.drug_interaction_warnings && doc.drug_interaction_warnings.length > 0) {
    drugInteractionsHtml = doc.drug_interaction_warnings.map(di => `
      <div class="bg-red-50 border border-red-200 text-red-800 text-xs p-2.5 rounded-xl font-medium flex items-center space-x-2">
        <i data-lucide="alert-triangle" class="w-4 h-4 text-red-600 flex-shrink-0"></i>
        <span><strong>DRUG INTERACTION:</strong> ${di.pair.join(' + ')} - ${di.description}</span>
      </div>
    `).join('');
  }

  card.innerHTML = `
    <div class="flex items-center justify-between">
      <div class="flex items-center space-x-2">
        <span class="font-bold text-sm text-slate-800">${doc.doc_type}</span>
        <span class="text-xs text-slate-400">(${doc.document_date})</span>
      </div>
      <span class="text-xs bg-emerald-100 text-emerald-800 font-bold px-2 py-0.5 rounded">Confidence: ${Math.round(doc.confidence_overall * 100)}%</span>
    </div>
    <p class="text-xs text-slate-600 font-medium">${doc.hospital_or_doctor}</p>
    ${doc.diagnoses && doc.diagnoses.length > 0 ? `<p class="text-xs text-slate-700"><strong>Extracted Diagnoses:</strong> ${doc.diagnoses.join(', ')}</p>` : ''}
    ${labsHtml ? `<div class="pt-1 flex flex-wrap gap-1.5">${labsHtml}</div>` : ''}
    ${drugInteractionsHtml}
  `;

  container.prepend(card);
  lucide.createIcons();
}

function skipDocumentsAndProceed() {
  generateSummaryAndProceed();
}

async function generateSummaryAndProceed() {
  try {
    const res = await fetch(`${API_BASE}/summary/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        patient_id: state.patient.id,
        session_id: state.sessionId || 'ses_demo_01'
      })
    });
    const data = await res.json();
    state.activeSummaryId = data.summary_id;

    // Display confirmation
    document.getElementById('txtTokenNumber').innerText = data.token_number || 'TK-042';
    document.getElementById('txtPatientSummaryVernacular').innerText = data.summary.patient_vernacular_summary || 'आपकी जानकारी सुरक्षित रूप से दर्ज कर ली गई है।';
    
    const prioBadge = document.getElementById('txtTriagePriority');
    if (data.red_flag_alert) {
      prioBadge.innerText = 'EMERGENCY RED FLAG';
      prioBadge.className = 'font-bold text-red-400';
    } else {
      prioBadge.innerText = 'REGULAR CONSULTATION';
      prioBadge.className = 'font-bold text-emerald-400';
    }

    goToKioskStep('confirm');
    refreshDoctorQueue();
  } catch (err) {
    console.error(err);
    goToKioskStep('confirm');
  }
}

async function wipeSessionAndFinish() {
  if (state.sessionId) {
    try {
      await fetch(`${API_BASE}/session/${state.sessionId}`, { method: 'DELETE' });
    } catch (e) {
      console.warn(e);
    }
  }
  alert('Session completed! Temporary audio and transcript buffers wiped securely per DPDP Act.');
  goToKioskStep('welcome');
}

// ==================== DOCTOR CLINICAL PORTAL ====================

async function refreshDoctorQueue() {
  try {
    const res = await fetch(`${API_BASE}/doctor/queue`);
    const data = await res.json();
    state.doctorQueue = data.queue;

    // Update stats
    document.getElementById('statTotal').innerText = data.count;
    document.getElementById('statRedFlags').innerText = `${data.red_flag_count} (Priority)`;
    document.getElementById('badgeRedFlags').innerText = data.red_flag_count;
    if (data.red_flag_count > 0) {
      document.getElementById('badgeRedFlags').classList.remove('hidden');
    }

    const container = document.getElementById('doctorQueueList');
    container.innerHTML = '';

    data.queue.forEach(item => {
      const card = document.createElement('div');
      const isRed = item.red_flag_alert;
      const isAccepted = item.status === 'accepted';
      card.className = `p-3.5 rounded-xl border cursor-pointer transition-all ${
        isRed ? 'border-red-300 bg-red-50/70 hover:bg-red-100/70' : 'border-slate-200 bg-white hover:bg-slate-50'
      } ${state.activeSummaryId === item.summary_id ? 'ring-2 ring-sky-500' : ''}`;

      card.onclick = () => selectDoctorPatient(item.summary_id);

      card.innerHTML = `
        <div class="flex items-center justify-between mb-1">
          <span class="font-bold text-sm text-slate-900">${item.patient_name}</span>
          <span class="font-mono text-xs font-bold px-2 py-0.5 rounded ${isRed ? 'bg-red-600 text-white' : 'bg-slate-100 text-slate-700'}">${item.token_number}</span>
        </div>
        <p class="text-xs text-slate-600 truncate">${item.chief_complaint}</p>
        <div class="flex items-center justify-between mt-2 pt-2 border-t border-slate-200/60 text-[11px]">
          <span class="text-slate-400">${item.age}Y / ${item.gender}</span>
          <span class="font-semibold ${isAccepted ? 'text-emerald-700' : (isRed ? 'text-red-700 font-bold' : 'text-amber-700')}">
            ${isAccepted ? '✓ Accepted' : (isRed ? '🚨 RED FLAG' : 'Pending')}
          </span>
        </div>
      `;
      container.appendChild(card);
    });

    lucide.createIcons();
  } catch (err) {
    console.error(err);
  }
}

async function selectDoctorPatient(summaryId) {
  state.activeSummaryId = summaryId;
  try {
    const res = await fetch(`${API_BASE}/summary/${summaryId}`);
    const data = await res.json();
    renderInspector(data);
  } catch (err) {
    console.error(err);
  }
}

function renderInspector(data) {
  document.getElementById('inspPatientName').innerText = data.patient_name;
  document.getElementById('inspTokenBadge').innerText = data.token_number;
  document.getElementById('inspPatientMeta').innerText = `${data.age}Y / ${data.gender} | ABHA: ${data.abha_id} | Phone: ${data.phone}`;

  const redBadge = document.getElementById('inspRedFlagBadge');
  if (data.red_flag_alert) {
    redBadge.classList.remove('hidden');
  } else {
    redBadge.classList.add('hidden');
  }

  const container = document.getElementById('inspectorSections');
  container.innerHTML = '';

  const sections = data.summary.sections || {};
  const sectionLabels = {
    chief_complaint: 'Chief Complaint',
    hpi: 'History of Present Illness (SOCRATES)',
    past_medical_surgical: 'Past Medical & Surgical History',
    medications: 'Current Reported & Prescribed Medications',
    allergies: 'Known Allergies',
    prior_investigations: 'Prior Investigations & Abnormal Labs',
    ayush_assessment: 'AYUSH Clinical Assessment (Prakriti / Agni / Koshtha)',
    red_flags_summary: 'Emergency Triage Red-Flag Flags'
  };

  // Drug Interactions Alert in Inspector
  if (data.summary.drug_interaction_warnings && data.summary.drug_interaction_warnings.length > 0) {
    const diAlert = document.createElement('div');
    diAlert.className = 'bg-red-50 border-l-4 border-red-600 p-3 rounded-r-xl text-xs text-red-900 space-y-1';
    diAlert.innerHTML = `
      <div class="font-bold flex items-center space-x-1.5">
        <i data-lucide="alert-octagon" class="w-4 h-4 text-red-600"></i>
        <span>CLINICAL DRUG INTERACTION ALERT</span>
      </div>
      <p>${data.summary.drug_interaction_warnings.map(d => `${d.pair.join(' + ')}: ${d.description}`).join('<br>')}</p>
    `;
    container.appendChild(diAlert);
  }

  for (const [key, label] of Object.entries(sectionLabels)) {
    const val = sections[key];
    if (!val) continue;

    const box = document.createElement('div');
    box.className = 'border-b border-slate-100 pb-3 space-y-1';

    // Highlight provenance tags
    const highlightedVal = val
      .replace(/\[Patient Stated\]/g, '<span class="bg-blue-100 text-blue-800 text-[10px] font-bold px-1.5 py-0.5 rounded">Patient Stated</span>')
      .replace(/\[From Document\]/g, '<span class="bg-emerald-100 text-emerald-800 text-[10px] font-bold px-1.5 py-0.5 rounded">From Document</span>')
      .replace(/\[HIGH\]/g, '<span class="bg-red-600 text-white text-[10px] font-bold px-1.5 py-0.5 rounded">HIGH</span>')
      .replace(/\[LOW\]/g, '<span class="bg-amber-600 text-white text-[10px] font-bold px-1.5 py-0.5 rounded">LOW</span>');

    box.innerHTML = `
      <h3 class="text-xs font-bold text-slate-500 uppercase tracking-wider">${label}</h3>
      <p class="text-sm text-slate-800 leading-relaxed">${highlightedVal}</p>
    `;
    container.appendChild(box);
  }

  // Existing Doctor Notes
  if (data.doctor_notes) {
    const notesBox = document.createElement('div');
    notesBox.className = 'bg-sky-50 border border-sky-200 rounded-xl p-3 text-xs text-sky-900';
    notesBox.innerHTML = `<strong>Doctor Notes:</strong> ${data.doctor_notes}`;
    container.appendChild(notesBox);
  }

  lucide.createIcons();
}

async function doctorAction(decision) {
  if (!state.activeSummaryId) return;
  try {
    const res = await fetch(`${API_BASE}/summary/${state.activeSummaryId}/confirm`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ decision: decision, doctor_notes: '' })
    });
    const data = await res.json();
    alert(`Case successfully marked as: ${decision}`);
    refreshDoctorQueue();
    selectDoctorPatient(state.activeSummaryId);
  } catch (err) {
    console.error(err);
  }
}

function toggleEditSummaryModal() {
  document.getElementById('modalEditSummary').classList.toggle('hidden');
}

async function saveDoctorEdits() {
  const notes = document.getElementById('inpDoctorNotes').value.trim();
  try {
    await fetch(`${API_BASE}/summary/${state.activeSummaryId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ doctor_notes: notes })
    });
    toggleEditSummaryModal();
    selectDoctorPatient(state.activeSummaryId);
  } catch (err) {
    console.error(err);
  }
}

async function exportAndPushHis() {
  if (!state.activeSummaryId) return;
  try {
    const res = await fetch(`${API_BASE}/his/push`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ summary_id: state.activeSummaryId })
    });
    const data = await res.json();
    document.getElementById('txtFhirJson').innerText = JSON.stringify(data.fhir_bundle, null, 2);
    document.getElementById('modalFhir').classList.remove('hidden');
  } catch (err) {
    console.error(err);
  }
}

function closeFhirModal() {
  document.getElementById('modalFhir').classList.add('hidden');
}

function copyFhirJson() {
  const txt = document.getElementById('txtFhirJson').innerText;
  navigator.clipboard.writeText(txt);
  alert('FHIR R4 Bundle JSON copied to clipboard!');
}

// ==================== PATIENT PHR & CONSENT ====================

async function loadPatientPhr() {
  try {
    const res = await fetch(`${API_BASE}/patient/timeline/${state.patient.id}`);
    const data = await res.json();

    const consentStatus = document.getElementById('lblPhrConsentStatus');
    if (data.consent && data.consent.revoked) {
      consentStatus.innerText = 'Consent Revoked';
      consentStatus.className = 'font-bold text-red-600 text-sm';
    } else {
      consentStatus.innerText = 'Active & Compliant';
      consentStatus.className = 'font-bold text-emerald-600 text-sm';
    }

    const container = document.getElementById('phrTimelineList');
    container.innerHTML = '';

    // Consultations
    data.consultations.forEach(c => {
      const card = document.createElement('div');
      card.className = 'p-4 rounded-xl border border-slate-200 bg-white space-y-1';
      card.innerHTML = `
        <div class="flex justify-between items-center text-xs">
          <span class="font-bold text-slate-800">Hospital Consultation (${c.token_number})</span>
          <span class="text-slate-400">${c.created_at}</span>
        </div>
        <p class="text-sm text-slate-700">${c.chief_complaint}</p>
        <p class="text-xs text-slate-500 italic">${c.patient_summary}</p>
      `;
      container.appendChild(card);
    });

    // Documents
    data.documents.forEach(d => {
      const card = document.createElement('div');
      card.className = 'p-4 rounded-xl border border-slate-200 bg-slate-50 space-y-1';
      card.innerHTML = `
        <div class="flex justify-between items-center text-xs">
          <span class="font-bold text-slate-800">${d.doc_type}</span>
          <span class="text-slate-400">${d.document_date}</span>
        </div>
        <p class="text-xs text-slate-600">${d.hospital_or_doctor}</p>
      `;
      container.appendChild(card);
    });

    lucide.createIcons();
  } catch (err) {
    console.error(err);
  }
}

async function revokePatientConsent() {
  if (!confirm('Are you sure you want to revoke data sharing consent under the DPDP Act 2023?')) return;
  try {
    await fetch(`${API_BASE}/consent/${state.patient.id}`, { method: 'DELETE' });
    alert('Consent successfully revoked. Data sharing halted per DPDP Act.');
    loadPatientPhr();
  } catch (err) {
    console.error(err);
  }
}
