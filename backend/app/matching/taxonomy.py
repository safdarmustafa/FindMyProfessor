from __future__ import annotations

"""
Hand-curated vocabulary that sits on top of the research-area catalog.

ALIASES maps a catalog label to the everyday phrases students actually write
on a CV ("NLP", "object detection", "LLMs"). A phrase only ever resolves to a
label that exists in the live catalog, so nothing here can invent an area.

RELATED lists pairs of catalog labels that are close neighbours but are kept
as separate labels on purpose (see the catalog's _comment). A related pair
earns partial credit in scoring; it is never reported as a shared area.
Generic labels (Machine Learning, Artificial Intelligence, Computer Science)
are deliberately left out of RELATED so they cannot inflate scores.
"""

import re
from functools import lru_cache

from app.matching.normalize import normalize_label

ALIASES: dict[str, tuple[str, ...]] = {
    "Machine Learning": (
        "ml", "statistical learning", "supervised learning", "unsupervised learning",
    ),
    "Computer Vision": (
        "image processing", "image segmentation", "semantic segmentation",
        "instance segmentation", "object detection", "image classification",
        "image recognition", "visual recognition", "video understanding",
        "video analysis", "scene understanding", "pose estimation",
        "3d vision", "3d reconstruction", "optical character recognition",
        "face recognition", "facial recognition",
    ),
    "Natural Language Processing": (
        "nlp", "natural language understanding", "nlu", "computational linguistics",
        "text mining", "text classification", "machine translation",
        "question answering", "sentiment analysis", "named entity recognition",
        "text summarization", "dialogue systems", "dialog systems", "chatbots",
    ),
    "Robotics": (
        "robot", "robots", "robotic", "slam", "autonomous navigation",
        "motion planning", "robot learning", "legged locomotion",
        "autonomous vehicles", "autonomous driving", "self-driving", "drones",
        "uav", "uavs",
    ),
    "Deep Learning": (
        "neural networks", "neural network", "deep neural networks",
        "convolutional neural networks", "convolutional neural network",
        "cnn", "cnns", "rnn", "rnns", "lstm", "transformer models",
        "representation learning", "self-supervised learning",
    ),
    "Trustworthy AI": (
        "ai safety", "adversarial robustness", "adversarial attacks",
        "adversarial machine learning", "differential privacy",
        "privacy-preserving machine learning", "ai security", "robust machine learning",
    ),
    "Medical AI": (
        "medical imaging", "medical image analysis", "medical image segmentation",
        "medical diagnosis", "clinical ai", "radiology", "diabetic retinopathy",
        "ai in medicine", "ai for medicine", "osteoarthritis", "x-ray", "x-rays", "mri",
        "ct scans", "tumor detection", "tumour detection", "cancer detection",
        "disease detection", "disease prediction", "diabetes", "retinal imaging",
        "histopathology", "medical images",
    ),
    "Healthcare AI": (
        "ai in healthcare", "ai for healthcare", "health informatics", "digital health",
        "clinical decision support", "electronic health records", "ehr",
    ),
    "Biomedical AI": (
        "biomedical informatics", "biomedical data", "biomedical engineering",
    ),
    "Computational Biology": (
        "bioinformatics", "genomics", "computational genomics", "protein structure",
        "protein folding", "systems biology",
    ),
    "AI for Science": (
        "scientific machine learning", "physics-informed neural networks",
        "physics-informed machine learning", "materials discovery", "drug discovery",
        "molecular modeling", "ai4science",
    ),
    "Efficient AI": (
        "model compression", "quantization", "network pruning", "model pruning",
        "knowledge distillation", "efficient deep learning", "efficient inference",
        "neural architecture search",
    ),
    "Edge AI": (
        "tinyml", "on-device ai", "on-device machine learning", "embedded ai",
        "embedded machine learning", "edge computing", "iot", "internet of things",
    ),
    "Data Science": (
        "data analytics", "data analysis", "data mining", "big data",
        "predictive analytics", "time series analysis", "time series forecasting",
    ),
    "Large Language Models": (
        "llm", "llms", "large language model", "language models", "language model",
        "gpt", "chatgpt", "instruction tuning", "rlhf", "prompt engineering",
        "retrieval-augmented generation", "rag", "in-context learning",
    ),
    "Reinforcement Learning": (
        "deep reinforcement learning", "rl", "imitation learning", "multi-armed bandits",
        "bandit algorithms", "markov decision processes", "policy optimization",
    ),
    "Foundation Models": (
        "foundation model", "pretrained models", "pre-trained models",
    ),
    "Multimodal Learning": (
        "multimodal", "multi-modal", "vision-language", "vision and language",
        "vision-language models", "vlm", "vlms", "audio-visual",
    ),
    "AI Agents": (
        "ai agent", "agentic ai", "agentic", "autonomous agents", "llm agents",
        "intelligent agents",
    ),
    "AI Systems": (
        "ml systems", "machine learning systems", "systems for machine learning",
        "systems for ml", "mlops", "distributed training", "model serving",
        "ml infrastructure",
    ),
    "Human-Centered AI": (
        "human-computer interaction", "hci", "human-ai interaction",
        "human-ai collaboration", "human-centered computing", "human-centred ai",
    ),
    "Information Retrieval": (
        "search engines", "semantic search", "web search", "learning to rank",
        "dense retrieval",
    ),
    "Responsible AI": (
        "ai ethics", "ethical ai", "algorithmic fairness", "fairness in machine learning",
        "ai fairness", "ai governance", "ai policy",
    ),
    "Generative AI": (
        "generative models", "generative modeling", "generative modelling",
        "diffusion models", "diffusion model", "gan", "gans",
        "generative adversarial networks", "variational autoencoders",
        "text-to-image", "image generation",
    ),
    "Explainable AI": (
        "xai", "explainability", "interpretability", "interpretable machine learning",
        "explainable machine learning",
    ),
    "Recommender Systems": (
        "recommendation systems", "recommendation system", "recommender system",
        "collaborative filtering",
    ),
    "AI Media Synthesis": (
        "deepfake", "deepfakes", "deepfake detection", "media forensics", "video synthesis",
    ),
    "Embodied AI": ("embodied intelligence", "embodied agents"),
    "Multi-Agent Systems": (
        "multi-agent", "multiagent", "multi-agent reinforcement learning", "marl",
    ),
    "Spatial AI": ("spatial computing",),
    "Speech / Language AI": (
        "speech recognition", "automatic speech recognition", "asr", "speech processing",
        "speech synthesis", "text-to-speech", "spoken language",
    ),
}

