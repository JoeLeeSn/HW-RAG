import { apiBaseUrl } from '../config/config';

const api = {
  async get(endpoint, params = {}) {
    const url = new URL(`${apiBaseUrl}/${endpoint}`);
    Object.keys(params).forEach(key => url.searchParams.append(key, params[key]));
    
    const response = await fetch(url);
    if (!response.ok) throw new Error(await response.text());
    return response.json();
  },

  async post(endpoint, data) {
    const response = await fetch(`${apiBaseUrl}/${endpoint}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error(await response.text());
    return response.json();
  },

  async postFormData(endpoint, formData) {
    const response = await fetch(`${apiBaseUrl}/${endpoint}`, {
      method: 'POST',
      body: formData,
    });
    if (!response.ok) throw new Error(await response.text());
    return response.json();
  }
};

export default api; 