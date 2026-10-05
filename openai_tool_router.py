import json

from openai import OpenAI

from commerce_api import escalate_to_human, get_listing_count, get_order


TOOL_MODEL = "gpt-4o-mini"

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_listing_count",
            "description": "Get the live listing count from an ecommerce platform such as Etsy or Shopify.",
            "parameters": {
                "type": "object",
                "properties": {
                    "platform": {
                        "type": "string",
                        "description": "The commerce platform to query.",
                        "enum": ["etsy", "shopify"],
                    }
                },
                "required": ["platform"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_order",
            "description": "Look up an order status, carrier, tracking number, and estimated delivery date.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "The customer's order number, without a leading #.",
                    },
                    "platform": {
                        "type": "string",
                        "description": "The commerce platform to query.",
                        "enum": ["etsy", "shopify"],
                    },
                },
                "required": ["order_id", "platform"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "escalate_to_human",
            "description": "Escalate high-risk, angry, refund-dispute, chargeback, or human-review requests.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "Short reason for escalation.",
                    },
                    "platform": {
                        "type": "string",
                        "description": "The commerce platform context.",
                        "enum": ["etsy", "shopify"],
                    },
                },
                "required": ["reason", "platform"],
            },
        },
    },
]


def _tool_system_prompt(platform: str) -> str:
    return (
        "You are an intent router for an ecommerce support agent. "
        "Use tools for exact operational facts: listing counts, order status, tracking, "
        "or human escalation. Do not answer shipping, return policy, FAQ, or product "
        "recommendation questions directly; leave those without a tool call so the app "
        f"can route them to RAG. The current platform is {platform}."
    )


def _run_tool(name: str, arguments: dict, platform: str) -> dict:
    arguments.setdefault("platform", platform)

    if name == "get_listing_count":
        return get_listing_count(platform=arguments["platform"])
    if name == "get_order":
        result = get_order(order_id=arguments["order_id"], platform=arguments["platform"])
        return result or {"platform": arguments["platform"], "order_id": arguments["order_id"], "found": False}
    if name == "escalate_to_human":
        return escalate_to_human(reason=arguments["reason"], platform=arguments["platform"])

    return {"error": f"Unknown tool: {name}"}


def _infer_intent_from_tool(name: str) -> str:
    if name == "get_listing_count":
        return "PRODUCT_COUNT"
    if name == "get_order":
        return "ORDER_STATUS"
    if name == "escalate_to_human":
        return "ESCALATE"
    return "TOOL"


def _format_tool_answer(client: OpenAI, messages: list, tool_result: dict) -> str:
    final_response = client.chat.completions.create(
        model=TOOL_MODEL,
        messages=[
            *messages,
            {
                "role": "system",
                "content": (
                    "Format the tool result into a concise, friendly customer-support answer. "
                    "Do not invent details beyond the tool result."
                ),
            },
        ],
        temperature=0,
    )
    content = final_response.choices[0].message.content
    if content:
        return content

    return json.dumps(tool_result, ensure_ascii=False)


def answer_message_with_tools(message: str, platform: str = "etsy") -> dict:
    client = OpenAI()
    messages = [
        {"role": "system", "content": _tool_system_prompt(platform)},
        {"role": "user", "content": message},
    ]
    response = client.chat.completions.create(
        model=TOOL_MODEL,
        messages=messages,
        tools=TOOLS,
        tool_choice="auto",
        temperature=0,
    )

    assistant_message = response.choices[0].message
    tool_calls = assistant_message.tool_calls or []

    if not tool_calls:
        from rag_service import answer_with_rag

        rag_result = answer_with_rag(message)
        return {
            "intent": "RAG",
            "answer": rag_result["answer"],
            "tool_result": None,
            "sources": rag_result["sources"],
        }

    tool_call = tool_calls[0]
    tool_name = tool_call.function.name
    arguments = json.loads(tool_call.function.arguments or "{}")
    tool_result = _run_tool(tool_name, arguments, platform=platform)
    assistant_tool_message = {
        "role": "assistant",
        "content": assistant_message.content,
        "tool_calls": [call.model_dump(exclude_none=True) for call in tool_calls],
    }

    tool_messages = [
        *messages,
        assistant_tool_message,
        {
            "role": "tool",
            "tool_call_id": tool_call.id,
            "name": tool_name,
            "content": json.dumps(tool_result, ensure_ascii=False),
        },
    ]

    return {
        "intent": _infer_intent_from_tool(tool_name),
        "answer": _format_tool_answer(client, tool_messages, tool_result),
        "tool_result": tool_result,
        "sources": [],
    }
