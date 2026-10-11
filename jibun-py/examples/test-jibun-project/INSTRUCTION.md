## Project Overview  
Build a collaborative whiteboard where users draw freehand on an HTML canvas, pick colors, and clear the board. Drawing actions are sent over a WebSocket connection so every participant sees updates instantly.

### Final Folder Structure
```
real-time-whiteboard/
├─ index.html
├─ style.css
├─ src/
│  ├─ app.js
│  └─ socket.js
└─ server/
   └─ server.js
```

**Tech stack** – HTML, CSS, vanilla JavaScript, Node.js (for the WebSocket server only, no frameworks).

---

### Step 1: Project Scaffold  

**What?**  
Create the root folder and the basic files needed for the client and server.

**Why?**  
A clear directory layout separates static assets (`index.html`, `style.css`) from application logic (`src/`) and server code (`server/`). This makes the codebase maintainable as the project grows.

**How?**  
- Create `real-time-whiteboard/` folder. Inside it, create `index.html`, `style.css`, `src/`, and `server/`.  
- Inside `src/` add empty `app.js` and `socket.js`.  
- Inside `server/` add empty `server.js`.  
- Read: https://developer.mozilla.org/en-US/docs/Learn/Getting_started_with_the_web/HTML_basics  

**Validation:**  
`index.html` exists && `style.css` exists && `src/app.js` exists && `src/socket.js` exists && `server/server.js` exists.  

---

### Step 2: Basic HTML Layout  

**What?**  
Add a `<canvas>` element, a color picker, and a “Clear” button to `index.html`.

**Why?**  
The canvas is the drawing surface; UI controls let users change color and reset the board. Keeping the markup minimal reduces layout reflows and simplifies later scripting.

**How?**  
- Edit `index.html` to include a `<canvas id="board">`, `<input type="color" id="colorPicker">`, and `<button id="clearBtn">Clear</button`.  
- Link `style.css` and `src/app.js`.  
- Read: https://developer.mozilla.org/en-US/docs/Web/HTML/Element/canvas  

**Validation:**  
`index.html` exists && contains `<canvas id="board"` && contains `id="colorPicker"` && contains `id="clearBtn"`.

---

### Step 3: Canvas Styling  

**What?**  
Style the canvas to fill most of the viewport and give the controls a clean layout.

**Why?**  
Proper sizing ensures drawing coordinates map directly to mouse positions. A simple CSS layout makes the UI intuitive without extra JavaScript calculations.

**How?**  
- Edit `style.css` to set `#board { border:1px solid #ccc; width:100%; height:80vh; }` and style the picker/button.  
- Read: https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_Flexible_Box_Layout/Basic_Concepts_of_Flexbox  

**Validation:**  
`style.css` exists && contains `#board` && contains `border:`.

---

### Step 4: Freehand Drawing Logic  

**What?**  
Implement mouse event handling in `src/app.js` to draw lines on the canvas as the user drags.

**Why?**  
Capturing `mousedown`, `mousemove`, and `mouseup` lets us translate pointer movement into continuous strokes, the core of a whiteboard.

**How?**  
- In `src/app.js`, obtain the canvas context, listen for the three mouse events, and use `ctx.lineTo` / `ctx.stroke` to render.  
- Store the current color from `#colorPicker`.  
- Read: https://developer.mozilla.org/en-US/docs/Web/API/Canvas_API/Tutorial/Drawing_shapes  

**Validation:**  
`src/app.js` exists && contains `addEventListener('mousedown'` && contains `getContext('2d')`.

---

### Step 5: Simple WebSocket Server  

**What?**  
Create a Node.js WebSocket server that broadcasts any received message to all connected clients.

**Why?**  
A central hub relays drawing data so every participant stays in sync. Using the lightweight `ws` library avoids any framework overhead.

**How?**  
- Run `npm init -y` in the project root (optional but creates `package.json`).  
- Install the WebSocket library: `npm install ws`.  
- In `server/server.js`, import `ws`, create a `WebSocket.Server` listening on port 8080, and on each connection forward incoming messages to all other sockets.  
- Read: https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API/Writing_WebSocket_servers  

