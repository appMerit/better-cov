"""Test scenario generators for each fault cluster."""

from typing import Any

from merit import Case


def generate_contract_cases() -> list[Case]:
    """Generate 30 cases for contract/JSON schema testing."""
    cases = []

    # Base scenarios: different trip types
    base_scenarios = [
        {"prompt": "Plan a 3-day trip to Paris", "city": "Paris", "days": 3},
        {"prompt": "Create a 5-day Tokyo itinerary", "city": "Tokyo", "days": 5},
        {"prompt": "I want to visit Rome for a week", "city": "Rome", "days": 7},
        {"prompt": "Plan a weekend in Barcelona", "city": "Barcelona", "days": 2},
        {"prompt": "Create a 10-day tour of London", "city": "London", "days": 10},
        {"prompt": "Help me plan 4 days in Berlin", "city": "Berlin", "days": 4},
        {"prompt": "I need a 6-day Sydney vacation plan", "city": "Sydney", "days": 6},
        {"prompt": "Plan a 3-day New York City trip", "city": "New York", "days": 3},
        {"prompt": "Create an 8-day Paris vacation", "city": "Paris", "days": 8},
        {"prompt": "I want to spend 5 days in Tokyo exploring", "city": "Tokyo", "days": 5},
    ]

    # Generate 3 variations per base scenario
    for idx, scenario in enumerate(base_scenarios):
        # Variation 1: Basic request
        cases.append(
            Case(
                tags={"contract"},
                metadata={"scenario_id": f"contract_{idx}_basic", "variation": "basic"},
                sut_input_values={"prompt": scenario["prompt"]},
                references={
                    "required_fields": ["destination", "dates", "flights", "hotels", "activities"],
                    "expected_city": scenario["city"],
                },
            )
        )

        # Variation 2: With budget
        cases.append(
            Case(
                tags={"contract"},
                metadata={"scenario_id": f"contract_{idx}_budget", "variation": "budget"},
                sut_input_values={
                    "prompt": f"{scenario['prompt']} with a budget of $2000"
                },
                references={
                    "required_fields": ["destination", "dates", "flights", "hotels", "activities", "budget"],
                    "expected_city": scenario["city"],
                },
            )
        )

        # Variation 3: With specific dates
        cases.append(
            Case(
                tags={"contract"},
                metadata={"scenario_id": f"contract_{idx}_dates", "variation": "dates"},
                sut_input_values={
                    "prompt": f"{scenario['prompt']} from June 1 to June {scenario['days']}"
                },
                references={
                    "required_fields": ["destination", "dates", "flights", "hotels", "activities"],
                    "expected_city": scenario["city"],
                    "date_specified": True,
                },
            )
        )

    return cases


def generate_prompt_cases() -> list[Case]:
    """Generate 30 cases for prompt assembly/role mixing testing."""
    cases = []

    base_scenarios = [
        {"prompt": "Output only valid JSON", "constraint": "json_only"},
        {"prompt": "Create itinerary in JSON format", "constraint": "format"},
        {"prompt": "Respond with structured data", "constraint": "structure"},
        {"prompt": "Give me a JSON response", "constraint": "json"},
        {"prompt": "Format output as JSON", "constraint": "format_json"},
        {"prompt": "Return valid JSON", "constraint": "valid_json"},
        {"prompt": "Structured JSON output please", "constraint": "structured"},
        {"prompt": "JSON format required", "constraint": "required_json"},
        {"prompt": "Output in JSON only", "constraint": "json_exclusive"},
        {"prompt": "Strict JSON response", "constraint": "strict"},
    ]

    for idx, scenario in enumerate(base_scenarios):
        # Variation 1: Direct constraint
        cases.append(
            Case(
                tags={"prompting"},
                metadata={"scenario_id": f"prompt_{idx}_direct", "variation": "direct"},
                sut_input_values={
                    "prompt": f"{scenario['prompt']}: Plan a trip to Paris"
                },
                references={
                    "constraint_type": scenario["constraint"],
                    "must_be_json": True,
                },
            )
        )

        # Variation 2: With system instruction emphasis
        cases.append(
            Case(
                tags={"prompting"},
                metadata={"scenario_id": f"prompt_{idx}_emphasis", "variation": "emphasis"},
                sut_input_values={
                    "prompt": f"IMPORTANT: {scenario['prompt']}. Plan Rome trip."
                },
                references={
                    "constraint_type": scenario["constraint"],
                    "must_be_json": True,
                    "has_emphasis": True,
                },
            )
        )

        # Variation 3: With policy reference
        cases.append(
            Case(
                tags={"prompting"},
                metadata={"scenario_id": f"prompt_{idx}_policy", "variation": "policy"},
                sut_input_values={
                    "prompt": f"According to policy, {scenario['prompt']}. Tokyo itinerary."
                },
                references={
                    "constraint_type": scenario["constraint"],
                    "must_be_json": True,
                    "mentions_policy": True,
                },
            )
        )

    return cases


