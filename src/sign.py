"""Local signing module for Douyin API using embedded JavaScript."""

from pathlib import Path
from typing import Optional

from py_mini_racer import MiniRacer


# Comprehensive browser environment polyfills
# These MUST be loaded before douyin.js to prevent its broken polyfills from executing
JS_BROWSER_ENV = """
// Create global object first
var global = {};
var window = global;
var self = global;

// Console
var console = {
    log: function() {},
    warn: function() {},
    error: function() {},
    info: function() {},
    debug: function() {},
    trace: function() {}
};

// Proper document polyfill with working createElement
var document = {
    cookie: '',
    domain: 'www.douyin.com',
    referrer: '',
    title: '',
    URL: 'https://www.douyin.com/',
    all: [],
    documentElement: {
        style: {},
        clientWidth: 2560,
        clientHeight: 1440
    },
    body: null,
    head: null,
    hidden: false,
    visibilityState: 'visible',
    readyState: 'complete',
    createElement: function(tag) {
        var elem = {
            tagName: tag ? tag.toUpperCase() : 'DIV',
            style: {},
            attributes: {},
            children: [],
            childNodes: [],
            innerHTML: '',
            innerText: '',
            textContent: '',
            outerHTML: '',
            src: '',
            href: '',
            type: '',
            id: '',
            className: '',
            async: false,
            defer: false,
            onload: null,
            onerror: null,
            onreadystatechange: null,
            readyState: 'complete',
            parentNode: null,
            parentElement: null,
            firstChild: null,
            lastChild: null,
            nextSibling: null,
            previousSibling: null,
            nodeType: 1,
            nodeName: tag ? tag.toUpperCase() : 'DIV',
            ownerDocument: document,
            getAttribute: function(name) { return this.attributes[name] || null; },
            setAttribute: function(name, value) { this.attributes[name] = String(value); },
            removeAttribute: function(name) { delete this.attributes[name]; },
            hasAttribute: function(name) { return name in this.attributes; },
            appendChild: function(child) {
                this.children.push(child);
                this.childNodes.push(child);
                if (child && typeof child === 'object') child.parentNode = this;
                return child;
            },
            removeChild: function(child) {
                var idx = this.children.indexOf(child);
                if (idx > -1) this.children.splice(idx, 1);
                return child;
            },
            insertBefore: function(newChild, refChild) { return newChild; },
            replaceChild: function(newChild, oldChild) { return oldChild; },
            cloneNode: function(deep) { return Object.assign({}, this); },
            addEventListener: function() {},
            removeEventListener: function() {},
            dispatchEvent: function() { return true; },
            click: function() {},
            focus: function() {},
            blur: function() {},
            getBoundingClientRect: function() {
                return { top: 0, left: 0, right: 0, bottom: 0, width: 0, height: 0, x: 0, y: 0 };
            },
            getClientRects: function() { return []; },
            matches: function() { return false; },
            closest: function() { return null; },
            contains: function() { return false; },
            querySelector: function() { return null; },
            querySelectorAll: function() { return []; },
            getElementsByTagName: function() { return []; },
            getElementsByClassName: function() { return []; }
        };

        if (tag && tag.toLowerCase() === 'canvas') {
            elem.width = 300;
            elem.height = 150;
            elem.getContext = function(type) {
                return {
                    fillRect: function() {},
                    clearRect: function() {},
                    getImageData: function(x, y, w, h) {
                        return { data: new Uint8ClampedArray((w||1) * (h||1) * 4), width: w, height: h };
                    },
                    putImageData: function() {},
                    createImageData: function(w, h) {
                        return { data: new Uint8ClampedArray(w * h * 4), width: w, height: h };
                    },
                    setTransform: function() {},
                    drawImage: function() {},
                    save: function() {},
                    restore: function() {},
                    fillText: function() {},
                    strokeText: function() {},
                    measureText: function() { return { width: 0 }; },
                    arc: function() {},
                    fill: function() {},
                    stroke: function() {},
                    beginPath: function() {},
                    closePath: function() {},
                    moveTo: function() {},
                    lineTo: function() {},
                    clip: function() {},
                    rect: function() {},
                    scale: function() {},
                    rotate: function() {},
                    translate: function() {},
                    transform: function() {},
                    createLinearGradient: function() { return { addColorStop: function() {} }; },
                    createRadialGradient: function() { return { addColorStop: function() {} }; },
                    canvas: elem,
                    fillStyle: '#000000',
                    strokeStyle: '#000000',
                    lineWidth: 1,
                    font: '10px sans-serif',
                    globalAlpha: 1,
                    globalCompositeOperation: 'source-over'
                };
            };
            elem.toDataURL = function() { return 'data:image/png;base64,'; };
        }
        return elem;
    },
    createEvent: function(type) {
        return {
            type: type,
            initEvent: function(type, bubbles, cancelable) { this.type = type; },
            preventDefault: function() {},
            stopPropagation: function() {}
        };
    },
    createTextNode: function(text) {
        return {
            nodeValue: text,
            textContent: text,
            nodeType: 3,
            nodeName: '#text',
            data: text,
            length: text ? text.length : 0
        };
    },
    createDocumentFragment: function() {
        return {
            appendChild: function(child) { return child; },
            children: [],
            childNodes: [],
            nodeType: 11,
            nodeName: '#document-fragment'
        };
    },
    getElementById: function(id) { return null; },
    getElementsByTagName: function(tag) { return []; },
    getElementsByClassName: function(cls) { return []; },
    querySelector: function(sel) { return null; },
    querySelectorAll: function(sel) { return []; },
    addEventListener: function() {},
    removeEventListener: function() {},
    hasFocus: function() { return true; },
    write: function() {},
    writeln: function() {},
    open: function() {},
    close: function() {}
};

// Initialize body and head
document.body = document.createElement('body');
document.head = document.createElement('head');

// Navigator
var navigator = {
    userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
    platform: 'MacIntel',
    language: 'zh-CN',
    languages: ['zh-CN', 'zh'],
    cookieEnabled: true,
    onLine: true,
    hardwareConcurrency: 8,
    deviceMemory: 8,
    maxTouchPoints: 0,
    vendor: 'Google Inc.',
    appName: 'Netscape',
    appVersion: '5.0',
    product: 'Gecko',
    connection: { effectiveType: '4g', downlink: 10, rtt: 100 },
    plugins: { length: 0 },
    mimeTypes: { length: 0 }
};

// Location
var location = {
    href: 'https://www.douyin.com/',
    protocol: 'https:',
    host: 'www.douyin.com',
    hostname: 'www.douyin.com',
    port: '',
    pathname: '/',
    search: '',
    hash: '',
    origin: 'https://www.douyin.com'
};

// Screen
var screen = {
    width: 2560,
    height: 1440,
    availWidth: 2560,
    availHeight: 1400,
    colorDepth: 24,
    pixelDepth: 24,
    orientation: { type: 'landscape-primary', angle: 0 }
};

// History
var history = {
    length: 1,
    state: null,
    pushState: function() {},
    replaceState: function() {},
    go: function() {},
    back: function() {},
    forward: function() {}
};

// Performance
var performance = {
    now: function() { return Date.now(); },
    timing: { navigationStart: Date.now() }
};

// Crypto
var crypto = {
    getRandomValues: function(array) {
        for (var i = 0; i < array.length; i++) {
            array[i] = Math.floor(Math.random() * 256);
        }
        return array;
    },
    subtle: {}
};

// XMLHttpRequest
var XMLHttpRequest = function() {
    this.readyState = 0;
    this.status = 0;
    this.statusText = '';
    this.responseText = '';
    this.response = '';
    this.onreadystatechange = null;
    this.onload = null;
    this.onerror = null;
};
XMLHttpRequest.prototype = {
    open: function() {},
    send: function() {},
    abort: function() {},
    setRequestHeader: function() {},
    getResponseHeader: function() { return null; },
    getAllResponseHeaders: function() { return ''; },
    addEventListener: function() {},
    removeEventListener: function() {}
};
XMLHttpRequest.UNSENT = 0;
XMLHttpRequest.OPENED = 1;
XMLHttpRequest.HEADERS_RECEIVED = 2;
XMLHttpRequest.LOADING = 3;
XMLHttpRequest.DONE = 4;

// Fetch
var fetch = function() {
    return Promise.resolve({
        ok: true,
        status: 200,
        json: function() { return Promise.resolve({}); },
        text: function() { return Promise.resolve(''); }
    });
};

// Storage
var Storage = function() { this._data = {}; };
Storage.prototype = {
    getItem: function(key) { return this._data[key] || null; },
    setItem: function(key, value) { this._data[key] = String(value); },
    removeItem: function(key) { delete this._data[key]; },
    clear: function() { this._data = {}; }
};
var localStorage = new Storage();
var sessionStorage = new Storage();

// TextEncoder/TextDecoder
var TextEncoder = function() {
    this.encode = function(str) {
        var arr = [];
        for (var i = 0; i < str.length; i++) {
            var c = str.charCodeAt(i);
            if (c < 128) arr.push(c);
            else if (c < 2048) { arr.push((c >> 6) | 192); arr.push((c & 63) | 128); }
            else { arr.push((c >> 12) | 224); arr.push(((c >> 6) & 63) | 128); arr.push((c & 63) | 128); }
        }
        return new Uint8Array(arr);
    };
};

var TextDecoder = function() {
    this.decode = function(arr) {
        var result = '';
        for (var i = 0; i < arr.length; i++) result += String.fromCharCode(arr[i]);
        return result;
    };
};

// atob/btoa
var atob = function(str) {
    var chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=';
    var output = '';
    str = String(str).replace(/=+$/, '');
    for (var bc = 0, bs, buffer, idx = 0; buffer = str.charAt(idx++);
        ~buffer && (bs = bc % 4 ? bs * 64 + buffer : buffer, bc++ % 4) ?
        output += String.fromCharCode(255 & bs >> (-2 * bc & 6)) : 0
    ) { buffer = chars.indexOf(buffer); }
    return output;
};

var btoa = function(str) {
    var chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=';
    var output = '';
    for (var block, charCode, idx = 0, map = chars;
        str.charAt(idx | 0) || (map = '=', idx % 1);
        output += map.charAt(63 & block >> 8 - idx % 1 * 8)
    ) { charCode = str.charCodeAt(idx += 3/4); block = block << 8 | charCode; }
    return output;
};

// Timers (no-op)
var setTimeout = function(fn, delay) { return 0; };
var setInterval = function(fn, delay) { return 0; };
var clearTimeout = function(id) {};
var clearInterval = function(id) {};
var requestAnimationFrame = function(fn) { return 0; };
var cancelAnimationFrame = function(id) {};

// Event constructors
var Event = function(type) { this.type = type; };
Event.prototype = { preventDefault: function() {}, stopPropagation: function() {} };
var CustomEvent = Event;
var MessageEvent = Event;

// Other constructors
var Blob = function() { this.size = 0; this.type = ''; };
var File = Blob;
var FileReader = function() {};
var FormData = function() {};
var URL = function(url) { this.href = url; };
URL.createObjectURL = function() { return 'blob:null'; };
URL.revokeObjectURL = function() {};
var Worker = function() { this.postMessage = function() {}; this.terminate = function() {}; };
var WebSocket = function() { this.send = function() {}; this.close = function() {}; };
var MutationObserver = function() { this.observe = function() {}; this.disconnect = function() {}; };
var ResizeObserver = MutationObserver;
var IntersectionObserver = MutationObserver;
var Image = function() { this.src = ''; this.onload = null; };
var Audio = function() { this.play = function() { return Promise.resolve(); }; };

// Window properties
window.innerWidth = 2560;
window.innerHeight = 1440;
window.outerWidth = 2560;
window.outerHeight = 1440;
window.screenX = 0;
window.screenY = 0;
window.pageXOffset = 0;
window.pageYOffset = 0;
window.scrollX = 0;
window.scrollY = 0;
window.devicePixelRatio = 1;
window.document = document;
window.navigator = navigator;
window.location = location;
window.screen = screen;
window.history = history;
window.performance = performance;
window.crypto = crypto;
window.localStorage = localStorage;
window.sessionStorage = sessionStorage;
window.console = console;
window.XMLHttpRequest = XMLHttpRequest;
window.fetch = fetch;
window.TextEncoder = TextEncoder;
window.TextDecoder = TextDecoder;
window.atob = atob;
window.btoa = btoa;
window.setTimeout = setTimeout;
window.setInterval = setInterval;
window.clearTimeout = clearTimeout;
window.clearInterval = clearInterval;
window.requestAnimationFrame = requestAnimationFrame;
window.cancelAnimationFrame = cancelAnimationFrame;
window.Event = Event;
window.CustomEvent = CustomEvent;
window.Blob = Blob;
window.URL = URL;
window.Worker = Worker;
window.WebSocket = WebSocket;
window.MutationObserver = MutationObserver;
window.Image = Image;
window.Audio = Audio;

window.getComputedStyle = function() { return { getPropertyValue: function() { return ''; } }; };
window.matchMedia = function(q) { return { matches: false, media: q, addListener: function() {}, removeListener: function() {} }; };
window.open = function() { return null; };
window.close = function() {};
window.focus = function() {};
window.blur = function() {};
window.alert = function() {};
window.confirm = function() { return true; };
window.prompt = function() { return null; };
window.addEventListener = function() {};
window.removeEventListener = function() {};
window.dispatchEvent = function() { return true; };
window.postMessage = function() {};
window.scrollTo = function() {};
window.scroll = function() {};
window.scrollBy = function() {};

window._sdkGlueVersionMap = {
    "sdkGlueVersion": "1.0.0.49",
    "bdmsVersion": "1.0.1.1",
    "captchaVersion": "4.0.2"
};
"""


