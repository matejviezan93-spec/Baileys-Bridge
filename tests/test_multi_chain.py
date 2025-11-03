import importlib.util
import json
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

MODULE_DIR = Path(__file__).resolve().parents[1] / "modules" / "bridge-ai" / "app"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    if spec.loader is None:  # pragma: no cover - loader resolution failure
        raise RuntimeError(f"Unable to load module from {path}")
    spec.loader.exec_module(module)
    return module


mc = load_module("bridge_ai_multi_chain", MODULE_DIR / "multi_chain.py")

app = FastAPI()
app.include_router(mc.router)


class StubClient:
    def __init__(self, *, model_name: str, text: str, input_tokens: int, output_tokens: int):
        self.model_name = model_name
        self._response = mc.LLMResponse(
            text=text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            metadata={"model": model_name},
        )
        self.calls = 0
        self.last_messages = None

    async def generate(self, messages, *, max_output_tokens=None, temperature=0.0, top_p=0.0):
        self.calls += 1
        self.last_messages = list(messages)
        return self._response


def compute_expected_cost(responses: dict[str, mc.LLMResponse]) -> float:
    total = 0.0
    for role, response in responses.items():
        model = response.metadata["model"]
        pricing = mc.MODEL_PRICING[model]
        total += (
            response.input_tokens * pricing.input_usd_per_mtok
            + response.output_tokens * pricing.output_usd_per_mtok
        ) / 1_000_000
    return total


def test_multi_chain_endpoint_aggregates_chain(tmp_path, monkeypatch):
    analyzer = StubClient(
        model_name="llama-3.1-8b",
        text="- Tone: Friendly\n- Persona: Bridge agent\n- Context: Symbióza pilot\n",
        input_tokens=500,
        output_tokens=200,
    )
    imitator = StubClient(
        model_name="gpt-4o-mini",
        text="Draft response body with detailed narrative about Symbióza.",
        input_tokens=1500,
        output_tokens=1100,
    )
    post_editor = StubClient(
        model_name="llama-3.3-70b",
        text="Edited narrative with improved cadence.",
        input_tokens=1100,
        output_tokens=1100,
    )
    masker = StubClient(
        model_name="llama-3.1-8b",
        text="Final story with subtle human-like pacing.",
        input_tokens=1100,
        output_tokens=1100,
    )

    stages = [
        mc.Stage(
            config=mc.StageConfig(
                role="analyzer",
                name="analyzer",
                provider="groq",
                model="llama-3.1-8b",
                temperature=0.1,
                top_p=0.9,
            ),
            client=analyzer,
        ),
        mc.Stage(
            config=mc.StageConfig(
                role="imitator",
                name="imitator",
                provider="openai",
                model="gpt-4o-mini",
                temperature=0.75,
                top_p=0.95,
            ),
            client=imitator,
        ),
        mc.Stage(
            config=mc.StageConfig(
                role="post_editor",
                name="post_editor",
                provider="groq",
                model="llama-3.3-70b",
                temperature=0.4,
                top_p=0.9,
            ),
            client=post_editor,
        ),
        mc.Stage(
            config=mc.StageConfig(
                role="masker",
                name="masker",
                provider="groq",
                model="llama-3.1-8b",
                temperature=0.65,
                top_p=0.95,
            ),
            client=masker,
        ),
    ]

    chain = mc.MultiModelChain(
        stages=stages,
        cost_cap_usd=0.009,
        history_max_tokens=30_000,
    )
    log_path = tmp_path / "costs.jsonl"
    monkeypatch.setattr(mc, "COST_LOG_PATH", log_path)
    app.dependency_overrides[mc.get_chain] = lambda: chain

    client = TestClient(app)
    payload = {
        "history": "Hello, who are you?",
        "user_input": "Tell me a story about the Symbióza system.",
        "settings": {"target_words": 1000},
    }

    try:
        response = client.post("/multi_chain", json=payload)
    finally:
        app.dependency_overrides.pop(mc.get_chain, None)

    assert response.status_code == 200
    body = response.json()
    assert body["output"] == masker._response.text
    assert body["latency_s"] >= 0

    expected_cost = compute_expected_cost(
        {
            "analyzer": analyzer._response,
            "imitator": imitator._response,
            "post_editor": post_editor._response,
            "masker": masker._response,
        }
    )
    assert abs(body["cost_usd"] - expected_cost) < 1e-9

    assert log_path.exists()
    logged = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(logged) == 1
    line = json.loads(logged[0])
    assert line["total_cost_usd"] == body["cost_usd"]
    assert line["calls"]["masker"]["model"] == "llama-3.1-8b"
    assert line["conversation_id"] is None


