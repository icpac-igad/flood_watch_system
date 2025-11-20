/**
 * API Logger - Logs API response times in the browser console
 * Useful for monitoring performance of API calls, especially for deterministic forecast points
 */

/**
 * Fetch wrapper that logs response time
 * @param {string} url - The API endpoint URL
 * @param {object} options - Fetch options
 * @returns {Promise<Response>} - Fetch response
 */
export const fetchWithTiming = async (url, options = {}) => {
  const startTime = performance.now();
  const endpoint = url.replace(/^https?:\/\/[^/]+/, ''); // Get path only

  try {
    const response = await fetch(url, options);
    const duration = Math.round(performance.now() - startTime);

    return response;
  } catch (error) {
    const duration = Math.round(performance.now() - startTime);
    console.error(
      `%c❌ API %cFailed%c ${endpoint} %c${duration}ms%c ${error.message}`,
      'color: #f44336; font-weight: bold',
      'color: #f44336; font-weight: bold',
      'color: #666',
      'color: #999',
      'color: #f44336; font-style: italic'
    );
    throw error;
  }
};

/**
 * Log a custom API timing message (disabled)
 * @param {string} endpoint - The endpoint name
 * @param {number} duration - Duration in milliseconds
 * @param {string} status - Status (success/error)
 * @param {string} message - Optional message
 */
export const logApiTiming = (endpoint, duration, status = 'success', message = '') => {
  // Logging disabled
};

export default fetchWithTiming;