def generate_retrieval_cases() -> list[Case]:
    """Generate 30 cases for retrieval relevance testing."""
    cases = []

    base_scenarios = [
        {
            "prompt": "What are the visa requirements for France?",
            "required_fact": "90 days without a visa",
            "kb_id": "visa_france",
        },
        {
            "prompt": "Tell me about tipping customs in Japan",
            "required_fact": "not customary",
            "kb_id": "tipping_japan",
        },
        {
            "prompt": "What's the weather like in Paris during summer?",
            "required_fact": "20-25°C",
            "kb_id": "weather_paris",
        },
        {
            "prompt": "How much should I budget for Tokyo?",
            "required_fact": "$120-180/day",
            "kb_id": "budget_tokyo",
        },
        {
            "prompt": "Do I need a visa for Japan as a US citizen?",
            "required_fact": "90 days without a visa",
            "kb_id": "visa_japan",
        },
        {
            "prompt": "What about tipping in French restaurants?",
            "required_fact": "5-10%",
            "kb_id": "tipping_france",
        },
        {
            "prompt": "Tokyo weather in summer?",
            "required_fact": "25-35°C",
            "kb_id": "weather_tokyo",
        },
        {
            "prompt": "Daily budget for Paris trip?",
            "required_fact": "$150-200/day",
            "kb_id": "budget_paris",
        },
        {
            "prompt": "France visa rules for Americans?",
            "required_fact": "90 days",
            "kb_id": "visa_france",
        },
        {
            "prompt": "Is tipping expected in Japan?",
            "required_fact": "not customary",
            "kb_id": "tipping_japan",
        },
    ]

    for idx, scenario in enumerate(base_scenarios):
        # Variation 1: Direct question
        cases.append(
            Case(
                tags={"retrieval"},
                metadata={"scenario_id": f"retrieval_{idx}_direct", "variation": "direct"},
                sut_input_values={"prompt": scenario["prompt"]},
                references={
                    "required_fact": scenario["required_fact"],
                    "kb_doc_id": scenario["kb_id"],
                },
            )
        )

        # Variation 2: As part of planning
        cases.append(
            Case(
                tags={"retrieval"},
                metadata={"scenario_id": f"retrieval_{idx}_planning", "variation": "planning"},
                sut_input_values={
                    "prompt": f"I'm planning a trip. {scenario['prompt']}"
                },
                references={
                    "required_fact": scenario["required_fact"],
                    "kb_doc_id": scenario["kb_id"],
                    "context": "planning",
                },
            )
        )

        # Variation 3: Multiple questions
        other_idx = (idx + 1) % len(base_scenarios)
        cases.append(
            Case(
                tags={"retrieval"},
                metadata={"scenario_id": f"retrieval_{idx}_multiple", "variation": "multiple"},
                sut_input_values={
                    "prompt": f"{scenario['prompt']} Also, {base_scenarios[other_idx]['prompt']}"
                },
                references={
                    "required_facts": [
                        scenario["required_fact"],
                        base_scenarios[other_idx]["required_fact"],
                    ],
                    "kb_doc_ids": [scenario["kb_id"], base_scenarios[other_idx]["kb_id"]],
                },
            )
        )

    return cases


