import os
import typing as t

import openai
from _types import Message, Parameters, Role
from mistralai.client import MistralClient # type: ignore
from mistralai.models.chat_completion import ChatMessage # type: ignore
from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam

import torch
import tensorflow as tf
import tensorflow_hub as hub


def _chat_openai(
    client: OpenAI, messages: t.List[Message], parameters: Parameters
) -> Message:
    response = client.chat.completions.create(
        model=parameters.model,
        messages=t.cast(t.List[ChatCompletionMessageParam], messages),
        temperature=parameters.temperature,
        max_tokens=parameters.max_tokens,
        top_p=parameters.top_p,
    )

    response_message = response.choices[0].message
    return Message(
        role=Role(response_message.role), content=str(response_message.content)
    )


def chat_openai(messages: t.List[Message], parameters: Parameters) -> Message:
    return _chat_openai(OpenAI(), messages, parameters)


def chat_mistral(
    messages: t.List[Message], parameters: Parameters
) -> Message:
    client = MistralClient()
    messages = [
        ChatMessage(role=message.role, content=message.content) for message in messages
    ]

    response = client.chat(
        model=parameters.model,
        messages=messages,
        temperature=parameters.temperature,
        max_tokens=parameters.max_tokens,
        top_p=parameters.top_p,
    )
    response_message = response.choices[-1].message
    return Message(role=response_message.role, content=response_message.content)

def embed_mistral(contents: t.List[str]) -> t.List[t.List[float]]:
    client = MistralClient()
    response = client.embeddings('mistral-embed', contents)
    return [d.embedding for d in response.data]

def chat_together(messages: t.List[Message], parameters: Parameters) -> Message:
    client = openai.OpenAI(
        api_key=os.environ["TOGETHER_API_KEY"],
        base_url="https://api.together.xyz/v1",
    )

    return _chat_openai(client, messages, parameters)

def use_model():
    module_url = "https://tfhub.dev/google/universal-sentence-encoder/4"
    embed = hub.load(module_url)

    def calculate_similarity(sentences1, sentences2):
        sts_encode1 = tf.nn.l2_normalize(embed(sentences1), axis=1)
        sts_encode2 = tf.nn.l2_normalize(embed(sentences2), axis=1)
        cosine_similarities = tf.reduce_sum(tf.multiply(sts_encode1, sts_encode2), axis=1)
        clip_cosine_similarities = tf.clip_by_value(cosine_similarities, -1.0, 1.0)
        sim_scores = 1.0 - tf.acos(clip_cosine_similarities)
        sim_scores = torch.from_numpy(sim_scores.numpy())

        return sim_scores

    return calculate_similarity