class DouyinSigner:
    """
    Douyin API request signer using embedded JavaScript.
    """

    _instance: Optional["DouyinSigner"] = None
    _js_code: Optional[str] = None

    def __init__(self):
        self._ctx: Optional[MiniRacer] = None
        self._load_js_code()

    @classmethod
    def get_instance(cls) -> "DouyinSigner":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_js_code(self) -> None:
        if DouyinSigner._js_code is None:
            js_path = Path(__file__).parent / "douyin.js"
            if not js_path.exists():
                raise FileNotFoundError(f"douyin.js not found at {js_path}")

            with open(js_path, "r", encoding="utf-8") as f:
                original_code = f.read()

            # Remove the broken polyfills from douyin.js (lines that define document, navigator, etc.)
            # We'll find the first occurrence of "window.bdms" and skip everything before it
            # that defines broken polyfills
            lines = original_code.split('\n')
            new_lines = []
            skip_polyfills = True

            for i, line in enumerate(lines):
                # Start including lines after we pass the broken polyfill section
                # The broken polyfills end around line 163 with "window.fetch = function"
                # and the real code starts with "window.bdms || function()"
                if 'window.bdms || function()' in line or 'window.bdms||function()' in line:
                    skip_polyfills = False

                if skip_polyfills:
                    # Skip lines that define broken polyfills
                    # But keep the comment lines and version marker
                    stripped = line.strip()
                    if stripped.startswith('//') or stripped.startswith('/*') or stripped.startswith('*'):
                        new_lines.append(line)
                    elif stripped == '' or stripped == '/**' or stripped == '**/':
                        new_lines.append(line)
                    # Skip: document = {}, navigator = {}, XMLHttpRequest, etc.
                else:
                    new_lines.append(line)

            DouyinSigner._js_code = '\n'.join(new_lines)

    def _get_context(self) -> MiniRacer:
        if self._ctx is None:
            self._ctx = MiniRacer()
            # Load browser environment first
            self._ctx.eval(JS_BROWSER_ENV)
            # Then load the patched douyin.js
            self._ctx.eval(DouyinSigner._js_code)
        return self._ctx

    def sign(self, query_params: str, post_data: str = "", user_agent: str = "") -> str:
        # Always use a fresh context - the JS state gets corrupted after first call
        self._ctx = None
        ctx = self._get_context()

        params_escaped = query_params.replace("\\", "\\\\").replace("'", "\\'")
        post_escaped = post_data.replace("\\", "\\\\").replace("'", "\\'")
        ua_escaped = user_agent.replace("\\", "\\\\").replace("'", "\\'")

        js_call = f"get_abogus('{params_escaped}', '{post_escaped}', '{ua_escaped}')"

        try:
            result = ctx.eval(js_call)
            return result if result else ""
        except Exception as e:
            self._ctx = None
            raise SignError(f"Failed to generate a_bogus signature: {e}")

    def reset(self) -> None:
        self._ctx = None


class SignError(Exception):
    pass


def get_a_bogus(query_params: str, post_data: str = "", user_agent: str = "") -> str:
    signer = DouyinSigner.get_instance()
    return signer.sign(query_params, post_data, user_agent)