def generate_grounding_cases() -> list[Case]:
    """Generate 30 cases for grounding enforcement testing."""
    cases = []

    # Questions that require KB facts
    unanswerable_without_kb = [
        "What are the visa requirements for France?",
        "Tell me about tipping in Japan",
        "What's the local custom for tipping in Paris?",
        "Do US citizens need a visa for Tokyo?",
        "What's the typical weather in Paris?",
        "How much should I budget per day in Tokyo?",
        "Are there any cultural customs I should know for Japan?",
        "What's the transportation system like in Paris?",
        "What's the climate in Tokyo during summer?",
        "Tell me about visa requirements for Japan",
    ]

    for idx, question in enumerate(unanswerable_without_kb):
        # Variation 1: Direct question
        cases.append(
            Case(
                tags={"grounding"},
                metadata={"scenario_id": f"grounding_{idx}_direct", "variation": "direct"},
                sut_input_values={"prompt": question},
                references={
                    "context_required": True,
                    "policy": "must_use_kb",
                },
            )
        )

        # Variation 2: With explicit instruction
        cases.append(
            Case(
                tags={"grounding"},
                metadata={"scenario_id": f"grounding_{idx}_explicit", "variation": "explicit"},
                sut_input_values={
                    "prompt": f"Based only on provided information: {question}"
                },
                references={
                    "context_required": True,
                    "policy": "must_use_kb",
                    "explicit_instruction": True,
                },
            )
        )

        # Variation 3: In trip planning context
        cases.append(
            Case(
                tags={"grounding"},
                metadata={"scenario_id": f"grounding_{idx}_context", "variation": "context"},
                sut_input_values={
                    "prompt": f"I'm planning a trip. {question}"
                },
                references={
                    "context_required": True,
                    "policy": "must_use_kb",
                    "planning_context": True,
                },
            )
        )

    return cases


def generate_routing_cases() -> list[Case]:
    """Generate 30 cases for tool routing testing."""
    cases = []

    tool_scenarios = [
        {"prompt": "What's the weather in Paris?", "expected_tool": "get_weather", "city": "Paris"},
        {"prompt": "Check Tokyo weather", "expected_tool": "get_weather", "city": "Tokyo"},
        {"prompt": "Find hotels in Rome", "expected_tool": "search_hotels", "city": "Rome"},
        {"prompt": "Search for accommodation in London", "expected_tool": "search_hotels", "city": "London"},
        {"prompt": "Look for flights to Barcelona", "expected_tool": "search_flights", "city": "Barcelona"},
        {"prompt": "Find me a flight to Berlin", "expected_tool": "search_flights", "city": "Berlin"},
        {"prompt": "Weather forecast for Sydney", "expected_tool": "get_weather", "city": "Sydney"},
        {"prompt": "Hotel options in Paris", "expected_tool": "search_hotels", "city": "Paris"},
        {"prompt": "Available flights to Tokyo", "expected_tool": "search_flights", "city": "Tokyo"},
        {"prompt": "Current weather in Rome", "expected_tool": "get_weather", "city": "Rome"},
    ]

    for idx, scenario in enumerate(tool_scenarios):
        # Variation 1: Direct request
        cases.append(
            Case(
                tags={"routing"},
                metadata={"scenario_id": f"routing_{idx}_direct", "variation": "direct"},
                sut_input_values={"prompt": scenario["prompt"]},
                references={
                    "expected_tool": scenario["expected_tool"],
                    "city": scenario["city"],
                },
            )
        )

        # Variation 2: As part of itinerary
        cases.append(
            Case(
                tags={"routing"},
                metadata={"scenario_id": f"routing_{idx}_itinerary", "variation": "itinerary"},
                sut_input_values={
                    "prompt": f"Plan a trip to {scenario['city']}. {scenario['prompt']}"
                },
                references={
                    "expected_tool": scenario["expected_tool"],
                    "city": scenario["city"],
                    "context": "itinerary",
                },
            )
        )

        # Variation 3: Urgent/immediate
        cases.append(
            Case(
                tags={"routing"},
                metadata={"scenario_id": f"routing_{idx}_urgent", "variation": "urgent"},
                sut_input_values={
                    "prompt": f"I need to know now: {scenario['prompt']}"
                },
                references={
                    "expected_tool": scenario["expected_tool"],
                    "city": scenario["city"],
                    "urgent": True,
                },
            )
        )

    return cases


