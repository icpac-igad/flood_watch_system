/**
 * In-memory cache for forecast data to enable instant loading
 * when switching between dates
 */

class ForecastCache {
  constructor(maxSize = 10, ttl = 3600000) { // 1 hour TTL
    this.cache = new Map();
    this.maxSize = maxSize;
    this.ttl = ttl;
  }

  /**
   * Generate cache key from date and country
   */
  _getKey(date, country = null) {
    return country ? `${date}_${country}` : date;
  }

  /**
   * Check if cache entry is still valid
   */
  _isValid(entry) {
    return Date.now() - entry.timestamp < this.ttl;
  }

  /**
   * Get cached data if available and valid
   */
  get(date, country = null) {
    const key = this._getKey(date, country);
    const entry = this.cache.get(key);

    if (!entry) {
      return null;
    }

    if (!this._isValid(entry)) {
      this.cache.delete(key);
      return null;
    }

    // Update access time for LRU
    entry.lastAccess = Date.now();
    return entry.data;
  }

  /**
   * Store data in cache
   */
  set(date, country = null, data) {
    const key = this._getKey(date, country);

    // Enforce max size using LRU eviction
    if (this.cache.size >= this.maxSize && !this.cache.has(key)) {
      // Find least recently used entry
      let oldestKey = null;
      let oldestTime = Infinity;

      for (const [k, v] of this.cache.entries()) {
        if (v.lastAccess < oldestTime) {
          oldestTime = v.lastAccess;
          oldestKey = k;
        }
      }

      if (oldestKey) {
        this.cache.delete(oldestKey);
      }
    }

    this.cache.set(key, {
      data,
      timestamp: Date.now(),
      lastAccess: Date.now()
    });
  }

  /**
   * Clear all cached data
   */
  clear() {
    this.cache.clear();
  }

  /**
   * Get cache statistics
   */
  stats() {
    return {
      size: this.cache.size,
      maxSize: this.maxSize,
      keys: Array.from(this.cache.keys())
    };
  }
}

// Export singleton instance
export const forecastCache = new ForecastCache();
