import os
import tempfile


def tmp_project() -> str:
    return tempfile.mkdtemp(prefix="jibun-test-")


def write(directory, rel, content):
    p = os.path.join(directory, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(content)


CURRICULUM = """A tiny todo app.

## Day 0: Setup

### Step 1: Scaffold

**What?**  
Create files.

**Why?**  
Structure.

**How?**  
- Create files.

**Validation:**  
Jibun checks for: `index.html` exists && `src/app.js` exists && `style.css` exists.

---

### Step 2: Markup

**What?**  
Add a list.

**Why?**  
Structure.

**How?**  
- Edit index.html

**Validation:**  
Jibun checks for: `index.html` exists && contains `<ul id="todos">`.

---

## Day 1: Behaviour

### Step 3: Add items

**What?**  
Wire the button.

**Why?**  
Events.

**How?**  
- Edit app.js

**Validation:**  
Jibun checks for: `src/app.js` exists && contains `addEventListener` && `node_modules/ws` folder exists.

---

## Next Steps

- Extend it.
"""