def generate_tool_args_cases() -> list[Case]:
    """Generate 30 cases for tool argument validation testing."""
    cases = []

    arg_scenarios = [
        {"tool": "weather", "location": "Paris", "date": "2024-06-01"},
        {"tool": "weather", "location": "Tokyo", "date": "2024-07-15"},
        {"tool": "hotel", "location": "Rome", "check_in": "2024-06-01", "check_out": "2024-06-05"},
        {"tool": "hotel", "location": "London", "check_in": "2024-08-10", "check_out": "2024-08-15"},
        {"tool": "flight", "from": "New York", "to": "Paris", "date": "2024-06-01"},
        {"tool": "flight", "from": "Los Angeles", "to": "Tokyo", "date": "2024-07-01"},
        {"tool": "weather", "location": "Barcelona", "date": "2024-09-01"},
        {"tool": "hotel", "location": "Berlin", "check_in": "2024-10-01", "check_out": "2024-10-05"},
        {"tool": "flight", "from": "Chicago", "to": "London", "date": "2024-11-01"},
        {"tool": "weather", "location": "Sydney", "date": "2024-12-01"},
    ]

    for idx, scenario in enumerate(arg_scenarios):
        if scenario["tool"] == "weather":
            # Variation 1: Correct args
            cases.append(
                Case(
                    tags={"tool_args"},
                    metadata={"scenario_id": f"tool_args_{idx}_correct", "variation": "correct"},
                    sut_input_values={
                        "prompt": f"What's the weather in {scenario['location']} on {scenario['date']}?"
                    },
                    references={
                        "expected_tool": "get_weather",
                        "expected_args": {"location": scenario["location"], "date": scenario["date"]},
                    },
                )
            )

            # Variation 2: Date format variant
            cases.append(
                Case(
                    tags={"tool_args"},
                    metadata={"scenario_id": f"tool_args_{idx}_date_format", "variation": "date_format"},
                    sut_input_values={
                        "prompt": f"Weather for {scenario['location']} on June 1, 2024?"
                    },
                    references={
                        "expected_tool": "get_weather",
                        "location": scenario["location"],
                        "date_format_flexible": True,
                    },
                )
            )

            # Variation 3: Location spelling
            cases.append(
                Case(
                    tags={"tool_args"},
                    metadata={"scenario_id": f"tool_args_{idx}_location", "variation": "location"},
                    sut_input_values={
                        "prompt": f"Check weather in {scenario['location']}"
                    },
                    references={
                        "expected_tool": "get_weather",
                        "location": scenario["location"],
                    },
                )
            )
        
        elif scenario["tool"] == "hotel":
            # Variation 1: Correct args
            cases.append(
                Case(
                    tags={"tool_args"},
                    metadata={"scenario_id": f"tool_args_{idx}_correct", "variation": "correct"},
                    sut_input_values={
                        "prompt": f"Find hotels in {scenario['location']} from {scenario['check_in']} to {scenario['check_out']}"
                    },
                    references={
                        "expected_tool": "search_hotels",
                        "expected_args": {
                            "location": scenario["location"],
                            "check_in": scenario["check_in"],
                            "check_out": scenario["check_out"],
                        },
                    },
                )
            )

            # Variation 2: Natural language dates
            cases.append(
                Case(
                    tags={"tool_args"},
                    metadata={"scenario_id": f"tool_args_{idx}_natural_dates", "variation": "natural_dates"},
                    sut_input_values={
                        "prompt": f"Search for accommodation in {scenario['location']} for 5 nights starting June 1"
                    },
                    references={
                        "expected_tool": "search_hotels",
                        "location": scenario["location"],
                        "date_format_flexible": True,
                    },
                )
            )

            # Variation 3: Location only
            cases.append(
                Case(
                    tags={"tool_args"},
                    metadata={"scenario_id": f"tool_args_{idx}_location_only", "variation": "location_only"},
                    sut_input_values={
                        "prompt": f"Show me hotels in {scenario['location']}"
                    },
                    references={
                        "expected_tool": "search_hotels",
                        "location": scenario["location"],
                    },
                )
            )
        
        elif scenario["tool"] == "flight":
            # Variation 1: Correct args
            cases.append(
                Case(
                    tags={"tool_args"},
                    metadata={"scenario_id": f"tool_args_{idx}_correct", "variation": "correct"},
                    sut_input_values={
                        "prompt": f"Find flights from {scenario['from']} to {scenario['to']} on {scenario['date']}"
                    },
                    references={
                        "expected_tool": "search_flights",
                        "expected_args": {
                            "origin": scenario["from"],
                            "destination": scenario["to"],
                            "date": scenario["date"],
                        },
                    },
                )
            )

            # Variation 2: Natural language
            cases.append(
                Case(
                    tags={"tool_args"},
                    metadata={"scenario_id": f"tool_args_{idx}_natural", "variation": "natural"},
                    sut_input_values={
                        "prompt": f"I need to fly from {scenario['from']} to {scenario['to']} in June"
                    },
                    references={
                        "expected_tool": "search_flights",
                        "origin": scenario["from"],
                        "destination": scenario["to"],
                        "date_format_flexible": True,
                    },
                )
            )

            # Variation 3: Route only
            cases.append(
                Case(
                    tags={"tool_args"},
                    metadata={"scenario_id": f"tool_args_{idx}_route", "variation": "route"},
                    sut_input_values={
                        "prompt": f"Search flights {scenario['from']} to {scenario['to']}"
                    },
                    references={
                        "expected_tool": "search_flights",
                        "origin": scenario["from"],
                        "destination": scenario["to"],
                    },
                )
            )

    return cases


