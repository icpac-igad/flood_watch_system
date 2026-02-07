/* progressively.js - lazy image loading stub */
var progressively = {
  init: function(options) {
    // Progressive image loading
    var images = document.querySelectorAll('[data-progressive]');
    if (!images.length) return;
    var observer = new IntersectionObserver(function(entries) {
      entries.forEach(function(entry) {
        if (entry.isIntersecting) {
          var img = entry.target;
          var src = img.getAttribute('data-progressive');
          if (src) {
            img.src = src;
            img.removeAttribute('data-progressive');
          }
          observer.unobserve(img);
        }
      });
    });
    images.forEach(function(img) { observer.observe(img); });
  }
};
