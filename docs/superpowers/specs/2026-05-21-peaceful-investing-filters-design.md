# Spec: Peaceful Investing Filter and Telegram Bot Fixes

## 1. Goal Description
The objective of this work is to:
1. Fix a runtime error (`NameError: name 'requests' is not defined`) in the Telegram listener bot (`listener/main.py`) which currently prevents fetching the active portfolio holdings for analysis.
2. Refine and clarify the "Peaceful" value investing filter prompt and skill criteria to allow high-quality, dual-use technology companies (e.g., NVIDIA, Microsoft, Google) even if they have general defense department contracts, while strictly excluding actual weapons manufacturers (e.g., Lockheed Martin, Raytheon, Northrop Grumman) and companies that design specialized software/systems specifically for espionage, intelligence, or tactical combat operations (e.g., Palantir).

## 2. Proposed Changes

### Component 1: Telegram Bot Listener (`listener/main.py`)
* **[MODIFY] [main.py](file:///Users/joaosantos/stock-tracker/listener/main.py)**
  * Add `import requests` in the import declarations.
  * Update the prompt template in `handle_message` to refine the "Peaceful" mandate. We will instruct the LLM to clearly distinguish between dual-use general-purpose technology and specialized combat/espionage weaponry or systems.

### Component 2: Buffett Strategic Analyst Skill (`agent/skills/buffett_analyst/SKILL.md`)
* **[MODIFY] [SKILL.md](file:///Users/joaosantos/stock-tracker/agent/skills/buffett_analyst/SKILL.md)**
  * Update the **Core Mandates** (specifically **"Peaceful" Investing**) to align with the refined definition. Make sure the instructions clearly separate dual-use hardware/software (like general-use microchips/GPUs, search, or productivity systems) from dedicated combat/killing products and surveillance/espionage systems.

---

## 3. Detailed Specifications

### A. Telegram Prompt Refinement (`listener/main.py`)
Currently, the prompt in `listener/main.py` is:
```python
        f"3. **STRICT MANDATE:** Verify if the company is 'Peaceful'. Strictly exclude companies that create 'killing products directly' or provide mission-critical combat technology (e.g., Lockheed Martin, Palantir, Raytheon). If the stock is NOT peaceful, your Action must be 'SELL' or 'AVOID' with a clear warning.\n"
```
We will replace it with:
```python
        f"3. **STRICT MANDATE:** Verify if the company is 'Peaceful'.\n"
        f"   - STRICTLY EXCLUDE: Companies that directly manufacture weapon systems, munitions, firearms, tactical hardware, military explosives, nuclear weapons, or warships (e.g., Lockheed Martin, Raytheon, Northrop Grumman), AND companies producing specialized software or systems designed specifically for intelligence, espionage, surveillance, warfare, and tactical combat operations (e.g., Palantir).\n"
        f"   - EXPLICITLY ALLOW: Companies producing general-purpose or dual-use technologies (e.g., standard consumer electronics, microchips, GPUs, enterprise software, general search/cloud infrastructure, commercial aviation) even if they have partnerships, research relationships, or general contracts with defense departments (e.g., NVIDIA, Microsoft, Google), unless their direct products are weapons or dedicated combat/espionage systems. If the stock is NOT peaceful according to these exact guidelines, your Action must be 'SELL' or 'AVOID' with a clear warning.\n"
```

### B. Core Skill Refinement (`agent/skills/buffett_analyst/SKILL.md`)
Currently, the mandate in `agent/skills/buffett_analyst/SKILL.md` is:
```markdown
1.  **"Peaceful" Investing:** Strictly exclude all "War-oriented" stocks. This includes companies that create "killing products directly" or provide mission-critical technology for combat (e.g., Lockheed Martin, Palantir, Northrop Grumman, Raytheon). We do not profit from products designed for conflict or destruction.
```
We will replace it with:
```markdown
1.  **"Peaceful" Investing:** Strictly exclude all "War-oriented" stocks.
    *   **Strictly Exclude:** Companies that directly manufacture weapon systems, munitions, firearms, tactical hardware, military explosives, nuclear weapons, or warships (e.g., Lockheed Martin, Raytheon, Northrop Grumman), and companies producing specialized software or systems designed specifically for intelligence, espionage, surveillance, warfare, and tactical combat operations (e.g., Palantir). We do not profit from products designed for conflict or destruction.
    *   **Explicitly Allow:** Companies producing general-purpose or dual-use technologies (e.g., standard consumer electronics, microchips, GPUs, enterprise software, general search/cloud infrastructure, commercial aviation) even if they have partnerships, research relationships, or general contracts with defense departments (e.g., NVIDIA, Microsoft, Google), unless their direct products are weapons or dedicated combat/espionage systems.
```

---

## 4. Verification Plan

### Automated Tests
* We can run `python -m py_compile listener/main.py` to ensure that it has no syntax errors after adding imports.

### Manual / LLM-Based Verification
We will verify that the prompt behaves exactly as expected for critical test cases:
1. **NVIDIA (`NVDA`)**: Should pass the "Peaceful" filter because GPUs are dual-use, general-purpose chips.
2. **Microsoft (`MSFT`)**: Should pass because enterprise/cloud software is dual-use.
3. **Google (`GOOGL`)**: Should pass because general search/cloud infrastructure is dual-use.
4. **Palantir (`PLTR`)**: Should fail/be excluded because they create specialized software/platforms for intelligence, espionage, and warfare.
5. **Lockheed Martin (`LMT`)**: Should fail/be excluded because they manufacture weapons and tactical combat machinery.
