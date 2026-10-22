/* Same-origin adapter for the local JOBNEX demo_server.py. */
(function () {
  'use strict';

  async function request(path, options) {
    const response = await fetch(path, {
      ...options,
      headers: { 'Content-Type': 'application/json', ...(options && options.headers) }
    });
    const payload = await response.json();
    if (!response.ok) {
      const detail = payload && payload.detail;
      throw new Error(typeof detail === 'string' ? detail : `Request failed (${response.status})`);
    }
    return payload;
  }

  const api = window.JOBNEX_API || {};
  api.analyzeResume = ({ resumeText, jdText }) => request('/api/analyze', {
    method: 'POST',
    body: JSON.stringify({ resume_text: resumeText, jd_text: jdText })
  });
  api.searchJobs = (keyword, limit = 10) => {
    const query = new URLSearchParams({ keyword, limit: String(limit) });
    return request(`/api/jobs/search?${query}`);
  };
  api.queueApplication = application => request('/api/applications', {
    method: 'POST',
    body: JSON.stringify(application)
  });
  api.getApplications = () => request('/api/applications');
  window.JOBNEX_API = api;
}());