def generate_memory_cases() -> list[Case]:
    """Generate 30 cases for state/memory testing."""
    cases = []

    # Two-turn scenarios
    preference_scenarios = [
        {"turn1": "I prefer window seats", "turn2": "Book a flight to Paris", "pref_type": "seat"},
        {"turn1": "My budget is $2000", "turn2": "Plan a Tokyo trip", "pref_type": "budget"},
        {"turn1": "I like luxury hotels", "turn2": "Find accommodation in Rome", "pref_type": "hotel"},
        {"turn1": "I prefer morning flights", "turn2": "Search flights to London", "pref_type": "flight_time"},
        {"turn1": "Budget traveler here", "turn2": "Plan Barcelona trip", "pref_type": "budget_style"},
        {"turn1": "I want aisle seats", "turn2": "Book Berlin flight", "pref_type": "seat"},
        {"turn1": "Maximum $3000 budget", "turn2": "Create Sydney itinerary", "pref_type": "budget"},
        {"turn1": "I prefer boutique hotels", "turn2": "Find Paris hotels", "pref_type": "hotel"},
        {"turn1": "I like evening flights", "turn2": "Search Tokyo flights", "pref_type": "flight_time"},
        {"turn1": "Mid-range traveler", "turn2": "Plan Rome trip", "pref_type": "budget_style"},
    ]

    for idx, scenario in enumerate(preference_scenarios):
        # Variation 1: Simple two-turn
        cases.append(
            Case(
                tags={"memory"},
                metadata={"scenario_id": f"memory_{idx}_two_turn", "variation": "two_turn"},
                sut_input_values={
                    "prompt": scenario["turn2"],
                    "session_id": f"memory_session_{idx}_a",
                    "previous_turn": scenario["turn1"],
                },
                references={
                    "preference_type": scenario["pref_type"],
                    "must_remember": scenario["turn1"],
                },
            )
        )

        # Variation 2: With explicit reference
        cases.append(
            Case(
                tags={"memory"},
                metadata={"scenario_id": f"memory_{idx}_explicit", "variation": "explicit"},
                sut_input_values={
                    "prompt": f"Based on what I said earlier, {scenario['turn2'].lower()}",
                    "session_id": f"memory_session_{idx}_b",
                    "previous_turn": scenario["turn1"],
                },
                references={
                    "preference_type": scenario["pref_type"],
                    "must_remember": scenario["turn1"],
                    "explicit_reference": True,
                },
            )
        )

        # Variation 3: Multiple turns
        cases.append(
            Case(
                tags={"memory"},
                metadata={"scenario_id": f"memory_{idx}_multiple", "variation": "multiple"},
                sut_input_values={
                    "prompt": scenario["turn2"],
                    "session_id": f"memory_session_{idx}_c",
                    "previous_turns": [scenario["turn1"], "Tell me more about options"],
                },
                references={
                    "preference_type": scenario["pref_type"],
                    "must_remember": scenario["turn1"],
                    "multi_turn": True,
                },
            )
        )

    return cases


