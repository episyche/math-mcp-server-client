import asyncio
import argparse
import json
import os
import sys
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv()


def get_server_script_path() -> str:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(current_dir, "google_ads_mcp_server.py")


async def call_tool(session: ClientSession, name: str, **arguments) -> str:
    result = await session.call_tool(name=name, arguments=arguments)
    try:
        content_items = getattr(result, "content", []) or []
        if content_items:
            first = content_items[0]
            text = getattr(first, "text", None)
            if text is not None:
                return text
        return str(result)
    except Exception:
        return str(result)


def normalize_operation(op: str | None) -> str | None:
    if op is None:
        return None
    mapping = {
        # Create Customer variations
        "create_customer": "create_customer",
        "create_account": "create_customer",
        "new_customer": "create_customer",
        "add_customer": "create_customer",
        "register_customer": "create_customer",
        "setup_customer": "create_customer",
        "new_account": "create_customer",
        "add_account": "create_customer",
        "register_account": "create_customer",
        "setup_account": "create_customer",
        "create_client": "create_customer",
        "new_client": "create_customer",
        "add_client": "create_customer",
        
        # Add Campaign variations
        "add_campaign": "add_campaign",
        "create_campaign": "add_campaign",
        "new_campaign": "add_campaign",
        "setup_campaign": "add_campaign",
        "start_campaign": "add_campaign",
        "launch_campaign": "add_campaign",
        "make_campaign": "add_campaign",
        "build_campaign": "add_campaign",
        "initiate_campaign": "add_campaign",
        "begin_campaign": "add_campaign",
        "establish_campaign": "add_campaign",
        "set_campaign": "add_campaign",
        "campaign_create": "add_campaign",
        "campaign_add": "add_campaign",
        "campaign_new": "add_campaign",
        "campaign_setup": "add_campaign",
        "campaign_start": "add_campaign",
        "campaign_launch": "add_campaign",
        "campaign_make": "add_campaign",
        "campaign_build": "add_campaign",
        
        # Remove Campaign variations
        "remove_campaign": "remove_campaign",
        "delete_campaign": "remove_campaign",
        "stop_campaign": "remove_campaign",
        "end_campaign": "remove_campaign",
        "cancel_campaign": "remove_campaign",
        "pause_campaign": "remove_campaign",
        
        # Add Ad Group variations
        "add_ad_group": "add_ad_group",
        "create_ad_group": "add_ad_group",
        "new_ad_group": "add_ad_group",
        "add_adgroup": "add_ad_group",
        "create_adgroup": "add_ad_group",
        "new_adgroup": "add_ad_group",
        "setup_ad_group": "add_ad_group",
        
        # Update Campaign variations
        "update_campaign": "update_campaign",
        "modify_campaign": "update_campaign",
        "edit_campaign": "update_campaign",
        "change_campaign": "update_campaign",
        "alter_campaign": "update_campaign",
        
        # Get Campaign variations
        "get_campaign": "get_campaign",
        "fetch_campaign": "get_campaign",
        "find_campaign": "get_campaign",
        "show_campaign": "get_campaign",
        "view_campaign": "get_campaign",
        "campaign_status": "get_campaign",
    }
    return mapping.get(op.lower(), op.lower())


def ensure_openai_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set. Export OPENAI_API_KEY.")
    try:
        from openai import OpenAI  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "OpenAI SDK not installed. Install 'openai' or run 'pip install -r requirements.txt'."
        ) from exc
    return OpenAI()


def llm_route_question(question: str, model: str | None = None) -> tuple[str | None, float | None, float | None, float | None]:
    client = ensure_openai_client()
    model_name = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    system_prompt = (
        "Extract Google Ads API action and parameters from user input."
        
        "ACTIONS & REQUIRED PARAMS:"
        "- add_campaign: create new campaign by ID (param: customer_id)"
        "- remove_campaign: delete campaign by ID (param: customer_id, param2: campaign_id)"
        "- add_ad_group: create ad group in campaign (param: ad_group_name, param2: campaign_id)"
        "- update_campaign: modify existing campaign (param: campaign_id, param2: field_to_update, param3: new_value)"
        "- create_customer: create new customer account (param: country)"
        "- get_campaign: fetch campaign details (param: customer_id)"
        
        "Return valid JSON format: {'action': 'action_name', 'param': 'parameter_value', 'param2': 'parameter_value_2', 'param3': 'parameter_value_3'}"
        "If unclear: {'action': 'unknown', 'param': ''}"
        
        "Examples:"
        "{'action': 'add_campaign', 'param': '123456789'}"
        "{'action': 'remove_campaign', 'param': '123456789', 'param2': 'campaign_123456789'}"
        "{'action': 'add_ad_group', 'param': 'Electronics Ad Group', 'param2': 'campaign_123456789'}"
        "{'action': 'update_campaign', 'param': 'campaign_123456789', 'param2': 'budget', 'param3': '1500'}"
        "{'action': 'create_customer', 'param': 'India'}"
    )

    user_prompt = f"User prompt: {question}"

    try:
        # Using Chat Completions with JSON response
        from openai import OpenAI  # type: ignore
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or "{}"
        data = json.loads(content)
        print("the data", data)
        op = normalize_operation(data.get("action"))
        a = data.get("param") if data.get("param") is not None else None
        b = data.get("param2") if data.get("param2") is not None else None
        c = data.get("param3") if data.get("param3") is not None else None
        
        return op, a, b, c
    except Exception as err:
        print("the err", err)
        return None, None, None, None


async def main() -> None:
    parser = argparse.ArgumentParser(description="CLI tool for Google Ads API operations to handle campaign management, ad group creation, and customer operations.")
    parser.add_argument("--question", "-q", nargs="+", help="Natural language question, e.g. 'Create a campaign for the customer id'", required=False)
    parser.add_argument("--model", "-m", default=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), help="LLM model name for agent mode")
    args = parser.parse_args()

    server_script = get_server_script_path()
    if not os.path.exists(server_script):
        raise FileNotFoundError(f"Server script not found at: {server_script}")

    server_params = StdioServerParameters(
        command=sys.executable,
        args=[server_script],
        env=None,
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            if not args.question:
                print("Please provide a question with --question/-q, e.g. --question 'Create a campaign for the customer id'")
                sys.exit(1)

            qtext = " ".join(args.question)
            operation, a, b, c = llm_route_question(qtext, model=args.model)
            print("the operation", operation, a, b, c)

            if operation and a is not None and b is None and c is None:
                # Single parameter operations
                result_text = await call_tool(session, operation, a=a)
                print(result_text)
            elif operation and a is not None and b is not None and c is None:
                # Two parameter operations
                result_text = await call_tool(session, operation, a=a, b=b)
                print(result_text)
            elif operation and a is not None and b is not None and c is not None:
                # Three parameter operations (like update_campaign)
                result_text = await call_tool(session, operation, a=a, b=b, c=c)
                print(result_text)
            else:
                print("LLM could not parse the question. Please rephrase and try again.")


if __name__ == "__main__":
    asyncio.run(main())
