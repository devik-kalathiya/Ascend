"""Maps common concepts to documentation URLs (fast local fallback for hints)."""

import re
from typing import List

DOCS_MAP = {
    'fetch': 'https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API/Using_Fetch',
    'document.createElement': 'https://developer.mozilla.org/en-US/docs/Web/API/Document/createElement',
    'addEventListener': 'https://developer.mozilla.org/en-US/docs/Web/API/EventTarget/addEventListener',
    'localStorage': 'https://developer.mozilla.org/en-US/docs/Web/API/Window/localStorage',
    'sessionStorage': 'https://developer.mozilla.org/en-US/docs/Web/API/Window/sessionStorage',
    'querySelector': 'https://developer.mozilla.org/en-US/docs/Web/API/Document/querySelector',
    'querySelectorAll': 'https://developer.mozilla.org/en-US/docs/Web/API/Document/querySelectorAll',
    'innerHTML': 'https://developer.mozilla.org/en-US/docs/Web/API/Element/innerHTML',
    'textContent': 'https://developer.mozilla.org/en-US/docs/Web/API/Node/textContent',
    'classList': 'https://developer.mozilla.org/en-US/docs/Web/API/Element/classList',
    'setAttribute': 'https://developer.mozilla.org/en-US/docs/Web/API/Element/setAttribute',
    'getAttribute': 'https://developer.mozilla.org/en-US/docs/Web/API/Element/getAttribute',
    'createElement': 'https://developer.mozilla.org/en-US/docs/Web/API/Document/createElement',
    'appendChild': 'https://developer.mozilla.org/en-US/docs/Web/API/Node/appendChild',
    'removeChild': 'https://developer.mozilla.org/en-US/docs/Web/API/Node/removeChild',
    'Event': 'https://developer.mozilla.org/en-US/docs/Web/API/Event',
    'CustomEvent': 'https://developer.mozilla.org/en-US/docs/Web/API/CustomEvent',
    'WebSocket': 'https://developer.mozilla.org/en-US/docs/Web/API/WebSocket',
    'Canvas': 'https://developer.mozilla.org/en-US/docs/Web/API/Canvas_API',
    'getContext': 'https://developer.mozilla.org/en-US/docs/Web/API/HTMLCanvasElement/getContext',
    'requestAnimationFrame': 'https://developer.mozilla.org/en-US/docs/Web/API/Window/requestAnimationFrame',
    'setInterval': 'https://developer.mozilla.org/en-US/docs/Web/API/setInterval',
    'setTimeout': 'https://developer.mozilla.org/en-US/docs/Web/API/setTimeout',
    'clearInterval': 'https://developer.mozilla.org/en-US/docs/Web/API/clearInterval',
    'clearTimeout': 'https://developer.mozilla.org/en-US/docs/Web/API/clearTimeout',
    'FormData': 'https://developer.mozilla.org/en-US/docs/Web/API/FormData',
    'FileReader': 'https://developer.mozilla.org/en-US/docs/Web/API/FileReader',
    'Blob': 'https://developer.mozilla.org/en-US/docs/Web/API/Blob',
    'URL.createObjectURL': 'https://developer.mozilla.org/en-US/docs/Web/API/URL/createObjectURL_static',
    'history.pushState': 'https://developer.mozilla.org/en-US/docs/Web/API/History/pushState',
    'navigator.geolocation': 'https://developer.mozilla.org/en-US/docs/Web/API/Geolocation_API',
    'IntersectionObserver': 'https://developer.mozilla.org/en-US/docs/Web/API/IntersectionObserver',
    'MutationObserver': 'https://developer.mozilla.org/en-US/docs/Web/API/MutationObserver',
    'ResizeObserver': 'https://developer.mozilla.org/en-US/docs/Web/API/ResizeObserver',
    'JSON.parse': 'https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/JSON/parse',
    'JSON.stringify': 'https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/JSON/stringify',
    'Promise': 'https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Promise',
    'async/await': 'https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Statements/async_function',
    'try/catch': 'https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Statements/try...catch',
    'Array.map': 'https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/map',
    'Array.filter': 'https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/filter',
    'Array.reduce': 'https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/reduce',
    'Array.forEach': 'https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/forEach',
    'Array.find': 'https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/find',
    'Array.includes': 'https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/includes',
    'Object.keys': 'https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Object/keys',
    'Object.values': 'https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Object/values',
    'Object.entries': 'https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Object/entries',
    'Object.assign': 'https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Object/assign',
    'Spread syntax': 'https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/Spread_syntax',
    'Destructuring': 'https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/Destructuring_assignment',
    'Template literals': 'https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Template_literals',
    'Arrow functions': 'https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Functions/Arrow_functions',
    'Modules': 'https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Modules',
    'import/export': 'https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Statements/import',
    'Flexbox': 'https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_flexible_box_layout/Basic_concepts_of_flexbox',
    'Grid': 'https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_grid_layout/Basic_concepts_of_grid_layout',
    'Media queries': 'https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_media_queries/Using_media_queries',
    'CSS variables': 'https://developer.mozilla.org/en-US/docs/Web/CSS/Using_CSS_custom_properties',
    'CSS transitions': 'https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_transitions/Using_CSS_transitions',
    'CSS animations': 'https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_animations/Using_CSS_animations',
    'position': 'https://developer.mozilla.org/en-US/docs/Web/CSS/position',
    'z-index': 'https://developer.mozilla.org/en-US/docs/Web/CSS/z-index',
    'box-sizing': 'https://developer.mozilla.org/en-US/docs/Web/CSS/box-sizing',
    'display': 'https://developer.mozilla.org/en-US/docs/Web/CSS/display',
    'overflow': 'https://developer.mozilla.org/en-US/docs/Web/CSS/overflow',
    'fs.readFileSync': 'https://nodejs.org/api/fs.html#fsreadfilesyncpath-options',
    'fs.writeFileSync': 'https://nodejs.org/api/fs.html#fswritefilesyncdata-options',
    'fs.existsSync': 'https://nodejs.org/api/fs.html#fsexistssyncpath',
    'fs.mkdirSync': 'https://nodejs.org/api/fs.html#fsmkdirsyncpath-options',
    'fs.readdirSync': 'https://nodejs.org/api/fs.html#fsreaddirsyncpath-options',
    'fs.statSync': 'https://nodejs.org/api/fs.html#fsstatsyncpath-options',
    'fs.watch': 'https://nodejs.org/api/fs.html#fswatchfilename-options-listener',
    'path.join': 'https://nodejs.org/api/path.html#pathjoinpaths',
    'path.resolve': 'https://nodejs.org/api/path.html#pathresolvepaths',
    'path.basename': 'https://nodejs.org/api/path.html#pathbasenamepath-suffix',
    'path.dirname': 'https://nodejs.org/api/path.html#pathdirnamepath',
    'path.extname': 'https://nodejs.org/api/path.html#pathextnamepath',
    'process.env': 'https://nodejs.org/api/process.html#processenv',
    'process.cwd': 'https://nodejs.org/api/process.html#processcwd',
    'Buffer': 'https://nodejs.org/api/buffer.html',
    'EventEmitter': 'https://nodejs.org/api/events.html#class-eventemitter',
    'http.createServer': 'https://nodejs.org/api/http.html#httpcreateserveroptions-requestlistener',
    'crypto': 'https://nodejs.org/api/crypto.html',
    'npm install': 'https://docs.npmjs.com/cli/v10/commands/npm-install',
    'package.json': 'https://docs.npmjs.com/cli/v10/configuring-npm/package-json',
    'npm scripts': 'https://docs.npmjs.com/cli/v10/using-npm/scripts',
    '.env': 'https://www.npmjs.com/package/dotenv',
    'dotenv': 'https://www.npmjs.com/package/dotenv',
    'chokidar': 'https://github.com/paulmillr/chokidar#readme',
    'commander': 'https://github.com/tj/commander.js#readme',
    'handlebars': 'https://handlebarsjs.com/guide/',
    'script type=module': 'https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Modules',
    'defer': 'https://developer.mozilla.org/en-US/docs/Web/HTML/Attributes/defer',
    'async': 'https://developer.mozilla.org/en-US/docs/Web/HTML/Attributes/async',
    'data attributes': 'https://developer.mozilla.org/en-US/docs/Learn_web_development/Howto/Solve_HTML_problems/Use_data_attributes',
    'semantic HTML': 'https://developer.mozilla.org/en-US/docs/Glossary/Semantics',
    'meta viewport': 'https://developer.mozilla.org/en-US/docs/Web/HTML/Viewport_meta_tag',
    'console.log': 'https://developer.mozilla.org/en-US/docs/Web/API/console/log_static',
    'debugger': 'https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Statements/debugger',
    'JSON': 'https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/JSON',
    'RegExp': 'https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/RegExp',
    'Date': 'https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Date',
    'Map': 'https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Map',
    'Set': 'https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Set',
    'WeakMap': 'https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/WeakMap',
    'WeakSet': 'https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/WeakSet',
}