def generate_control_flow_cases() -> list[Case]:
    """Generate 30 cases for control flow/termination testing."""
    cases = []

    multi_step_scenarios = [
        {"prompt": "Check weather then find hotels in Paris", "min_steps": 2},
        {"prompt": "Search flights and hotels for Tokyo", "min_steps": 2},
        {"prompt": "Get weather, find hotels, and search flights for Rome", "min_steps": 3},
        {"prompt": "Plan complete trip: weather, hotels, flights to London", "min_steps": 3},
        {"prompt": "Multi-step: check Barcelona weather then find accommodation", "min_steps": 2},
        {"prompt": "First weather, then hotels for Berlin", "min_steps": 2},
        {"prompt": "Complex trip: weather, hotels, flights for Sydney", "min_steps": 3},
        {"prompt": "Check Paris weather and find flights", "min_steps": 2},
        {"prompt": "Tokyo trip: weather then hotels", "min_steps": 2},
        {"prompt": "Three-step plan: weather, hotels, flights for Rome", "min_steps": 3},
    ]

    for idx, scenario in enumerate(multi_step_scenarios):
        # Variation 1: Sequential steps
        cases.append(
            Case(
                tags={"control_flow"},
                metadata={"scenario_id": f"control_{idx}_sequential", "variation": "sequential"},
                sut_input_values={"prompt": scenario["prompt"]},
                references={
                    "min_steps": scenario["min_steps"],
                    "termination_reason_valid": ["max_steps_reached", "complete"],
                },
            )
        )

        # Variation 2: With step limit
        cases.append(
            Case(
                tags={"control_flow"},
                metadata={"scenario_id": f"control_{idx}_limited", "variation": "limited"},
                sut_input_values={
                    "prompt": scenario["prompt"],
                    "max_steps": scenario["min_steps"] + 1,
                },
                references={
                    "min_steps": scenario["min_steps"],
                    "max_steps": scenario["min_steps"] + 1,
                },
            )
        )

        # Variation 3: Complex dependencies
        cases.append(
            Case(
                tags={"control_flow"},
                metadata={"scenario_id": f"control_{idx}_complex", "variation": "complex"},
                sut_input_values={
                    "prompt": f"Detailed {scenario['prompt']} with all options"
                },
                references={
                    "min_steps": scenario["min_steps"],
                    "complex_dependencies": True,
                },
            )
        )

    return cases


