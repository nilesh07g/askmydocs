# USER MESSAGE — paste into LangSmith Playground "Human" / "User" field

This is the test input for the question: **"who is the author?"**

Copy everything between the `---` lines below (not the `---` lines themselves).
The XML tags `<context>`, `</context>`, `<question>`, `</question>` ARE part of
what you paste — do not strip them.

---

<context>
[Page 146]
About the Author
One of the most popular writers on Instagram, Rithvik's words have never failed to comfort his readers. His words feel like home and refuse to leave your heart. His first book, 'Warmth' was published in 2021, and it was very well-received. Rithvik lives a simple life and wants to inspire people to hold onto hope and love themselves more. You can connect with him on Instagram: @wordsofrithvik.

[Page 145]
If you enjoyed reading this book, please write to Rithvik at @wordsofrithvik on Instagram. He'd love to hear from you!
Also by the author:
Warmth

[Page 3]
Copyright © Rithvik Singh 2024
All Rights Reserved.
e-ISBN 979-8-89277-741-4

[Page 133]
Whenever I've fallen in love, it's been one-sided. I've dated people. I've lived with them. I've spent Valentine's Day with them and taken trips with them. But whenever I've fallen in love with them, it's been one-sided. I've got the habit of always feeling more than the other person. I author my own pain by always giving out more than I ever receive.

[Page 9]
here's a dying patient who has fallen in love with life. An orphan who thinks his parents are still alive. A soldier's wife waiting for a letter from her husband who died. A wilted flower waiting for spring to arrive. We're all so different but so alike—wanting things we cannot get, praying to a God who refuses to listen.
</context>

<question>
who is the author?
</question>

---

# Settings for Playground

| Setting | Value |
|---|---|
| Model | `llama-3.3-70b-versatile` (Groq) |
| Temperature | `0.0` |
| Max tokens | `1024` |
| Top-p | leave default |

# What a good output looks like

Expected (any of these is fine):
- "The author is Rithvik Singh (p. 3)."
- "Rithvik Singh (p. 3) — a writer popular on Instagram (@wordsofrithvik) whose first book Warmth was published in 2021 (p. 146)."

Bad outputs (these mean the prompt still has a bug):
- "2 million followers..."
- "bestselling books..." (without page citation)
- Output starting with `:` or "Answer:"
- Invented `Passage 6 — page 147:` or similar
- Long bio with details not in the context

# More test cases to try after the first one works

Replace `<question>` content with these one at a time:

1. `what other book has this author written?` → expect "Warmth (p. 145)" or similar
2. `what year was the author born?` → MUST output exactly "The passages I have access to don't cover that."
3. `summarize this book` → 1–3 short paragraphs synthesizing only what's in the 5 passages
4. `hi` → one warm sentence (no <context> block needed for this test)
