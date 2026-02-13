const year = document.getElementById("year");
if (year) {
  year.textContent = new Date().getFullYear();
}

const observer = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("visible");
      }
    });
  },
  { threshold: 0.14 }
);

document.querySelectorAll(".reveal").forEach((node, index) => {
  node.style.transitionDelay = `${Math.min(index * 35, 280)}ms`;
  observer.observe(node);
});

const statObserver = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) {
        return;
      }

      const el = entry.target;
      const target = Number(el.dataset.target || "0");
      const duration = 900;
      const start = performance.now();

      function tick(now) {
        const progress = Math.min((now - start) / duration, 1);
        el.textContent = Math.floor(target * (1 - Math.pow(1 - progress, 3))).toString();
        if (progress < 1) {
          requestAnimationFrame(tick);
        }
      }

      requestAnimationFrame(tick);
      statObserver.unobserve(el);
    });
  },
  { threshold: 0.3 }
);

document.querySelectorAll(".stat-number").forEach((node) => statObserver.observe(node));

const tiltElements = document.querySelectorAll(".tilt");
tiltElements.forEach((card) => {
  card.addEventListener("mousemove", (event) => {
    const rect = card.getBoundingClientRect();
    const px = (event.clientX - rect.left) / rect.width;
    const py = (event.clientY - rect.top) / rect.height;
    const rx = (0.5 - py) * 5;
    const ry = (px - 0.5) * 7;
    card.style.transform = `perspective(700px) rotateX(${rx}deg) rotateY(${ry}deg) translateY(-2px)`;
  });

  card.addEventListener("mouseleave", () => {
    card.style.transform = "";
  });
});

const canvas = document.getElementById("bg-canvas");
const ctx = canvas?.getContext("2d");
const particles = [];

function resizeCanvas() {
  if (!canvas) {
    return;
  }

  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;
}

function initParticles() {
  if (!canvas) {
    return;
  }

  particles.length = 0;
  const total = Math.max(44, Math.floor(window.innerWidth / 26));
  for (let i = 0; i < total; i += 1) {
    particles.push({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      vx: (Math.random() - 0.5) * 0.25,
      vy: (Math.random() - 0.5) * 0.25,
      r: Math.random() * 2 + 0.4,
    });
  }
}

function drawParticles() {
  if (!ctx || !canvas) {
    return;
  }

  ctx.clearRect(0, 0, canvas.width, canvas.height);

  particles.forEach((point, i) => {
    point.x += point.vx;
    point.y += point.vy;

    if (point.x <= 0 || point.x >= canvas.width) {
      point.vx *= -1;
    }

    if (point.y <= 0 || point.y >= canvas.height) {
      point.vy *= -1;
    }

    ctx.fillStyle = "rgba(29, 106, 97, 0.55)";
    ctx.beginPath();
    ctx.arc(point.x, point.y, point.r, 0, Math.PI * 2);
    ctx.fill();

    for (let j = i + 1; j < particles.length; j += 1) {
      const other = particles[j];
      const dx = point.x - other.x;
      const dy = point.y - other.y;
      const dist = Math.hypot(dx, dy);
      if (dist < 120) {
        ctx.strokeStyle = `rgba(218, 90, 42, ${0.16 - dist / 850})`;
        ctx.lineWidth = 0.8;
        ctx.beginPath();
        ctx.moveTo(point.x, point.y);
        ctx.lineTo(other.x, other.y);
        ctx.stroke();
      }
    }
  });

  requestAnimationFrame(drawParticles);
}

resizeCanvas();
initParticles();
drawParticles();
window.addEventListener("resize", () => {
  resizeCanvas();
  initParticles();
});

const sampleText =
  "The support experience was surprisingly smooth. The chatbot resolved two billing issues in under three minutes, but the handoff to a human agent still felt delayed when I asked for a refund timeline.";