def test_cost_projection_rejects_over_budget(monkeypatch):
    analyzer = StubClient(
        model_name="llama-3.1-8b",
        text="Summary",
        input_tokens=1000,
        output_tokens=1000,
    )
    imitator = StubClient(
        model_name="gpt-4o-mini",
        text="Draft",
        input_tokens=1000,
        output_tokens=2000,
    )
    post_editor = StubClient(
        model_name="llama-3.3-70b",
        text="Edited",
        input_tokens=2000,
        output_tokens=2000,
    )
    masker = StubClient(
        model_name="llama-3.1-8b",
        text="Final",
        input_tokens=2000,
        output_tokens=2000,
    )

    stages = [
        mc.Stage(
            config=mc.StageConfig(
                role="analyzer",
                name="analyzer",
                provider="groq",
                model="llama-3.1-8b",
                temperature=0.1,
                top_p=0.9,
            ),
            client=analyzer,
        ),
        mc.Stage(
            config=mc.StageConfig(
                role="imitator",
                name="imitator",
                provider="openai",
                model="gpt-4o-mini",
                temperature=0.75,
                top_p=0.95,
            ),
            client=imitator,
        ),
        mc.Stage(
            config=mc.StageConfig(
                role="post_editor",
                name="post_editor",
                provider="groq",
                model="llama-3.3-70b",
                temperature=0.4,
                top_p=0.9,
            ),
            client=post_editor,
        ),
        mc.Stage(
            config=mc.StageConfig(
                role="masker",
                name="masker",
                provider="groq",
                model="llama-3.1-8b",
                temperature=0.65,
                top_p=0.95,
            ),
            client=masker,
        ),
    ]

    chain = mc.MultiModelChain(
        stages=stages,
        cost_cap_usd=0.001,  # force tight budget
        history_max_tokens=30_000,
    )
    app.dependency_overrides[mc.get_chain] = lambda: chain
    client = TestClient(app)

    payload = {
        "history": " ".join(["hello"] * 1000),
        "user_input": "Give me an exhaustive analysis of the entire system with diagrams.",
        "settings": {"target_words": 2000},
    }

    try:
        response = client.post("/multi_chain", json=payload)
    finally:
        app.dependency_overrides.pop(mc.get_chain, None)

    assert response.status_code == 402
    assert "exceeds budget" in response.json()["detail"]


def test_pipeline_length_can_be_customized(tmp_path, monkeypatch):
    analyzer = StubClient(
        model_name="llama-3.1-8b",
        text="Summary bullets",
        input_tokens=600,
        output_tokens=250,
    )
    imitator = StubClient(
        model_name="gpt-4o-mini",
        text="Long draft body.",
        input_tokens=1400,
        output_tokens=900,
    )
    post_editor = StubClient(
        model_name="llama-3.3-70b",
        text="Polished draft body.",
        input_tokens=900,
        output_tokens=900,
    )

    stages = [
        mc.Stage(
            config=mc.StageConfig(
                role="analyzer",
                name="analyzer",
                provider="groq",
                model="llama-3.1-8b",
                temperature=0.1,
                top_p=0.9,
            ),
            client=analyzer,
        ),
        mc.Stage(
            config=mc.StageConfig(
                role="imitator",
                name="imitator",
                provider="openai",
                model="gpt-4o-mini",
                temperature=0.75,
                top_p=0.95,
            ),
            client=imitator,
        ),
        mc.Stage(
            config=mc.StageConfig(
                role="post_editor",
                name="post_editor",
                provider="groq",
                model="llama-3.3-70b",
                temperature=0.4,
                top_p=0.9,
            ),
            client=post_editor,
        ),
    ]

    chain = mc.MultiModelChain(
        stages=stages,
        cost_cap_usd=0.009,
        history_max_tokens=30_000,
    )
    log_path = tmp_path / "costs.jsonl"
    monkeypatch.setattr(mc, "COST_LOG_PATH", log_path)
    app.dependency_overrides[mc.get_chain] = lambda: chain

    client = TestClient(app)
    payload = {
        "history": "One two three four",
        "user_input": "Short request",
        "settings": {"target_words": 500},
    }

    try:
        response = client.post("/multi_chain", json=payload)
    finally:
        app.dependency_overrides.pop(mc.get_chain, None)

    assert response.status_code == 200
    body = response.json()
    assert body["output"] == post_editor._response.text
    assert log_path.exists()