RELATED: tuple[tuple[str, str], ...] = (
    ("Medical AI", "Healthcare AI"),
    ("Medical AI", "Biomedical AI"),
    ("Healthcare AI", "Biomedical AI"),
    ("Biomedical AI", "Computational Biology"),
    ("Computational Biology", "AI for Science"),
    ("Natural Language Processing", "Large Language Models"),
    ("Natural Language Processing", "Speech / Language AI"),
    ("Large Language Models", "Foundation Models"),
    ("Large Language Models", "Generative AI"),
    ("Foundation Models", "Generative AI"),
    ("Generative AI", "AI Media Synthesis"),
    ("Multimodal Learning", "Multimodal AI"),
    ("Trustworthy AI", "Responsible AI"),
    ("Trustworthy AI", "Explainable AI"),
    ("Responsible AI", "Explainable AI"),
    ("Efficient AI", "Edge AI"),
    ("Efficient AI", "AI Systems"),
    ("Edge AI", "AI Systems"),
    ("Robotics", "Embodied AI"),
    ("Embodied AI", "Spatial AI"),
    ("AI Agents", "Multi-Agent Systems"),
    ("Computer Vision", "Object Recognition"),
    ("Information Retrieval", "Recommender Systems"),
)

RELATED_CREDIT = 0.5


def related_labels(label: str) -> set[str]:
    """Normalized labels that are close neighbours of `label`."""
    return _related_index().get(normalize_label(label), set())


@lru_cache(maxsize=1)
def _related_index() -> dict[str, set[str]]:
    index: dict[str, set[str]] = {}
    for left, right in RELATED:
        a, b = normalize_label(left), normalize_label(right)
        index.setdefault(a, set()).add(b)
        index.setdefault(b, set()).add(a)
    return index


def terms_for(label: str) -> tuple[str, ...]:
    """The label itself followed by its aliases."""
    for name, aliases in ALIASES.items():
        if normalize_label(name) == normalize_label(label):
            return (label, *aliases)
    return (label,)


@lru_cache(maxsize=256)
def label_patterns(catalog_names: tuple[str, ...]) -> tuple[tuple[str, re.Pattern[str]], ...]:
    """One compiled, case-insensitive, word-bounded pattern per catalog label."""
    compiled: list[tuple[str, re.Pattern[str]]] = []
    seen: set[str] = set()
    for name in catalog_names:
        key = normalize_label(name)
        if not key or key in seen:
            continue
        seen.add(key)
        terms = sorted({t.strip() for t in terms_for(name) if t.strip()}, key=len, reverse=True)
        body = "|".join(_term_regex(t) for t in terms)
        compiled.append((name, re.compile(r"(?<!\w)(?:" + body + r")(?!\w)", re.IGNORECASE)))
    return tuple(compiled)


def _term_regex(term: str) -> str:
    # Let "Speech / Language AI" or "multi-agent" tolerate spacing/hyphen variants.
    parts = [re.escape(p) for p in re.split(r"[\s\-]+", term) if p]
    return r"[\s\-]*".join(parts)