const stopWords = new Set([
  "the",
  "and",
  "for",
  "that",
  "this",
  "with",
  "was",
  "are",
  "but",
  "from",
  "have",
  "had",
  "into",
  "your",
  "you",
  "our",
  "their",
  "they",
  "them",
  "his",
  "her",
  "its",
  "when",
  "where",
  "what",
  "who",
  "will",
  "would",
  "could",
  "should",
  "can",
  "just",
  "than",
  "then",
  "been",
  "were",
  "about",
  "over",
  "under",
  "after",
  "before",
  "while",
  "there",
  "here",
  "some",
  "more",
  "most",
  "very",
  "still",
  "only",
  "also",
  "onto",
  "does",
  "did",
]);

const positiveWords = new Set([
  "good",
  "great",
  "excellent",
  "smooth",
  "helpful",
  "fast",
  "easy",
  "resolved",
  "clear",
  "improved",
  "love",
  "success",
  "effective",
]);

const negativeWords = new Set([
  "bad",
  "slow",
  "delay",
  "delayed",
  "confusing",
  "issue",
  "issues",
  "error",
  "bug",
  "worst",
  "hard",
  "difficult",
  "refund",
  "problem",
]);

const input = document.getElementById("input-text");
const output = document.getElementById("analysis-output");
const analyzeBtn = document.getElementById("analyze-btn");
const clearBtn = document.getElementById("clear-btn");
const sampleBtn = document.getElementById("sample-btn");

function tokenize(value) {
  return (value.toLowerCase().match(/[a-z']+/g) || []).filter((word) => word.length > 1);
}

function analyzeText(value) {
  const words = tokenize(value);
  const sentences = (value.match(/[.!?]+/g) || []).length || (value.trim() ? 1 : 0);
  const chars = value.replace(/\s/g, "").length;
  const readingTime = Math.max(1, Math.round(words.length / 220));

  let sentimentScore = 0;
  words.forEach((word) => {
    if (positiveWords.has(word)) {
      sentimentScore += 1;
    }

    if (negativeWords.has(word)) {
      sentimentScore -= 1;
    }
  });

  const tone = sentimentScore > 1 ? "Positive" : sentimentScore < -1 ? "Negative" : "Neutral";

  const freq = new Map();
  words.forEach((word) => {
    if (stopWords.has(word)) {
      return;
    }

    freq.set(word, (freq.get(word) || 0) + 1);
  });

  const keywords = [...freq.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 6)
    .map(([word, count]) => `${word} (${count})`);

  const lexicalDiversity = words.length ? (new Set(words).size / words.length) * 100 : 0;

  return {
    words: words.length,
    sentences,
    chars,
    readingTime,
    tone,
    lexicalDiversity: lexicalDiversity.toFixed(1),
    keywords,
  };
}

function renderAnalysis(stats) {
  if (!output) {
    return;
  }

  output.innerHTML = `
    <div class="kpi">
      <article><h4>Words</h4><p>${stats.words}</p></article>
      <article><h4>Sentences</h4><p>${stats.sentences}</p></article>
      <article><h4>Characters</h4><p>${stats.chars}</p></article>
      <article><h4>Read Time</h4><p>${stats.readingTime} min</p></article>
    </div>
    <p><strong>Tone:</strong> ${stats.tone}</p>
    <p><strong>Lexical diversity:</strong> ${stats.lexicalDiversity}%</p>
    <p><strong>Top keywords:</strong></p>
    <div class="tags">
      ${(stats.keywords.length ? stats.keywords : ["none"]) 
        .map((word) => `<span class="tag">${word}</span>`)
        .join("")}
    </div>
  `;
}

analyzeBtn?.addEventListener("click", () => {
  const value = input?.value?.trim() || "";
  if (!value) {
    if (output) {
      output.innerHTML = '<p class="mono">Add some text first to run analysis.</p>';
    }
    return;
  }

  renderAnalysis(analyzeText(value));
});

clearBtn?.addEventListener("click", () => {
  if (input) {
    input.value = "";
  }
  if (output) {
    output.innerHTML = '<p class="mono">Awaiting input...</p>';
  }
});

sampleBtn?.addEventListener("click", () => {
  if (input) {
    input.value = sampleText;
  }
  renderAnalysis(analyzeText(sampleText));
});