def test_persona_prompt_injected_into_stage_messages(tmp_path, monkeypatch):
    persona_dir = tmp_path / "personas"
    persona_dir.mkdir()
    persona_text = "Always respond like a seasoned ship captain."
    (persona_dir / "12345_c.us.txt").write_text(persona_text, encoding="utf-8")
    monkeypatch.setenv("PERSONA_DIR", str(persona_dir))

    analyzer = StubClient(
        model_name="llama-3.1-8b",
        text="Summary",
        input_tokens=200,
        output_tokens=150,
    )
    imitator = StubClient(
        model_name="gpt-4o-mini",
        text="Draft",
        input_tokens=400,
        output_tokens=300,
    )
    post_editor = StubClient(
        model_name="llama-3.3-70b",
        text="Edited",
        input_tokens=300,
        output_tokens=250,
    )
    masker = StubClient(
        model_name="llama-3.1-8b",
        text="Final",
        input_tokens=250,
        output_tokens=200,
    )

    stages = [
        mc.Stage(
            config=mc.StageConfig(
                role="analyzer",
                name="analyzer",
                provider="groq",
                model="llama-3.1-8b",
                temperature=0.1,
                top_p=0.9,
            ),
            client=analyzer,
        ),
        mc.Stage(
            config=mc.StageConfig(
                role="imitator",
                name="imitator",
                provider="openai",
                model="gpt-4o-mini",
                temperature=0.75,
                top_p=0.95,
            ),
            client=imitator,
        ),
        mc.Stage(
            config=mc.StageConfig(
                role="post_editor",
                name="post_editor",
                provider="groq",
                model="llama-3.3-70b",
                temperature=0.4,
                top_p=0.9,
            ),
            client=post_editor,
        ),
        mc.Stage(
            config=mc.StageConfig(
                role="masker",
                name="masker",
                provider="groq",
                model="llama-3.1-8b",
                temperature=0.65,
                top_p=0.95,
            ),
            client=masker,
        ),
    ]

    chain = mc.MultiModelChain(
        stages=stages,
        cost_cap_usd=0.05,
        history_max_tokens=10_000,
    )
    app.dependency_overrides[mc.get_chain] = lambda: chain

    client = TestClient(app)
    payload = {
        "history": "Hi there.",
        "user_input": "Tell me a joke.",
        "settings": {"target_words": 250},
        "persona_id": "12345@c.us",
    }

    try:
        response = client.post("/multi_chain", json=payload)
    finally:
        app.dependency_overrides.pop(mc.get_chain, None)

    assert response.status_code == 200
    assert analyzer.last_messages is not None
    assert imitator.last_messages is not None
    assert post_editor.last_messages is not None
    assert masker.last_messages is not None

    def contains_persona(messages):
        return any(
            msg.get("role") == "system" and persona_text in msg.get("content", "")
            for msg in messages
        )

    assert contains_persona(analyzer.last_messages)
    assert contains_persona(imitator.last_messages)
    assert contains_persona(post_editor.last_messages)
    assert contains_persona(masker.last_messages)


def test_history_loaded_and_persisted(tmp_path, monkeypatch):
    history_dir = tmp_path / "history"
    history_dir.mkdir()
    existing = [
        {"role": "user", "text": "Hello there"},
        {"role": "assistant", "text": "Hi!"},
    ]
    history_file = history_dir / "12345_c.us.jsonl"
    history_file.write_text(
        "\n".join(json.dumps(entry) for entry in existing),
        encoding="utf-8",
    )
    monkeypatch.setenv("HISTORY_DIR", str(history_dir))

    analyzer = StubClient(
        model_name="llama-3.1-8b",
        text="Analyzer summary",
        input_tokens=200,
        output_tokens=150,
    )
    imitator = StubClient(
        model_name="gpt-4o-mini",
        text="Draft body",
        input_tokens=400,
        output_tokens=300,
    )
    post_editor = StubClient(
        model_name="llama-3.3-70b",
        text="Edited body",
        input_tokens=300,
        output_tokens=250,
    )
    masker = StubClient(
        model_name="llama-3.1-8b",
        text="Final body",
        input_tokens=250,
        output_tokens=200,
    )

    stages = [
        mc.Stage(
            config=mc.StageConfig(
                role="analyzer",
                name="analyzer",
                provider="groq",
                model="llama-3.1-8b",
                temperature=0.1,
                top_p=0.9,
            ),
            client=analyzer,
        ),
        mc.Stage(
            config=mc.StageConfig(
                role="imitator",
                name="imitator",
                provider="openai",
                model="gpt-4o-mini",
                temperature=0.75,
                top_p=0.95,
            ),
            client=imitator,
        ),
        mc.Stage(
            config=mc.StageConfig(
                role="post_editor",
                name="post_editor",
                provider="groq",
                model="llama-3.3-70b",
                temperature=0.4,
                top_p=0.9,
            ),
            client=post_editor,
        ),
        mc.Stage(
            config=mc.StageConfig(
                role="masker",
                name="masker",
                provider="groq",
                model="llama-3.1-8b",
                temperature=0.65,
                top_p=0.95,
            ),
            client=masker,
        ),
    ]

    chain = mc.MultiModelChain(
        stages=stages,
        cost_cap_usd=0.05,
        history_max_tokens=10_000,
    )
    app.dependency_overrides[mc.get_chain] = lambda: chain

    client = TestClient(app)
    payload = {
        "user_input": "How are you?",
        "settings": {"target_words": 250},
        "persona_id": "12345@c.us",
        "conversation_id": "12345@c.us",
    }

    try:
        response = client.post("/multi_chain", json=payload)
    finally:
        app.dependency_overrides.pop(mc.get_chain, None)

    assert response.status_code == 200
    assert analyzer.last_messages is not None
    # Loaded history should be present in analyzer prompt
    analyzer_history_texts = "\n".join(
        msg.get("content", "") for msg in analyzer.last_messages if msg.get("role") != "system"
    )
    assert "Hello there" in analyzer_history_texts

    lines = history_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == len(existing) + 2  # appended user + assistant turns
    appended_user = json.loads(lines[-2])
    appended_assistant = json.loads(lines[-1])
    assert appended_user["role"] == "user"
    assert appended_user["text"] == "How are you?"
    assert appended_assistant["role"] == "assistant"
    assert appended_assistant["text"] == masker._response.text
