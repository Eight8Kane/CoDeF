/* globals marked, unfetch, ES6Promise, Promise */ // eslint-disable-line no-redeclare

if (!self.Promise) {
  self.importScripts('https://cdn.jsdelivr.net/npm/es6-promise/dist/es6-promise.js');
  self.Promise = ES6Promise;
}
if (!self.fetch) {
  self.importScripts('https://cdn.jsdelivr.net/npm/unfetch/dist/unfetch.umd.js');
  self.fetch = unfetch;
}
self.importScripts('/static/js/marked.min.js')

var versionCache = {};
var currentVersion;

var options = {
   'async': false,
   'baseUrl': null,
   'breaks': true,
   'extensions': null,
   'gfm': true,
   'headerIds': false,
   'headerPrefix': '',
   'highlight': null,
   'hooks': null,
   'langPrefix': 'language-',
   'mangle': false,
   'pedantic': false,
   'sanitize': false,
   'sanitizer': null,
   'silent': false,
   'smartypants': false,
   'tokenizer': null,
   'walkTokens': null,
   'xhtml': false
};

onunhandledrejection = function(e) {
  throw e.reason;
};

onmessage = function(e) {
  parse(e);
};

function getDefaults() {
  var defaults = {};
  if (typeof marked.getDefaults === 'function') {
    defaults = marked.getDefaults();
    delete defaults.renderer;
  } else if ('defaults' in marked) {
    for (var prop in marked.defaults) {
      if (prop !== 'renderer') {
        defaults[prop] = marked.defaults[prop];
      }
    }
  }
  return defaults;
}

function mergeOptions(options) {
  var opts = {};
  var invalidOptions = [
    'renderer',
    'tokenizer',
    'walkTokens',
    'extensions',
    'highlight',
    'sanitizer'
  ];
  for (var prop in defaults) {
    opts[prop] = invalidOptions.includes(prop) || !(prop in options)
      ? defaults[prop]
      : options[prop];
  }
  return opts;
}

function parse(e) {
  switch (e.data.task) {
    case 'parse':
      postMessage({
        id: e.data.id,
        task: e.data.task,
        parsed: marked.parse(e.data.markdown),
      });
      break;
  }
}

function stringRepeat(char, times) {
  var s = '';
  for (var i = 0; i < times; i++) {
    s += char;
  }
  return s;
}

function jsonString(input, level) {
  level = level || 0;
  if (Array.isArray(input)) {
    if (input.length === 0) {
      return '[]';
    }
    var items = [],
        i;
    if (!Array.isArray(input[0]) && typeof input[0] === 'object' && input[0] !== null) {
      for (i = 0; i < input.length; i++) {
        items.push(stringRepeat(' ', 2 * level) + jsonString(input[i], level + 1));
      }
      return '[\n' + items.join('\n') + '\n]';
    }
    for (i = 0; i < input.length; i++) {
      items.push(jsonString(input[i], level));
    }
    return '[' + items.join(', ') + ']';
  } else if (typeof input === 'object' && input !== null) {
    var props = [];
    for (var prop in input) {
      props.push(prop + ':' + jsonString(input[prop], level));
    }
    return '{' + props.join(', ') + '}';
  } else {
    return JSON.stringify(input);
  }
}

function loadVersion(ver) {
  var promise;
  if (versionCache[ver]) {
    promise = Promise.resolve(versionCache[ver]);
  } else {
    promise = fetch(ver)
      .then(function(res) { return res.text(); })
      .then(function(text) {
        versionCache[ver] = text;
        return text;
      });
  }
  return promise.then(function(text) {
    try {
      // eslint-disable-next-line no-new-func
      Function(text)();
    } catch (err) {
      throw new Error('Cannot load that version of marked');
    }
    currentVersion = ver;
  });
}