def generate_determinism_cases() -> list[Case]:
    """Generate 30 cases for determinism/config drift testing."""
    cases = []

    # Prompts where format matters
    format_sensitive = [
        "Output travel plan in JSON",
        "Create structured itinerary",
        "Return only JSON format",
        "Give me JSON response",
        "Format: strict JSON",
        "JSON output required",
        "Structured data only",
        "Valid JSON response",
        "Output in JSON format",
        "JSON itinerary please",
    ]

    for idx, prompt in enumerate(format_sensitive):
        # Variation 1: Single run
        cases.append(
            Case(
                tags={"determinism"},
                metadata={"scenario_id": f"determ_{idx}_single", "variation": "single"},
                sut_input_values={"prompt": f"{prompt}: Paris trip"},
                references={
                    "must_be_json": True,
                    "format_sensitive": True,
                },
            )
        )

        # Variation 2: Repeated run (for checking consistency)
        cases.append(
            Case(
                tags={"determinism"},
                metadata={"scenario_id": f"determ_{idx}_repeat", "variation": "repeat"},
                sut_input_values={
                    "prompt": f"{prompt}: Tokyo trip",
                    "check_consistency": True,
                },
                references={
                    "must_be_json": True,
                    "format_sensitive": True,
                    "repeat_count": 3,
                },
            )
        )

        # Variation 3: With temperature check
        cases.append(
            Case(
                tags={"determinism"},
                metadata={"scenario_id": f"determ_{idx}_temp", "variation": "temperature"},
                sut_input_values={
                    "prompt": f"{prompt}: Rome itinerary",
                    "check_temperature": True,
                },
                references={
                    "must_be_json": True,
                    "expected_temperature": 0.0,
                },
            )
        )

    return cases


def generate_postprocess_cases() -> list[Case]:
    """Generate 30 cases for postprocessing/mapping testing."""
    cases = []

    # Different itinerary structures
    itinerary_types = [
        {"prompt": "Simple Paris trip", "complexity": "simple"},
        {"prompt": "Complex Tokyo itinerary with activities", "complexity": "complex"},
        {"prompt": "Rome vacation with multiple hotels", "complexity": "multi_hotel"},
        {"prompt": "London trip with various flights", "complexity": "multi_flight"},
        {"prompt": "Barcelona itinerary with daily activities", "complexity": "detailed"},
        {"prompt": "Berlin trip with budget breakdown", "complexity": "budgeted"},
        {"prompt": "Sydney vacation with notes", "complexity": "annotated"},
        {"prompt": "Paris weekend getaway", "complexity": "short"},
        {"prompt": "Tokyo extended stay", "complexity": "long"},
        {"prompt": "Multi-city Rome-Paris trip", "complexity": "multi_city"},
    ]

    for idx, scenario in enumerate(itinerary_types):
        # Variation 1: Standard fields
        cases.append(
            Case(
                tags={"postprocess"},
                metadata={"scenario_id": f"postproc_{idx}_standard", "variation": "standard"},
                sut_input_values={"prompt": scenario["prompt"]},
                references={
                    "required_schema_fields": ["destination", "dates", "flights", "hotels", "activities"],
                    "complexity": scenario["complexity"],
                },
            )
        )

        # Variation 2: All optional fields
        cases.append(
            Case(
                tags={"postprocess"},
                metadata={"scenario_id": f"postproc_{idx}_full", "variation": "full"},
                sut_input_values={
                    "prompt": f"{scenario['prompt']} with complete details"
                },
                references={
                    "required_schema_fields": ["destination", "dates", "flights", "hotels", "activities", "budget", "notes"],
                    "complexity": scenario["complexity"],
                },
            )
        )

        # Variation 3: Minimal fields
        cases.append(
            Case(
                tags={"postprocess"},
                metadata={"scenario_id": f"postproc_{idx}_minimal", "variation": "minimal"},
                sut_input_values={
                    "prompt": f"Quick {scenario['prompt']}"
                },
                references={
                    "required_schema_fields": ["destination", "dates"],
                    "complexity": "minimal",
                },
            )
        )

    return cases