def resolve_docs(concept: str) -> List[str]:
    """Up to two doc URLs for a concept: exact key matches first, then substring matches."""
    lower = concept.lower()
    results: List[str] = []

    for key, url in DOCS_MAP.items():
        if key.lower() == lower:
            results.append(url)
            if len(results) >= 2:
                break

    if len(results) < 2:
        for key, url in DOCS_MAP.items():
            k = key.lower()
            if k in lower or lower in k:
                if url not in results:
                    results.append(url)
                    if len(results) >= 2:
                        break

    return results


_KNOWN_KEYWORDS = [
    "fetch", "localStorage", "Promise", "async", "await",
    "Flexbox", "Grid", "Canvas", "WebSocket", "EventEmitter",
    "fs.readFileSync", "fs.writeFileSync", "path.join",
    "JSON.parse", "JSON.stringify", "Array.map", "Array.filter",
]


def extract_concepts(step_content: str) -> List[str]:
    """Pick likely concepts out of a step: `code spans` plus a few known keywords."""
    concepts: List[str] = []

    for block in re.findall(r"`([^`]+)`", step_content):
        clean = block.strip()
        if "/" in clean and "." not in clean:
            continue
        if clean.startswith("npm "):
            continue
        if len(clean) < 3:
            continue
        if " " in clean:
            continue
        concepts.append(clean)

    for kw in _KNOWN_KEYWORDS:
        if kw in step_content and kw not in concepts:
            concepts.append(kw)

    return concepts[:5]
