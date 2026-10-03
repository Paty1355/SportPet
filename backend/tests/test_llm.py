import asyncio
from types import SimpleNamespace

from app.agents.llm import AzureLLM, detect_image_type
from app.memory.embeddings import AzureEmbeddingFunction


class FakeChatCompletions:
    def __init__(self):
        self.calls = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))])


def fake_async_client():
    completions = FakeChatCompletions()
    return SimpleNamespace(chat=SimpleNamespace(completions=completions)), completions


def test_text_uses_chat_deployment():
    client, completions = fake_async_client()
    llm = AzureLLM(client, chat_deployment="chat", vision_deployment="vision")

    reply = asyncio.run(llm.complete("system", [{"role": "user", "content": "hej"}]))

    assert reply == "ok"
    call = completions.calls[0]
    assert call["model"] == "chat"
    assert call["messages"] == [{"role": "system", "content": "system"}, {"role": "user", "content": "hej"}]


def test_image_uses_vision_deployment_and_data_url():
    client, completions = fake_async_client()
    llm = AzureLLM(client, chat_deployment="chat", vision_deployment="vision")

    asyncio.run(llm.complete("system", [{"role": "user", "content": "co to?"}], image=b"\x89PNG data"))

    call = completions.calls[0]
    assert call["model"] == "vision"
    text, image = call["messages"][-1]["content"]
    assert text == {"type": "text", "text": "co to?"}
    assert image["image_url"]["url"].startswith("data:image/png;base64,")


def test_vision_falls_back_to_chat_deployment():
    client, completions = fake_async_client()
    asyncio.run(AzureLLM(client, "chat").complete("s", [{"role": "user", "content": "x"}], image=b"\xff\xd8"))
    assert completions.calls[0]["model"] == "chat"


def test_detect_image_type():
    assert detect_image_type(b"\x89PNG....") == "image/png"
    assert detect_image_type(b"RIFF\x00\x00\x00\x00WEBPVP8") == "image/webp"
    assert detect_image_type(b"\xff\xd8\xff") == "image/jpeg"


def test_embedding_function_keeps_input_order():
    data = [SimpleNamespace(index=1, embedding=[0.0, 1.0]), SimpleNamespace(index=0, embedding=[1.0, 0.0])]
    client = SimpleNamespace(embeddings=SimpleNamespace(create=lambda **_: SimpleNamespace(data=data)))

    embeddings = AzureEmbeddingFunction(client, "emb")(["a", "b"])

    assert [list(e) for e in embeddings] == [[1.0, 0.0], [0.0, 1.0]]
    assert AzureEmbeddingFunction(client, "emb").get_config() == {"deployment": "emb"}
