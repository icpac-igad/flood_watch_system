/**
 * URL Encoding Utilities
 * Based on mukau-viz-components utils/request.js
 * Handles Base64 encoding/decoding of state for shareable URLs
 */

/**
 * Encode a JSON object to Base64 string for URL parameter
 * @param {Object} json - The object to encode
 * @returns {string} Base64 encoded string
 */
export const encodeJsonToBase64 = (json) => {
  try {
    const jsonString = JSON.stringify(json);
    // Use btoa for browser, Buffer for Node
    if (typeof window !== "undefined" && window.btoa) {
      return window.btoa(unescape(encodeURIComponent(jsonString)));
    }
    return Buffer.from(jsonString).toString("base64");
  } catch (error) {
    console.error("Error encoding JSON to Base64:", error);
    return "";
  }
};

/**
 * Decode a Base64 string back to JSON object
 * @param {string} base64String - The Base64 encoded string
 * @returns {Object} Decoded JSON object or empty object on error
 */
export const decodeBase64ToJson = (base64String) => {
  try {
    if (!base64String) return {};

    let jsonString;
    // Use atob for browser, Buffer for Node
    if (typeof window !== "undefined" && window.atob) {
      jsonString = decodeURIComponent(escape(window.atob(base64String)));
    } else {
      jsonString = Buffer.from(base64String, "base64").toString("utf-8");
    }

    return JSON.parse(jsonString);
  } catch (error) {
    console.error("Error decoding Base64 to JSON:", error);
    return {};
  }
};

/**
 * Build a query string from an object
 * @param {Object} params - Object with key-value pairs
 * @returns {string} Query string (without leading ?)
 */
export const buildQueryString = (params) => {
  const searchParams = new URLSearchParams();

  Object.entries(params).forEach(([key, value]) => {
    if (value !== null && value !== undefined && value !== "") {
      searchParams.append(key, value);
    }
  });

  return searchParams.toString();
};

/**
 * Parse query string to object
 * @param {string} queryString - Query string (with or without leading ?)
 * @returns {Object} Parsed parameters
 */
export const parseQueryString = (queryString) => {
  const params = {};
  const searchParams = new URLSearchParams(
    queryString.startsWith("?") ? queryString.slice(1) : queryString
  );

  searchParams.forEach((value, key) => {
    params[key] = value;
  });

  return params;
};

/**
 * Update URL with new query parameters without page reload
 * @param {Object} params - Parameters to encode
 * @param {Object} settings - Settings to encode
 */
export const updateUrlState = (params, settings) => {
  const encoded = encodeJsonToBase64({ params, settings });
  const newUrl = `${window.location.pathname}?qstr=${encoded}`;
  window.history.replaceState({ params, settings }, "", newUrl);
};

/**
 * Get current state from URL
 * @returns {Object} { params, settings } or empty objects
 */
export const getStateFromUrl = () => {
  if (typeof window === "undefined") {
    return { params: {}, settings: {} };
  }

  const urlParams = new URLSearchParams(window.location.search);
  const qstr = urlParams.get("qstr");

  if (qstr) {
    return decodeBase64ToJson(qstr);
  }

  return { params: {}, settings: {} };
};

export default {
  encodeJsonToBase64,
  decodeBase64ToJson,
  buildQueryString,
  parseQueryString,
  updateUrlState,
  getStateFromUrl,
};
