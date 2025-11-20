/**
 * Base API Client
 * Handles common HTTP operations with timing and error handling
 */

/**
 * Fetch with timing information
 */
export const fetchWithTiming = async (url: string, options?: RequestInit): Promise<Response> => {
  const startTime = performance.now();

  try {
    const response = await fetch(url, options);
    return response;
  } catch (error) {
    const duration = Math.round(performance.now() - startTime);
    console.error(`❌ API Error ${url} (${duration}ms):`, error);
    throw error;
  }
};

/**
 * Generic fetch JSON with error handling
 */
export const fetchJSON = async <T>(url: string, options?: RequestInit): Promise<T> => {
  const response = await fetchWithTiming(url, options);
  
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }
  
  return response.json();
};

/**
 * Cache wrapper for API calls
 */
const cache = new Map<string, { data: any; timestamp: number }>();

export const fetchWithCache = async <T>(
  url: string,
  cacheDuration: number,
  options?: RequestInit
): Promise<T> => {
  const cached = cache.get(url);
  const now = Date.now();

  if (cached && (now - cached.timestamp) < cacheDuration) {
    return cached.data as T;
  }

  const data = await fetchJSON<T>(url, options);
  cache.set(url, { data, timestamp: now });

  return data;
};

/**
 * Clear cache
 */
export const clearCache = (urlPattern?: string): void => {
  if (!urlPattern) {
    cache.clear();
    return;
  }
  
  for (const key of cache.keys()) {
    if (key.includes(urlPattern)) {
      cache.delete(key);
    }
  }
};
