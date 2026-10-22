/*
 * JOBNEX shared script. Each page sets <body data-page="...">.
 *
 * BACKEND HOOK: define window.JOBNEX_API BEFORE this script loads. Any method you
 * provide replaces the demo behaviour; anything missing stays in clearly labelled demo mode.
 *   signInWithEmail({email,password})  signInWithGoogle()  analyzeResume({resumeText,jdText})
 *   chat({message,history}) -> string | {text}
 * Never put API keys in this file. Call your own server instead.
 */
(function () {
  'use strict';
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const API = () => window.JOBNEX_API || {};
  // Safe element builder (uses textContent, so user text can never inject HTML)
  function h(tag, attrs, ...kids) {
    const e = document.createElement(tag);
    for (const k in attrs || {}) {
      const v = attrs[k];
      if (v === false || v == null) continue;
      if (k === 'class') e.className = v;
      else if (k.startsWith('on')) e.addEventListener(k.slice(2), v);
      else e.setAttribute(k, v === true ? '' : v);
    }
    kids.flat().forEach(c => e.append(c instanceof Node ? c : document.createTextNode(c == null ? '' : c)));
    return e;
  }
  const store = {
    get(k, d) { try { const v = localStorage.getItem('jobnex.' + k); return v == null ? d : JSON.parse(v); } catch (e) { return d; } },
    set(k, v) { try { localStorage.setItem('jobnex.' + k, JSON.stringify(v)); return true; } catch (e) { return false; } }
  };
  const say = (el, text, state) => { el.textContent = text; el.dataset.state = state || ''; };
  const setErr = (id, msg) => {
    const f = $('#' + id), e = $('#' + id + '-error');
    if (e) e.textContent = msg;
    msg ? f.setAttribute('aria-invalid', 'true') : f.removeAttribute('aria-invalid');
  };

  /* ---------- session (only an email flag is stored; never passwords) ---------- */
  const SKEY = 'jobnex.session';
  const getSession = () => { try { return JSON.parse(sessionStorage.getItem(SKEY) || localStorage.getItem(SKEY) || 'null'); } catch (e) { return null; } };
  const setSession = (s, remember) => { try { (remember ? localStorage : sessionStorage).setItem(SKEY, JSON.stringify(s)); } catch (e) { } };
  const logout = () => { try { sessionStorage.removeItem(SKEY); localStorage.removeItem(SKEY); } catch (e) { } location.href = 'index.html'; };

  const page = document.body.dataset.page;
  const session = getSession();
  if (page === 'login') { if (session) { location.replace('dashboard.html'); return; } }
  else if (!session) { location.replace('index.html'); return; }

  /* ---------- shared header / footer ---------- */
  const LINKS = [['dashboard.html', 'Dashboard'], ['analyzer.html', 'Resume Analyzer'], ['jobs.html', 'Find Jobs'], ['chatbot.html', 'AI Assistant'], ['interview.html', 'Interview Prep'], ['courses.html', 'Courses'], ['applications.html', 'Applications'], ['privacy.html', 'Privacy']];
  function renderChrome() {
    const header = $('#site-header'), footer = $('#site-footer');
    if (!header) return;
    const here = location.pathname.split('/').pop() || 'index.html';
    const ul = h('ul', { class: 'nav-links', id: 'nav-links' },
      LINKS.map(([href, l]) => h('li', {}, h('a', { href, 'aria-current': href === here ? 'page' : false }, l))),
      h('li', {}, h('button', { type: 'button', class: 'danger sm', onclick: logout }, 'Logout')));
    const toggle = h('button', { type: 'button', class: 'secondary nav-toggle', 'aria-expanded': 'false', 'aria-controls': 'nav-links', onclick() { toggle.setAttribute('aria-expanded', ul.classList.toggle('open')); } }, '☰ Menu');
    header.append(h('nav', { class: 'nav-bar', 'aria-label': 'Main navigation' }, h('a', { class: 'logo', href: 'dashboard.html' }, 'JOB', h('span', {}, 'NEX')), toggle, ul));
    footer.append(h('p', {}, '© ' + new Date().getFullYear() + ' JOBNEX. Frontend demo: sample data, no live services.'));
  }

  /* ---------- shared application data (localStorage, demo only) ---------- */
  const STATUSES = ['Applied', 'Interview', 'Offer', 'Rejected', 'Withdrawn'];
  const daysAgo = n => new Date(Date.now() - n * 864e5).toISOString().slice(0, 10);
  const SEED = () => [
    { id: 'a1', jobId: 3, company: 'Orbit Analytics', title: 'Data Analyst', date: daysAgo(3), status: 'Applied' },
    { id: 'a2', jobId: 5, company: 'Cobalt Works', title: 'DevOps Engineer', date: daysAgo(8), status: 'Interview' },
    { id: 'a3', jobId: 1, company: 'Northwind Labs', title: 'Frontend Developer', date: daysAgo(14), status: 'Offer' },
    { id: 'a4', jobId: 6, company: 'Lumen Software', title: 'QA Engineer', date: daysAgo(20), status: 'Rejected' },
    { id: 'a5', jobId: 2, company: 'Brightpath Systems', title: 'Python Developer', date: daysAgo(1), status: 'Applied' }];
  const getApps = () => store.get('apps', null) || SEED();
  const saveApps = a => store.set('apps', a);
  const badge = s => h('span', { class: 'badge s-' + s.toLowerCase() }, s);
  const dateCell = d => h('td', {}, h('time', { datetime: d }, d));

  const pages = {};

  /* ---------- index.html: login ---------- */
  pages.login = () => {
    const live = !!API().signInWithEmail, fb = $('#login-feedback'), btn = $('#login-button');
    $('#demo-note').hidden = live;
    const finish = (email, remember) => { setSession({ email, demo: !live }, remember); location.href = 'dashboard.html'; };
    $('#login-form').addEventListener('submit', async e => {
      e.preventDefault();
      const email = $('#login-email').value.trim(), pw = $('#login-password').value;
      setErr('login-email', !email ? 'Enter your email address.' : !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email) ? 'Enter a valid email address.' : '');
      setErr('login-password', !pw ? 'Enter your password.' : (!live && pw.length < 8 ? 'Use at least 8 characters.' : ''));
      const bad = $('[aria-invalid]', e.target);
      if (bad) { say(fb, 'Please fix the highlighted fields.', 'error'); bad.focus(); return; }
      btn.disabled = true; say(fb, 'Signing in…');
      try { if (live) await API().signInWithEmail({ email, password: pw }); finish(email, $('#remember-me').checked); }
      catch (x) { say(fb, 'Sign-in failed. Check your details and try again.', 'error'); btn.disabled = false; }
    });
    $('#google-login').addEventListener('click', async () => {
      if (!API().signInWithGoogle) return say(fb, 'Google sign-in is not connected. It needs a Google OAuth setup and a backend, so please use email.', 'error');
      try { const r = await API().signInWithGoogle(); finish((r && r.email) || 'Google account', false); }
      catch (x) { say(fb, 'Google sign-in failed. Please try again.', 'error'); }
    });
    $('#forgot-password').addEventListener('click', e => { e.preventDefault(); say(fb, 'Password reset is not connected in this demo, so no email is sent.'); });
  };

  /* ---------- dashboard.html ---------- */
  pages.dashboard = () => {
    const a = getApps(), n = s => a.filter(x => x.status === s).length;
    $('#stat-applied').textContent = a.length; $('#stat-interview').textContent = n('Interview');
    $('#stat-offer').textContent = n('Offer'); $('#stat-rejected').textContent = n('Rejected');
    const tb = $('#recent-body');
    a.slice().sort((x, y) => y.date.localeCompare(x.date)).slice(0, 5)
      .forEach(x => tb.append(h('tr', {}, h('td', {}, x.company), h('td', {}, x.title), dateCell(x.date), h('td', {}, badge(x.status)))));
    if (!a.length) tb.append(h('tr', {}, h('td', { colspan: 4 }, 'No applications yet. Use Apply on the Find Jobs page.')));
  };

  /* ---------- analyzer.html (IDs kept: resume_text, jd_text, analyze-button, status, results, result-data) ---------- */
  const STOP = new Set('and the for with you our are will have has this that from your their they not but can all any who use using able also into more must such than then them these those its was were been being work team'.split(' '));
  const words = t => [...new Set((t.toLowerCase().match(/[a-z][a-z+#.]{2,}/g) || []).map(w => w.replace(/\.$/, '')).filter(w => !STOP.has(w)))];
  pages.analyzer = () => {
    const st = $('#status'), btn = $('#analyze-button');
    $('#analyze-form').addEventListener('submit', async e => {
      e.preventDefault();
      const r = $('#resume_text'), j = $('#jd_text');
      setErr('resume_text', r.value.trim() ? '' : 'Paste your resume to continue.');
      setErr('jd_text', j.value.trim() ? '' : 'Paste the job description to continue.');
      const bad = $('[aria-invalid]', e.target);
      if (bad) { say(st, 'Please fill in both fields.', 'error'); bad.focus(); return; }
      btn.disabled = true; btn.textContent = 'Analyzing…'; $('#results').hidden = true; say(st, 'Analyzing…');
      try {
        let text;
        if (API().analyzeResume) {
          const res = await API().analyzeResume({ resumeText: r.value.trim(), jdText: j.value.trim() });
          text = typeof res === 'string' ? res : JSON.stringify(res, null, 2);
        } else {
          const rs = new Set(words(r.value)), jw = words(j.value), hit = jw.filter(w => rs.has(w)), miss = jw.filter(w => !rs.has(w));
          store.set('missing', miss.slice(0, 8));
          text = `Match score (demo keyword overlap): ${jw.length ? Math.round(hit.length / jw.length * 100) : 0}%\n\nMatched keywords:\n${hit.slice(0, 25).join(', ') || 'none'}\n\nMissing keywords:\n${miss.slice(0, 25).join(', ') || 'none'}\n\nDemo mode: a simple word comparison, not an AI review.`;
        }
        $('#result-data').textContent = text; $('#results').hidden = false; say(st, 'Analysis complete.');
      } catch (x) { say(st, 'Resume analysis failed. Please try again.', 'error'); }
      btn.disabled = false; btn.textContent = 'Analyze Resume';
    });
  };

  /* ---------- jobs.html (SAMPLE listings only) ---------- */
  const JOBS = [
    { id: 1, company: 'Northwind Labs', title: 'Frontend Developer', location: 'Bengaluru, India', region: 'bengaluru', exp: 'junior', certs: [], match: 86, skills: 'html css javascript react' },
    { id: 2, company: 'Brightpath Systems', title: 'Python Developer', location: 'Hyderabad, India', region: 'india', exp: 'mid', certs: ['aws'], match: 78, skills: 'python flask aws sql' },
    { id: 3, company: 'Orbit Analytics', title: 'Data Analyst', location: 'Remote', region: 'global', exp: 'fresher', certs: [], match: 64, skills: 'sql python dashboards' },
    { id: 4, company: 'Harbor & Finch', title: 'Java Developer', location: 'Austin, TX, USA', region: 'usa', exp: 'senior', certs: ['pmp'], match: 71, skills: 'java spring microservices' },
    { id: 5, company: 'Cobalt Works', title: 'DevOps Engineer', location: 'Bengaluru, India', region: 'bengaluru', exp: 'mid', certs: ['azure', 'aws'], match: 59, skills: 'docker kubernetes ci cd' },
    { id: 6, company: 'Lumen Software', title: 'QA Engineer', location: 'Pune, India', region: 'india', exp: 'fresher', certs: [], match: 66, skills: 'testing selenium' },
    { id: 7, company: 'Fieldnote AI', title: 'Django Developer', location: 'Seattle, WA, USA', region: 'usa', exp: 'mid', certs: ['gcp'], match: 82, skills: 'python django rest postgres' },
    { id: 8, company: 'Tidewater Digital', title: 'Scrum Master', location: 'Remote', region: 'global', exp: 'mid', certs: ['scrum'], match: 52, skills: 'agile scrum coaching' }];
  pages.jobs = () => {
    const f = $('#job-search-form'), box = $('#job-results'), cnt = $('#result-count');
    const saved = new Set(store.get('savedJobs', []));
    const regionOk = (sel, r) => sel === 'global' || (sel === 'india' ? r === 'india' || r === 'bengaluru' : sel === r);
    function card(j, applied) {
      const apply = h('button', { type: 'button', disabled: applied, onclick() { const a = getApps(); a.push({ id: 'a' + Date.now(), jobId: j.id, company: j.company, title: j.title, date: daysAgo(0), status: 'Applied' }); saveApps(a); apply.textContent = 'Applied'; apply.disabled = true; } }, applied ? 'Applied' : 'Apply');
      const save = h('button', { type: 'button', class: 'secondary', 'aria-pressed': String(saved.has(j.id)), onclick() { saved.has(j.id) ? saved.delete(j.id) : saved.add(j.id); store.set('savedJobs', [...saved]); save.setAttribute('aria-pressed', saved.has(j.id)); save.textContent = saved.has(j.id) ? 'Saved' : 'Save'; } }, saved.has(j.id) ? 'Saved' : 'Save');
      return h('article', { class: 'card job' }, h('h2', {}, j.company), h('p', { class: 'role' }, j.role || j.title), h('p', { class: 'muted' }, j.location),
        h('label', { for: 'match-' + j.id }, 'Match score: ' + j.match + '%'), h('meter', { id: 'match-' + j.id, min: 0, max: 100, value: j.match }, j.match + '%'),
        h('div', { class: 'row' }, apply, save));
    }
    function run() {
      cnt.textContent = ''; box.replaceChildren(h('p', { class: 'card' }, h('span', { class: 'spinner', 'aria-hidden': 'true' }), 'Searching sample jobs…'));
      setTimeout(() => {
        try {
          const q = $('#job-keywords').value.toLowerCase().split(/\s+/).filter(Boolean), ex = $('#filter-experience').value, rg = $('#filter-region').value, ce = $('#filter-cert').value;
          const list = JOBS.filter(j => { const hay = (j.title + ' ' + j.company + ' ' + j.skills).toLowerCase(); return q.every(t => hay.includes(t)) && (ex === 'any' || j.exp === ex) && regionOk(rg, j.region) && (ce === 'any' || j.certs.includes(ce)); });
          if (!list.length) { box.replaceChildren(h('div', { class: 'card' }, h('h2', {}, 'No sample jobs match'), h('p', {}, 'Try a broader region or clear the filters.'))); return; }
          cnt.textContent = list.length + ' sample job' + (list.length > 1 ? 's' : '') + ' found.';
          const applied = new Set(getApps().map(a => a.jobId));
          box.replaceChildren(...list.map(j => card(j, applied.has(j.id))));
        } catch (x) {
          box.replaceChildren(h('div', { class: 'card', role: 'alert' }, h('h2', {}, 'Something went wrong'), h('p', {}, 'The search could not run.'), h('button', { type: 'button', onclick: run }, 'Retry')));
        }
      }, 400);
    }
    f.addEventListener('submit', e => { e.preventDefault(); run(); });
    $('#apply-cert-exp-filters').addEventListener('click', run);
    f.addEventListener('reset', () => setTimeout(run));
    $$('[data-q]').forEach(b => b.addEventListener('click', () => { $('#job-keywords').value = b.dataset.q; run(); }));
    run();
  };

  /* ---------- chatbot.html ---------- */
  const DEMO = [[/resume|improve/, 'Lead with a one-line summary aimed at the role. Start each bullet with an action verb and a result you can measure. Mirror keywords from the job description where they are true.'],
  [/skill/, () => { const m = store.get('missing', []); return m.length ? 'From your last Resume Analyzer run, these keywords are missing: ' + m.slice(0, 5).join(', ') + '.' : 'Run the Resume Analyzer first and I can list your missing skills.'; }],
  [/career|guid/, 'List the tasks you enjoy most, find roles built around them, and pick one skill to deepen over the next month.'],
  [/mock|interview/, 'Mock interview: "Tell me about a project you are proud of." Answer in about two minutes using Situation, Action, Result. More questions are on the Interview Prep page.']];
  const demoReply = t => { const m = DEMO.find(d => d[0].test(t.toLowerCase())); return m ? (typeof m[1] === 'function' ? m[1]() : m[1]) : 'This demo only has scripted answers. Try one of the quick actions.'; };
  pages.chatbot = () => {
    const log = $('#chat-window'), typing = $('#typing'), input = $('#chat-input'), send = $('#chat-send');
    const WELCOME = { role: 'bot', text: 'Hi! I am a demo assistant with scripted answers. Use a quick action or type a question about your resume, skills, interviews or career.', label: 'Demo reply' };
    let msgs = store.get('chat', []);
    const paint = m => { log.append(h('div', { class: 'msg ' + m.role }, m.role === 'bot' ? [h('span', { class: 'badge-demo' }, m.label || (m.real ? 'AI' : 'Demo reply')), h('br'), m.text] : m.text)); log.scrollTop = log.scrollHeight; };
    const hist = () => {
      const ul = $('#history-list'), u = msgs.filter(m => m.role === 'user').slice(-10).reverse();
      ul.replaceChildren(...(u.length ? u.map(m => h('li', {}, m.text)) : [h('li', { class: 'muted' }, 'No messages yet.')]));
    };
    const add = m => { msgs = [...msgs, m].slice(-60); store.set('chat', msgs); paint(m); hist(); };
    async function ask(text) {
      text = text.trim(); if (!text) return;
      add({ role: 'user', text }); send.disabled = true; typing.hidden = false;
      let r;
      try {
        if (API().chat) { const x = await API().chat({ message: text, history: msgs }); r = { text: typeof x === 'string' ? x : x.text, real: true }; }
        else { await new Promise(s => setTimeout(s, 800)); r = { text: demoReply(text), real: false }; }
      } catch (e) { r = { text: 'The assistant could not respond. Please try again.', label: 'Notice' }; }
      typing.hidden = true; send.disabled = false; add({ role: 'bot', ...r });
    }
    if (!msgs.length) add(WELCOME); else { msgs.forEach(paint); hist(); }
    $('#chat-form').addEventListener('submit', e => { e.preventDefault(); const t = input.value; input.value = ''; ask(t); input.focus(); });
    $$('[data-quick]').forEach(b => b.addEventListener('click', () => ask(b.textContent)));
    $('#clear-history').addEventListener('click', () => { msgs = []; store.set('chat', []); log.replaceChildren(); add(WELCOME); });
  };

  /* ---------- interview.html ---------- */
  const QS = {
    technical: [['Explain a project you built and the decisions you made.', 'State the problem, your role, tools chosen, trade-offs and the result.'], ['How would you debug an API request that returns an error?', 'Check status code and body, reproduce, read server logs, isolate the cause.'], ['Client-side vs server-side validation: what is the difference?', 'Client-side gives fast feedback; server-side is essential because clients can be bypassed.'], ['How do you stop duplicate form submissions?', 'Disable submit while a request runs, guard repeat handlers, use backend idempotency.'], ['How would you make a page usable by keyboard only?', 'Semantic HTML, logical focus order, visible focus, labelled controls.']],
    behavioral: [['Tell me about a time you learned something quickly.', 'Describe the goal, how you split the topic, how you practised and what you delivered.'], ['Describe a mistake and how you handled it.', 'Own it, explain the impact, the fix and what you changed afterwards.'], ['Tell me about difficult feedback you received.', 'Say what it was, how you clarified it and what improved.'], ['How do you prioritize when everything is urgent?', 'Compare impact, deadline and risk, and communicate trade-offs early.'], ['Describe working with unclear requirements.', 'Name the unknowns, the questions you asked and how you confirmed assumptions.']],
    hr: [['Tell me about yourself.', 'Present, past, future in about two minutes, tied to this role.'], ['Why this role and company?', 'Connect real responsibilities to your strengths and goals. Research first.'], ['What team environment suits you best?', 'Give practical conditions plus a short example.'], ['What are your strengths?', 'Pick two relevant strengths and back each with an example.'], ['What are your goals for the next few years?', 'Focus on skills and growing responsibility, realistic for the role.']],
    system: [['Design a URL shortener.', 'Clarify requirements, then cover ID generation, storage, caching, redirects and scale.'], ['How would you design a job-search API?', 'Cover endpoints, pagination, filters, indexing, caching and rate limiting.'], ['How would you design a notification system?', 'Discuss queues, retries, delivery channels, user preferences and idempotency.'], ['How do you scale a read-heavy service?', 'Caching, read replicas, CDN, indexing and measuring before optimizing.'], ['Design a resume-upload feature.', 'Cover validation, size limits, virus scanning, storage, privacy and access control.']]
  };
  pages.interview = () => {
    const tabs = $$('[role=tab]'), list = $('#interview-questions'), panel = $('#interview-panel'), st = $('#interview-status');
    let cat = 'technical';
    const render = qs => list.replaceChildren(...qs.map(([q, t]) => h('li', { class: 'card' }, h('p', { class: 'q' }, q), h('details', {}, h('summary', {}, 'Answer tips'), h('p', {}, t)))));
    const select = t => { cat = t.dataset.cat; tabs.forEach(x => { x.setAttribute('aria-selected', x === t); x.tabIndex = x === t ? 0 : -1; }); panel.setAttribute('aria-labelledby', t.id); st.textContent = ''; render(QS[cat]); };
    tabs.forEach((t, i) => {
      t.addEventListener('click', () => select(t));
      t.addEventListener('keydown', e => { const d = { ArrowRight: 1, ArrowLeft: -1 }[e.key]; if (!d) return; e.preventDefault(); const n = tabs[(i + d + tabs.length) % tabs.length]; n.focus(); select(n); });
    });
    $('#generate-questions').addEventListener('click', () => { render(QS[cat].slice().sort(() => Math.random() - .5).slice(0, 3)); st.textContent = 'Showing 3 random questions from the built-in set (not AI-generated).'; });
    select(tabs[0]);
  };

  /* ---------- courses.html (SAMPLE courses) ---------- */
  const COURSES = [['Python for Beginners', 'SampleLearn', 'Beginner', 4.6, '🐍'], ['REST API Design', 'SampleLearn', 'Intermediate', 4.5, '🔌'], ['SQL Essentials', 'DemoAcademy', 'Beginner', 4.7, '🗄️'], ['Docker in Practice', 'DemoAcademy', 'Intermediate', 4.4, '🐳'], ['Cloud Fundamentals', 'ExampleU', 'Beginner', 4.3, '☁️'], ['System Design Basics', 'ExampleU', 'Advanced', 4.8, '🧩']];
  pages.courses = () => {
    const m = store.get('missing', []), skills = m.length ? m : ['Docker', 'REST APIs', 'SQL'];
    $('#skills-source').textContent = m.length ? 'From your latest Resume Analyzer run.' : 'Sample skills. Run the Resume Analyzer to see your own.';
    $('#missing-skills-list').replaceChildren(...skills.map(s => h('li', {}, s)));
    $('#course-cards').replaceChildren(...COURSES.map(([t, p, l, r, ic], i) => h('article', { class: 'card course' },
      h('div', { class: 'thumb t' + (i % 4), 'aria-hidden': 'true' }, ic), h('h3', {}, t), h('p', { class: 'muted' }, p + ' · ' + l), h('p', { 'aria-label': 'Rating ' + r + ' out of 5' }, '★ ' + r),
      h('button', { type: 'button', class: 'secondary', onclick() { say($('#course-msg'), 'Enrollment is not connected in this demo. "' + t + '" is a sample course.'); } }, 'Enroll'))));
  };

  /* ---------- applications.html ---------- */
  pages.applications = () => {
    const body = $('#apps-body'), msg = $('#app-msg'), pick = $('#ref-app'), apps = getApps();
    body.replaceChildren(...(apps.length ? apps.map((x, i) => {
      const bc = h('td', {}, badge(x.status));
      return h('tr', {}, h('td', {}, x.company), h('td', {}, x.title), dateCell(x.date), bc,
        h('td', {}, h('label', { class: 'visually-hidden', for: 'status-row-' + (i + 1) }, 'Status for ' + x.company),
          h('select', { id: 'status-row-' + (i + 1), onchange(e) { x.status = e.target.value; saveApps(apps); bc.replaceChildren(badge(x.status)); say(msg, 'Status updated for ' + x.company + '.'); } }, STATUSES.map(s => h('option', { selected: s === x.status }, s)))),
        h('td', {}, h('button', { type: 'button', class: 'danger sm', 'aria-label': 'Remove ' + x.company, onclick() { saveApps(apps.filter(y => y !== x)); location.reload(); } }, 'Remove')));
    }) : [h('tr', {}, h('td', { colspan: 6 }, 'No applications yet. Use Apply on the Find Jobs page.'))]));
    pick.append(...apps.map((x, i) => h('option', { value: i }, x.company + ' – ' + x.title)));
    pick.addEventListener('change', () => { const x = apps[pick.value]; if (x) { $('#company-name').value = x.company; $('#job-role').value = x.title; } });

    // Referral email: text only. Nothing is ever sent from this page.
    const out = $('#referral-output');
    $('#referral-form').addEventListener('submit', e => {
      e.preventDefault();
      const v = id => $('#' + id).value.trim(), co = v('company-name'), role = v('job-role');
      setErr('company-name', co ? '' : 'Enter the company name.'); setErr('job-role', role ? '' : 'Enter the job role.');
      const bad = $('[aria-invalid]', e.target); if (bad) { bad.focus(); return; }
      $('#ref-subject').value = `Referral Request for ${role} Position`;
      $('#ref-body').value = `Hello ${v('recruiter-name') || '[Recruiter]'},\n\nI hope you are doing well.\n\nI recently came across the ${role} position at ${co}.\n\n${v('your-background') || 'My background includes [add your relevant skills and experience here].'}\n\nWould you be open to referring me or pointing me to the right person? I am happy to share my resume.\n\nThank you for your time.\n\nBest Regards,\n${v('your-name') || '[Applicant Name]'}`;
      out.hidden = false; say($('#copy-msg'), 'Draft ready. Review and edit it, then send it yourself from your email service.'); $('#ref-subject').focus();
    });
    $('#copy-referral').addEventListener('click', async () => {
      const text = 'Subject: ' + $('#ref-subject').value + '\n\n' + $('#ref-body').value;
      try { await navigator.clipboard.writeText(text); say($('#copy-msg'), 'Copied to your clipboard.'); }
      catch (e) { $('#ref-body').select(); say($('#copy-msg'), 'Copy was blocked by the browser. The body is selected, so press Ctrl+C.', 'error'); }
    });
  };

  /* ---------- privacy.html ---------- */
  pages.privacy = () => {
    const f = $('#privacy-form'), p = store.get('privacy', null);
    if (p) {
      const r = $(`input[name=resume-visibility][value="${p.vis}"]`, f); if (r) r.checked = true;
      $('#hide-email').checked = !!p.email; $('#hide-phone').checked = !!p.phone; $('#allow-download').checked = !!p.dl;
    }
    const save = () => {
      const ok = store.set('privacy', { vis: $('input[name=resume-visibility]:checked', f).value, email: $('#hide-email').checked, phone: $('#hide-phone').checked, dl: $('#allow-download').checked });
      say($('#privacy-msg'), ok ? 'Saved in this browser only. This does not change who can see your resume until a backend is connected.' : 'Could not save: browser storage is unavailable.', ok ? '' : 'error');
    };
    $('#save-privacy').addEventListener('click', save);
    f.addEventListener('submit', e => { e.preventDefault(); save(); });
  };

  renderChrome();
  if (pages[page]) pages[page]();
}());