**Validation:**  
`server/server.js` exists && contains `new WebSocket.Server` && contains `ws.on('message'` && `node_modules/ws` folder exists.

---

### Step 6: Client‑Side WebSocket Connection  

**What?**  
Open a WebSocket from the browser and expose a `send` function in `src/socket.js`.

**Why?**  
Encapsulating the socket logic separates networking from drawing code, making each module easier to test and evolve.

**How?**  
- In `src/socket.js`, instantiate `new WebSocket('ws://localhost:8080')`.  
- Export a `broadcast(data)` function that stringifies `data` and calls `socket.send`.  
- Listen for `socket.onmessage` and dispatch a custom event (e.g., `draw`) with the parsed payload.  
- Read: https://developer.mozilla.org/en-US/docs/Web/API/WebSocket  

**Validation:**  
`src/socket.js` exists && contains `new WebSocket('ws://localhost:8080'` && contains `socket.send(` && contains `socket.onmessage`.

---

### Step 7: Emit Local Strokes  

**What?**  
Modify `src/app.js` to send each drawn segment (start x,y, end x,y, color) through the WebSocket.

**Why?**  
Transmitting only the minimal segment data keeps bandwidth low and ensures other clients can reconstruct the exact stroke.

**How?**  
- Import `broadcast` from `src/socket.js`.  
- Inside the `mousemove` handler, after drawing locally, call `broadcast({type:'stroke', from:{x,y}, to:{x2,y2}, color})`.  
- Read: https://developer.mozilla.org/en-US/docs/Web/API/CanvasRenderingContext2D/lineTo  

**Validation:**  
`src/app.js` exists && contains `broadcast(` && contains `'stroke'`.

---

### Step 8: Render Remote Strokes  

**What?**  
Listen for the custom `draw` event (or directly for WebSocket messages) and replay incoming strokes on the canvas.

**Why?**  
Applying remote strokes keeps every participant’s view identical, achieving real‑time collaboration.

**How?**  
- In `src/app.js`, add a listener for the event emitted by `socket.js`.  
- When a `stroke` payload arrives, use the same canvas context to draw the segment with the supplied color.  
- Read: https://developer.mozilla.org/en-US/docs/Web/API/CustomEvent  

**Validation:**  
`src/app.js` exists && contains `addEventListener('draw'` && contains `if (msg.type === 'stroke')`.

---

### Step 9: Clear‑Canvas Synchronization  

**What?**  
Make the “Clear” button erase the local canvas and broadcast a `clear` command to all peers.

**Why?**  
All users must see the same empty board; broadcasting a single command guarantees consistency without each client guessing when to clear.

**How?**  
- In `src/app.js`, attach a click listener to `#clearBtn` that calls `ctx.clearRect` and then `broadcast({type:'clear'})`.  
- Extend the remote‑stroke listener to handle `type:'clear'` by clearing the canvas.  
- Read: https://developer.mozilla.org/en-US/docs/Web/API/CanvasRenderingContext2D/clearRect  

**Validation:**  
`src/app.js` exists && contains `broadcast({type:'clear'}` && contains `if (msg.type === 'clear')`.

---

### Step 10: Color Picker Integration  

**What?**  
Ensure the selected color travels with each stroke and updates the UI when a remote user draws in a different hue.

**Why?**  
Color is part of the drawing state; transmitting it preserves the visual intent of each participant.

**How?**  
- In `src/app.js`, read `#colorPicker.value` whenever a new stroke starts and include it in the broadcast payload.  
- When rendering remote strokes, set `ctx.strokeStyle` to the received `color`.  
- Read: https://developer.mozilla.org/en-US/docs/Web/API/CanvasRenderingContext2D/strokeStyle  

**Validation:**  
`src/app.js` exists && contains `strokeStyle = msg.color` && contains `colorPicker.value`.

---

## Next Steps  

1. **Persist Sessions** – Add a simple in‑memory store on the server to replay existing strokes to newcomers.  
2. **Undo/Redo Stack** – Record each stroke locally and allow users to revert their last action, broadcasting undo events.  
3. **Touch Support** – Extend the drawing handlers to work with `pointer` events so tablets and phones can join the whiteboard.  