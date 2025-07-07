/* globals marked, unfetch, ES6Promise, Promise */ // eslint-disable-line no-redeclare

if (!window.Promise) {
  window.Promise = ES6Promise;
}
if (!window.fetch) {
  window.fetch = unfetch;
}

onunhandledrejection = function(e) {
  throw e.reason;
};

var $markdownElem = document.querySelector('#guide');
var $markedVer = document.querySelector('#markedCdn');
var $previewElem = document.querySelector('#preview');
var $previewIframe = document.querySelector('#preview');
var $permalinkElem = document.querySelector('#permalink');
var $inputPanes = document.querySelectorAll('.inputPane');
var lastInput = '';
var inputDirty = true;
var search = searchToObject();
var markedVersionCache = {};
var delayTime = 1;
var checkChangeTimeout = null;
var markedWorker;

$markdownElem.addEventListener('change', handleInput, false);
$markdownElem.addEventListener('keyup', handleInput, false);
$markdownElem.addEventListener('keypress', handleInput, false);
$markdownElem.addEventListener('keydown', handleInput, false);

Promise.all([
]).then(function() {
  checkForChanges();
  setScrollPercent(0);
});

function setInitialText() {
  if ('text' in search) {
    $markdownElem.value = search.text;
  } else {
    return fetch('./initial.md')
      .then(function(res) { return res.text(); })
      .then(function(text) {
        if ($markdownElem.value === '') {
          $markdownElem.value = text;
        }
      });
  }
}

function handleInput() {
  inputDirty = true;
}

function getPrCommit(pr) {
  return fetch('https://api.github.com/repos/markedjs/marked/pulls/' + pr + '/commits')
    .then(function(res) {
      return res.json();
    })
    .then(function(json) {
      return json[json.length - 1].sha;
    }).catch(function() {
      // return undefined
    });
}

function searchToObject() {
  // modified from https://stackoverflow.com/a/7090123/806777
  var pairs = location.search.slice(1).split('&');
  var obj = {};

  for (var i = 0; i < pairs.length; i++) {
    if (pairs[i] === '') {
      continue;
    }

    var pair = pairs[i].split('=');

    obj[decodeURIComponent(pair.shift())] = decodeURIComponent(pair.join('='));
  }

  return obj;
}

function isArray(arr) {
  return Object.prototype.toString.call(arr) === '[object Array]';
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
  if (isArray(input)) {
    if (input.length === 0) {
      return '[]';
    }
    var items = [],
        i;
    if (!isArray(input[0]) && typeof input[0] === 'object' && input[0] !== null) {
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

function getScrollSize() {
  var e = $previewElem;

  return e.scrollHeight - e.clientHeight;
}

function getScrollPercent() {
  var size = getScrollSize();

  if (size <= 0) {
    return 1;
  }

  return $previewElem.scrollTop / size;
}

function setScrollPercent(percent) {
  $previewElem.scrollTop = percent * getScrollSize();
}

function checkForChanges() {
  if (inputDirty && (typeof marked !== 'undefined' || window.Worker)) {
    inputDirty = false;

    var markdown = $markdownElem.value;
    if (lastInput !== markdown) {
      lastInput = markdown;
      if (window.Worker) {
        delayTime = 100;
        messageWorker({
          task: 'parse',
          markdown: markdown,
        });
      } else {
        var parsed = marked.parser(lexed, options);

        $previewElem.classList.remove('error');
        var scrollPercent = getScrollPercent();
        setParsed(parsed);
        setScrollPercent(scrollPercent);
      }
    }
  }
  checkChangeTimeout = window.setTimeout(checkForChanges, delayTime);
}

function setParsed(parsed) {
//  $previewIframe.contentDocument.body.innerHTML = parsed;
}

var workerPromises = {};
function messageWorker(message) {
  if (!markedWorker || markedWorker.working) {
    if (markedWorker) {
      clearTimeout(markedWorker.timeout);
      markedWorker.terminate();
    }
    markedWorker = new Worker('/static/js/worker.js?n=0');
    markedWorker.onmessage = function(e) {
      clearTimeout(markedWorker.timeout);
      markedWorker.working = false;
      switch (e.data.task) {
        case 'parse':
//          $previewElem.classList.remove('error');
          $previewElem.classList.remove('error');
          var scrollPercent = getScrollPercent();
          setParsed(e.data.parsed);
          setScrollPercent(scrollPercent);
          break;
      }
      clearTimeout(checkChangeTimeout);
      delayTime = 10;
      checkForChanges();
      workerPromises[e.data.id]();
      delete workerPromises[e.data.id];
    };
    markedWorker.onerror = markedWorker.onmessageerror = function(err) {
      clearTimeout(markedWorker.timeout);
      var error = 'There was an error in the Worker';
      if (err) {
        if (err.message) {
          error = err.message;
        } else {
          error = err;
        }
      }
      error = error.replace(/^Uncaught Error: /, '');
//      $previewElem.classList.add('error');
      setParsed(error);
      setScrollPercent(0);
    };
  }
  markedWorker.working = true;
  workerTimeout(0);
  return new Promise(function(resolve) {
    message.id = uniqueWorkerMessageId();
    workerPromises[message.id] = resolve;
    markedWorker.postMessage(message);
  });
}

function uniqueWorkerMessageId() {
  var id;
  do {
    id = Math.random().toString(36);
  } while (id in workerPromises);
  return id;
}

function workerTimeout(seconds) {
  markedWorker.timeout = setTimeout(function() {
    seconds++;
    markedWorker.onerror('Marked has taken longer than ' + seconds + ' second' + (seconds > 1 ? 's' : '') + ' to respond...');
    workerTimeout(seconds);
  }, 1000);
}