import itertools
import math
import re
from datetime import date, datetime, timedelta
from itertools import combinations

import requests
import streamlit as st

LOTOFACIL_MIN = 1
LOTOFACIL_MAX = 25
ALL_NUMBERS = list(range(LOTOFACIL_MIN, LOTOFACIL_MAX + 1))
API_URL = "https://loteriascaixa-api.herokuapp.com/api/lotofacil/latest"
API_CONTEST_URL = "https://loteriascaixa-api.herokuapp.com/api/lotofacil/{contest}"

# Tabela vigente da aposta da Lotofácil (CAIXA). Uma aposta com mais de 15
# dezenas equivale a várias apostas simples e por isso tem preço próprio.
BET_PRICES = {15: 3.50, 16: 56.00, 17: 476.00, 18: 2856.00, 19: 13566.00, 20: 54264.00}

MODERN_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Outfit:wght@600;700;800&display=swap');

    /* Fontes Globais e Estilo Base */
    html, body, .stApp, p, h1, h2, h3, h4, h5, h6, label, input, textarea, select {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Preservar ícones nativos do Streamlit e do Expander */
    [data-testid="stIconMaterial"],
    [class*="MaterialSymbols"],
    [class*="material-icons"],
    div[data-testid="stExpander"] summary *,
    div[data-testid="stExpander"] i {
        font-family: 'Material Symbols Outlined', 'Material Icons', inherit !important;
    }

    /* Ocultar elementos nativos desnecessários */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Estilização limpa para Expanders */
    div[data-testid="stExpander"] {
        border-radius: 14px !important;
        border: 1px solid #e2e8f0 !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03) !important;
        background: #ffffff !important;
        margin-bottom: 1rem !important;
        overflow: hidden !important;
    }
    div[data-testid="stExpander"] summary {
        font-weight: 700 !important;
        color: #1e1b4b !important;
        font-size: 1rem !important;
    }

    /* Hero Header Moderno */
    .hero-container {
        background: linear-gradient(135deg, #1e1b4b 0%, #312e81 40%, #4c1d95 100%);
        border-radius: 20px;
        padding: 2.2rem 2rem;
        color: #ffffff;
        box-shadow: 0 15px 35px -5px rgba(76, 29, 149, 0.35);
        margin-bottom: 1.8rem;
        position: relative;
        overflow: hidden;
        border: 1px solid rgba(255, 255, 255, 0.15);
    }
    .hero-container::before {
        content: "";
        position: absolute;
        top: -50%;
        right: -10%;
        width: 300px;
        height: 300px;
        background: radial-gradient(circle, rgba(168, 85, 247, 0.3) 0%, rgba(0,0,0,0) 70%);
        border-radius: 50%;
        pointer-events: none;
    }
    .hero-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(255, 255, 255, 0.15);
        backdrop-filter: blur(10px);
        padding: 4px 14px;
        border-radius: 20px;
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #e9d5ff;
        border: 1px solid rgba(255, 255, 255, 0.2);
        margin-bottom: 0.75rem;
    }
    .hero-title {
        font-family: 'Outfit', sans-serif;
        font-size: 2.4rem;
        font-weight: 800;
        margin: 0;
        line-height: 1.15;
        background: linear-gradient(120deg, #ffffff 30%, #f3e8ff 70%, #d8b4fe 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .hero-subtitle {
        color: #c084fc;
        font-size: 0.98rem;
        font-weight: 500;
        margin-top: 0.5rem;
        margin-bottom: 0;
    }

    /* Cartela de Dezenas Interativa (Volante) */
    .ticket-card {
        background: #ffffff;
        border-radius: 20px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 10px 30px -5px rgba(0, 0, 0, 0.06);
        overflow: hidden;
        margin: 0 auto;
        transition: all 0.3s ease;
    }
    .ticket-header {
        background: linear-gradient(135deg, #831843 0%, #be185d 50%, #9d174d 100%);
        padding: 1rem 1.25rem;
        text-align: center;
        color: #ffffff;
    }
    .ticket-header-title {
        font-family: 'Outfit', sans-serif;
        font-size: 1.35rem;
        font-weight: 800;
        letter-spacing: 0.12em;
        margin: 0;
        text-transform: uppercase;
    }
    .ticket-header-sub {
        font-size: 0.76rem;
        font-weight: 600;
        color: #fbcfe8;
        margin-top: 4px;
        letter-spacing: 0.04em;
    }
    .ticket-body {
        padding: 1.2rem;
        background: #fafafa;
    }
    .ticket-legend {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 12px;
        padding: 0.75rem;
        background: #ffffff;
        border-top: 1px solid #f1f5f9;
        font-size: 0.78rem;
        font-weight: 600;
        color: #475569;
        flex-wrap: wrap;
    }
    .legend-item {
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }
    .legend-dot {
        width: 10px;
        height: 10px;
        border-radius: 50%;
    }
    .dot-fixed { background: #be185d; box-shadow: 0 0 6px rgba(190, 24, 93, 0.5); }
    .dot-variable { background: #2563eb; box-shadow: 0 0 6px rgba(37, 99, 235, 0.5); }
    .dot-extra { background: #10b981; box-shadow: 0 0 6px rgba(16, 185, 129, 0.5); }
    .dot-empty { background: #e2e8f0; }

    /* Estilização dos Botões de Dezenas (Pílulas) - usando st-key do Streamlit */
    [class*="st-key-btn_ticket_"] button,
    [class*="st-key-btn_sel_"] button,
    [class*="st-key-btn_extra_"] button {
        border-radius: 12px !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-size: 0.95rem !important;
        font-weight: 700 !important;
        height: 2.6rem !important;
        min-height: 2.6rem !important;
        padding: 0 !important;
        width: 100% !important;
        transition: all 0.18s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }

    /* Estado Desmarcado (3º Clique / Neutro - BRANCO) */
    [class*="st-key-btn_ticket_"][class*="_empty"] button,
    [class*="st-key-btn_sel_"][class*="_empty"] button,
    [class*="st-key-btn_extra_"][class*="_empty"] button {
        background: #ffffff !important;
        background-color: #ffffff !important;
        border: 1.5px solid #cbd5e1 !important;
        color: #334155 !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02) !important;
    }
    [class*="st-key-btn_ticket_"][class*="_empty"] button:hover,
    [class*="st-key-btn_sel_"][class*="_empty"] button:hover,
    [class*="st-key-btn_extra_"][class*="_empty"] button:hover {
        background: #f1f5f9 !important;
        background-color: #f1f5f9 !important;
        border-color: #94a3b8 !important;
        color: #0f172a !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 8px rgba(0,0,0,0.06) !important;
    }

    /* Estado Dezena Fixa (1º CLIQUE - VINHO / MAGENTA) */
    [class*="st-key-btn_ticket_"][class*="_fixed"] button {
        background: linear-gradient(135deg, #831843 0%, #be185d 100%) !important;
        background-color: #be185d !important;
        border: 1.5px solid #831843 !important;
        color: #ffffff !important;
        box-shadow: 0 4px 14px rgba(190, 24, 93, 0.45) !important;
        transform: translateY(-1px) !important;
    }
    [class*="st-key-btn_ticket_"][class*="_fixed"] button:hover {
        background: linear-gradient(135deg, #9d174d 0%, #db2777 100%) !important;
        background-color: #db2777 !important;
        box-shadow: 0 6px 18px rgba(190, 24, 93, 0.55) !important;
    }

    /* Estado Dezena Variável (2º CLIQUE - AZUL ELÉTRICO) */
    [class*="st-key-btn_ticket_"][class*="_variable"] button {
        background: linear-gradient(135deg, #1e40af 0%, #2563eb 100%) !important;
        background-color: #2563eb !important;
        border: 1.5px solid #1e40af !important;
        color: #ffffff !important;
        box-shadow: 0 4px 14px rgba(37, 99, 235, 0.45) !important;
        transform: translateY(-1px) !important;
    }
    [class*="st-key-btn_ticket_"][class*="_variable"] button:hover {
        background: linear-gradient(135deg, #1d4ed8 0%, #3b82f6 100%) !important;
        background-color: #3b82f6 !important;
        box-shadow: 0 6px 18px rgba(37, 99, 235, 0.55) !important;
    }

    /* Estado Dezena Extra / Selecionada (VERDE ESMERALDA) */
    [class*="st-key-btn_ticket_"][class*="_extra"] button,
    [class*="st-key-btn_sel_"][class*="_selected"] button,
    [class*="st-key-btn_extra_"][class*="_selected"] button {
        background: linear-gradient(135deg, #047857 0%, #10b981 100%) !important;
        background-color: #10b981 !important;
        border: 1.5px solid #047857 !important;
        color: #ffffff !important;
        box-shadow: 0 4px 14px rgba(16, 185, 129, 0.45) !important;
        transform: translateY(-1px) !important;
    }
    [class*="st-key-btn_ticket_"][class*="_extra"] button:hover,
    [class*="st-key-btn_sel_"][class*="_selected"] button:hover,
    [class*="st-key-btn_extra_"][class*="_selected"] button:hover {
        background: linear-gradient(135deg, #059669 0%, #34d399 100%) !important;
        background-color: #059669 !important;
        box-shadow: 0 6px 18px rgba(16, 185, 129, 0.55) !important;
    }

    /* Estilização dos Containers & Envoltórios de Borda */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 16px !important;
        border: 1px solid #e2e8f0 !important;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.03) !important;
        background: #ffffff !important;
    }

    /* Estilização de Botões de Ação Principais (Excluindo Volantes) */
    div.stButton:not([class*="st-key-ticket_"]) button[kind="primary"] {
        background: linear-gradient(135deg, #4c1d95 0%, #6d28d9 100%) !important;
        background-color: #6d28d9 !important;
        border: none !important;
        border-radius: 12px !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        font-size: 1rem !important;
        padding: 0.6rem 1.2rem !important;
        box-shadow: 0 4px 14px rgba(109, 40, 217, 0.35) !important;
        transition: all 0.2s ease !important;
    }
    div.stButton:not([class*="st-key-ticket_"]) button[kind="primary"]:hover {
        background: linear-gradient(135deg, #5b21b6 0%, #7c3aed 100%) !important;
        background-color: #7c3aed !important;
        box-shadow: 0 6px 20px rgba(109, 40, 217, 0.5) !important;
        transform: translateY(-2px) !important;
    }

    /* Download Buttons */
    .stDownloadButton button {
        border-radius: 12px !important;
        font-weight: 700 !important;
        border: 1.5px solid #cbd5e1 !important;
        transition: all 0.2s ease !important;
    }
    .stDownloadButton button:hover {
        border-color: #6d28d9 !important;
        color: #6d28d9 !important;
        background: #f5f3ff !important;
        transform: translateY(-1px) !important;
    }

    /* Navegação Segmentada (Radio Buttons Horizontal) */
    div[data-testid="stRadio"] > div[role="radiogroup"] {
        background: #f1f5f9;
        padding: 5px;
        border-radius: 16px;
        gap: 6px;
        border: 1px solid #e2e8f0;
    }
    div[data-testid="stRadio"] > div[role="radiogroup"] label {
        background: transparent;
        padding: 8px 18px;
        border-radius: 12px;
        font-weight: 700;
        font-size: 0.92rem;
        color: #64748b;
        transition: all 0.2s ease;
        border: none !important;
        cursor: pointer;
    }
    div[data-testid="stRadio"] > div[role="radiogroup"] label[data-checked="true"] {
        background: #ffffff !important;
        color: #4c1d95 !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08) !important;
    }

    /* Métricas Reestilizadas */
    div[data-testid="stMetric"] {
        background: #ffffff;
        padding: 1.1rem 1.3rem;
        border-radius: 16px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
    }
    div[data-testid="stMetricLabel"] {
        font-size: 0.85rem !important;
        font-weight: 700 !important;
        color: #64748b !important;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }
    div[data-testid="stMetricValue"] {
        font-family: 'Outfit', sans-serif !important;
        font-size: 1.8rem !important;
        font-weight: 800 !important;
        color: #1e1b4b !important;
    }

    /* Responsividade para Celulares e Tablets */
    @media (max-width: 768px) {
        .hero-container {
            padding: 1.5rem 1.2rem;
            margin-bottom: 1.2rem;
        }
        .hero-title {
            font-size: 1.75rem;
        }
        .hero-subtitle {
            font-size: 0.88rem;
        }
        .ticket-body {
            padding: 0.6rem;
        }
        .ticket-header-title {
            font-size: 1.15rem;
        }
        [class*="st-key-ticket_"] button {
            height: 2.3rem !important;
            min-height: 2.3rem !important;
            font-size: 0.88rem !important;
            border-radius: 8px !important;
        }
        div[data-testid="stRadio"] > div[role="radiogroup"] {
            flex-direction: column;
        }
    }
</style>
"""


def parse_numbers(text: str) -> list[int]:
    return [int(n) for n in re.findall(r"\d+", text)]


def format_game(numbers: list[int]) -> str:
    return ",".join(f"{n:02d}" for n in numbers)


def parse_game_line(line: str) -> list[int] | None:
    line = line.strip()
    if not line:
        return None
    numbers = parse_numbers(line)
    if not numbers:
        return None
    return sorted(set(numbers))


def init_selection(key: str) -> None:
    if key not in st.session_state:
        st.session_state[key] = []
    elif isinstance(st.session_state[key], set):
        st.session_state[key] = sorted(st.session_state[key])


def selection_priority(key: str) -> int | None:
    return st.session_state.get("selection_priorities", {}).get(key)


def toggle_number(key: str, num: int) -> None:
    init_selection(key)
    if num in st.session_state[key]:
        st.session_state[key].remove(num)
        if not st.session_state[key]:
            st.session_state.get("selection_priorities", {}).pop(key, None)
    else:
        if not st.session_state[key]:
            priorities = st.session_state.setdefault("selection_priorities", {})
            priorities[key] = st.session_state.get("selection_priority_counter", 0)
            st.session_state["selection_priority_counter"] = priorities[key] + 1
        st.session_state[key].append(num)


def get_selection(key: str) -> list[int]:
    init_selection(key)
    return st.session_state[key].copy()


def unique_in_selection_order(numbers: list[int]) -> list[int]:
    """Remove duplicatas preservando a ordem em que as dezenas foram selecionadas."""
    return list(dict.fromkeys(numbers))


def has_consecutive_sequence(game: list[int], max_sequence: int) -> bool:
    if max_sequence <= 1:
        return True
    game_sorted = sorted(game)
    consecutive = 1
    for i in range(1, len(game_sorted)):
        if game_sorted[i] == game_sorted[i - 1] + 1:
            consecutive += 1
            if consecutive >= max_sequence:
                return True
        else:
            consecutive = 1
    return False


def filter_games_by_sequence(games: list[list[int]], max_sequence: int, fixed: list[int] = None) -> list[list[int]]:
    if max_sequence == 0:
        return games
    
    fixed_set = set(fixed) if fixed else set()
    filtered_games = []
    for game in games:
        variables_only = [num for num in game if num not in fixed_set]
        if not has_consecutive_sequence(variables_only, max_sequence):
            filtered_games.append(game)
    return filtered_games


def render_number_selector(key: str, label: str) -> list[int]:
    init_selection(key)
    st.markdown(f"**{label}**")

    side_left, ticket_column, side_right = st.columns([0.2, 3.6, 0.2])
    with ticket_column:
        st.markdown(
            """
            <div class="ticket-card">
                <div class="ticket-header">
                    <div class="ticket-header-title">LOTOFÁCIL</div>
                    <div class="ticket-header-sub">SELEÇÃO DE DEZENAS</div>
                </div>
                <div class="ticket-body">
            """,
            unsafe_allow_html=True,
        )

        for row in range(5):
            cols = st.columns(5, gap="small")
            for col_idx in range(5):
                num = col_idx * 5 + row + 1
                is_selected = num in st.session_state[key]
                state_suffix = "selected" if is_selected else "empty"
                with cols[col_idx]:
                    if st.button(
                        f"{num:02d}",
                        key=f"btn_sel_{key}_{num}_{state_suffix}",
                        use_container_width=True,
                    ):
                        toggle_number(key, num)
                        st.rerun()

        st.markdown(
            """
                </div>
                <div class="ticket-legend">
                    <span class="legend-item"><span class="legend-dot dot-extra"></span> Selecionada</span>
                    <span class="legend-item"><span class="legend-dot dot-empty"></span> Livre</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    selected = get_selection(key)
    if selected:
        st.caption(f"Selecionadas ({len(selected)}): {', '.join(f'{n:02d}' for n in selected)}")
    else:
        st.caption("Nenhuma dezena selecionada.")
    return selected


def ticket_state(key: str) -> tuple[list[int], list[int], dict[int, int]]:
    """Retorna fixas, variáveis e a ordem global dos cliques ativos."""
    states = st.session_state.setdefault(f"{key}_states", {})
    order = st.session_state.setdefault(f"{key}_order", {})
    fixed = [number for number in ALL_NUMBERS if states.get(number) == 1]
    variables = [number for number in ALL_NUMBERS if states.get(number) == 2]
    fixed.sort(key=lambda number: order[number])
    variables.sort(key=lambda number: order[number])
    return fixed, variables, order


def cycle_ticket_number(key: str, number: int) -> None:
    """Ciclo: desmarcada -> fixa -> variável -> desmarcada."""
    states = st.session_state.setdefault(f"{key}_states", {})
    order = st.session_state.setdefault(f"{key}_order", {})
    current = states.get(number, 0)
    if current == 2:
        states.pop(number, None)
        order.pop(number, None)
        return

    states[number] = current + 1
    order[number] = st.session_state.get("ticket_click_counter", 0)
    st.session_state["ticket_click_counter"] = order[number] + 1


def render_unified_ticket(key: str) -> tuple[list[int], list[int], dict[int, int]]:
    fixed, variables, order = ticket_state(key)
    side_left, ticket_column, side_right = st.columns([0.1, 3.8, 0.1])
    with ticket_column:
        st.markdown(
            """
            <div class="ticket-card">
                <div class="ticket-header">
                    <div class="ticket-header-title">VOLANTE LOTOFÁCIL</div>
                    <div class="ticket-header-sub">1º CLIQUE: FIXA · 2º CLIQUE: VARIÁVEL · 3º CLIQUE: DESMARCA</div>
                </div>
                <div class="ticket-body">
            """,
            unsafe_allow_html=True,
        )

        states = st.session_state[f"{key}_states"]
        for row in range(5):
            columns = st.columns(5, gap="small")
            for column_index in range(5):
                number = column_index * 5 + row + 1
                state = states.get(number, 0)
                state_suffix = ("empty", "fixed", "variable")[state]
                with columns[column_index]:
                    if st.button(
                        f"{number:02d}",
                        key=f"btn_ticket_{key}_{number}_{state_suffix}",
                        use_container_width=True,
                    ):
                        cycle_ticket_number(key, number)
                        st.rerun()

        st.markdown(
            """
                </div>
                <div class="ticket-legend">
                    <span class="legend-item"><span class="legend-dot dot-fixed"></span> <b>Fixa</b> (Vinho)</span>
                    <span class="legend-item"><span class="legend-dot dot-variable"></span> <b>Variável</b> (Azul)</span>
                    <span class="legend-item"><span class="legend-dot dot-empty"></span> Não selecionada</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    fixed, variables, order = ticket_state(key)
    st.caption(
        f"**Fixas ({len(fixed)})**: {', '.join(f'{n:02d}' for n in fixed) or 'nenhuma'}  |  "
        f"**Variáveis ({len(variables)})**: {', '.join(f'{n:02d}' for n in variables) or 'nenhuma'}"
    )
    return fixed, variables, order


def generate_ticket_combinations(
    fixed: list[int], variables: list[int], pick: int, order: dict[int, int]
) -> list[list[int]]:
    if pick < 0 or pick > len(variables):
        raise ValueError("A quantidade de dezenas variáveis por jogo é inválida.")
    return [
        sorted(fixed + list(variable_pick), key=lambda number: order[number])
        for variable_pick in combinations(variables, pick)
    ]


def render_extra_ticket(key: str) -> list[int]:
    """Cartela de seleção simples para as dezenas extras do Arquivo C."""
    init_selection(key)
    side_left, ticket_column, side_right = st.columns([0.1, 3.8, 0.1])
    with ticket_column:
        st.markdown(
            """
            <div class="ticket-card">
                <div class="ticket-header" style="background: linear-gradient(135deg, #047857 0%, #10b981 100%);">
                    <div class="ticket-header-title">VARIÁVEIS EXTRAS</div>
                    <div class="ticket-header-sub">SELEÇÃO COMPLEMENTAR PARA O ARQUIVO C</div>
                </div>
                <div class="ticket-body">
            """,
            unsafe_allow_html=True,
        )

        for row in range(5):
            columns = st.columns(5, gap="small")
            for column_index in range(5):
                number = column_index * 5 + row + 1
                selected = number in st.session_state[key]
                state_suffix = "selected" if selected else "empty"
                with columns[column_index]:
                    if st.button(
                        f"{number:02d}",
                        key=f"btn_extra_{key}_{number}_{state_suffix}",
                        use_container_width=True,
                    ):
                        toggle_number(key, number)
                        st.rerun()

        st.markdown(
            """
                </div>
                <div class="ticket-legend">
                    <span class="legend-item"><span class="legend-dot dot-extra"></span> Extra Selecionada</span>
                    <span class="legend-item"><span class="legend-dot dot-empty"></span> Livre</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    return get_selection(key)


def variable_core(game: list[int], fixed_numbers: list[int]) -> list[int]:
    fixed_set = set(fixed_numbers)
    return [number for number in game if number not in fixed_set]


def generate_file_c(
    games_a: list[list[int]],
    games_b: list[list[int]],
    fixed_a: list[int],
    fixed_b: list[int],
    extra_variables: list[int],
    target_size: int,
) -> list[list[int]]:
    """Combina os miolos de A e B com as variáveis extras, sem repetir dezenas."""
    if target_size not in BET_PRICES:
        raise ValueError("O Arquivo C deve ter de 15 a 20 dezenas por aposta.")

    generated = []
    seen = set()
    for game_a in games_a:
        core_a = variable_core(game_a, fixed_a)
        for game_b in games_b:
            core_b = variable_core(game_b, fixed_b)
            base = unique_in_selection_order(core_a + core_b)
            needed = target_size - len(base)
            if needed < 0:
                continue
            candidates = [number for number in extra_variables if number not in base]
            extra_picks = (
                combinations(candidates, needed)
                if needed <= len(candidates)
                else [tuple(candidates)]
            )
            for extra_pick in extra_picks:
                game = base + list(extra_pick)
                signature = tuple(game)
                if signature not in seen:
                    seen.add(signature)
                    generated.append(game)
    return generated


def open_generated_games_in_checker() -> None:
    """Callback executado antes dos widgets, permitindo trocar de aba com segurança."""
    generated_text = st.session_state.get("generated_games_txt")
    if not generated_text:
        st.session_state["checker_navigation_error"] = True
        return
    st.session_state["checker_games_text"] = generated_text
    st.session_state["checker_input_method"] = "Colar texto"
    st.session_state["active_section"] = "Conferidor"
    st.session_state["auto_check_pending"] = True


def open_intersection_c_in_checker() -> None:
    games = st.session_state.get("intersection_c_games", [])
    if not games:
        st.session_state["checker_navigation_error"] = True
        return
    st.session_state["checker_games_text"] = "\n".join(format_game(game) for game in games)
    st.session_state["checker_input_method"] = "Colar texto"
    st.session_state["active_section"] = "Conferidor"
    st.session_state["auto_check_pending"] = True


def make_open_intersection_ab_in_checker(letter: str):
    """Fábrica de callbacks para abrir Arquivo A ou B no conferidor."""
    def _callback() -> None:
        key = f"intersection_{letter.lower()}_games"
        games = st.session_state.get(key, [])
        if not games:
            st.session_state["checker_navigation_error"] = True
            return
        st.session_state["checker_games_text"] = "\n".join(format_game(game) for game in games)
        st.session_state["checker_input_method"] = "Colar texto"
        st.session_state["active_section"] = "Conferidor"
        st.session_state["auto_check_pending"] = True
    return _callback


def generate_combinations(
    fixed: list[int], groups: list[tuple[list[int], int]], fixed_first: bool = True
) -> list[list[int]]:
    fixed_unique = unique_in_selection_order(fixed)

    if not groups:
        return [fixed_unique] if fixed_unique else []

    group_combos = []
    for numbers, pick in groups:
        unique = unique_in_selection_order(numbers)
        if pick < 0:
            raise ValueError("A quantidade a escolher não pode ser negativa.")
        if pick > len(unique):
            raise ValueError(
                f"Grupo [{', '.join(f'{n:02d}' for n in unique)}]: "
                f"escolher {pick} dezenas, mas só há {len(unique)} disponíveis."
            )
        group_combos.append(list(combinations(unique, pick)))

    games = []
    for picks in itertools.product(*group_combos):
        variable_numbers = [n for group in picks for n in group]
        numbers = fixed_unique + variable_numbers if fixed_first else variable_numbers + fixed_unique
        game = unique_in_selection_order(numbers)
        games.append(game)
    return games


def expected_combination_count(groups: list[tuple[list[int], int]]) -> int:
    total = 1
    for numbers, pick in groups:
        n = len(set(numbers))
        if pick > n or pick < 0:
            return 0
        total *= math.comb(n, pick)
    return total


def configured_dezenas_count(fixed: list[int], groups: list[tuple[list[int], int]]) -> int:
    return len(set(fixed)) + sum(pick for _, pick in groups)


def find_overlap_warnings(fixed: list[int], groups: list[tuple[list[int], int]]) -> list[str]:
    warnings = []
    fixed_set = set(fixed)

    seen_in_groups: set[int] = set()
    for idx, (numbers, _) in enumerate(groups, start=1):
        group_set = set(numbers)
        overlap_fixed = group_set & fixed_set
        if overlap_fixed:
            nums = ", ".join(f"{n:02d}" for n in sorted(overlap_fixed))
            warnings.append(f"Grupo {idx} repete dezenas fixas: {nums}.")

        overlap_groups = group_set & seen_in_groups
        if overlap_groups:
            nums = ", ".join(f"{n:02d}" for n in sorted(overlap_groups))
            warnings.append(f"Grupo {idx} repete dezenas de outro grupo: {nums}.")

        seen_in_groups |= group_set

    return warnings


def fetch_latest_result() -> dict:
    response = requests.get(API_URL, timeout=15)
    response.raise_for_status()
    return response.json()


def fetch_contest_result(contest: int) -> dict:
    response = requests.get(API_CONTEST_URL.format(contest=contest), timeout=15)
    response.raise_for_status()
    return response.json()


def result_date(result: dict) -> date:
    return datetime.strptime(result["data"], "%d/%m/%Y").date()


def fetch_results_for_dates(start: date, end: date) -> list[dict]:
    latest = fetch_latest_result()
    current = latest
    results = []

    while result_date(current) >= start:
        drawn_date = result_date(current)
        if drawn_date <= end:
            results.append(current)

        previous_contest = int(current["concurso"]) - 1
        if previous_contest < 1:
            break
        current = fetch_contest_result(previous_contest)

    return sorted(results, key=lambda item: int(item["concurso"]))


def fetch_recent_results(count: int = 10) -> list[dict]:
    latest = fetch_latest_result()
    results = [latest]
    for contest in range(int(latest["concurso"]) - 1, int(latest["concurso"]) - count, -1):
        if contest < 1:
            break
        results.append(fetch_contest_result(contest))
    return sorted(results, key=lambda item: int(item["concurso"]), reverse=True)


def count_hits(game: list[int], drawn: set[int]) -> int:
    return len(set(game) & drawn)


def prize_units(game_size: int, hits: int) -> dict[int, int]:
    if game_size not in BET_PRICES:
        return {points: 0 for points in range(11, 16)}
    misses = game_size - hits
    return {
        points: math.comb(hits, points) * math.comb(misses, 15 - points)
        if hits >= points and misses >= 15 - points
        else 0
        for points in range(11, 16)
    }


def prizes_by_points(result: dict) -> dict[int, float]:
    return {
        int(item["descricao"].split()[0]): float(item["valorPremio"])
        for item in result.get("premiacoes", [])
    }


def brl(value: float) -> str:
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


PDF_PAGE_WIDTH = 595
PDF_PAGE_HEIGHT = 842


def pdf_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def pdf_text(x: float, y_top: float, text: str, size: float = 10, color: str = "0 0 0") -> str:
    y = PDF_PAGE_HEIGHT - y_top
    return f"BT /F1 {size} Tf {color} rg 1 0 0 1 {x:.2f} {y:.2f} Tm ({pdf_escape(text)}) Tj ET"


def pdf_rect(x: float, y_top: float, width: float, height: float, color: str, fill: bool = True) -> str:
    y = PDF_PAGE_HEIGHT - y_top - height
    operator = "f" if fill else "S"
    return f"{color} {'rg' if fill else 'RG'} {x:.2f} {y:.2f} {width:.2f} {height:.2f} re {operator}"


def draw_pdf_game_card(game: list[int], game_number: int, top: float) -> str:
    x, width, height = 38, 519, 228
    commands = [
        pdf_rect(x, top, width, height, "0.98 0.98 0.99"),
        pdf_rect(x, top, width, height, "0.40 0.10 0.30", fill=False),
        pdf_rect(x, top, width, 30, "0.40 0.10 0.30"),
        pdf_text(x + 16, top + 20, "LOTOFACIL - FOLHA DE CONFERENCIA", 13, "1 1 1"),
        pdf_text(x + 360, top + 19, f"JOGO {game_number:03d}", 10, "1 1 1"),
        pdf_text(x + 18, top + 51, "NAO OFICIAL - NAO VALIDA PARA REGISTRO", 8, "0.40 0.10 0.30"),
        pdf_text(x + 18, top + 68, "Dezenas marcadas", 9, "0.20 0.10 0.20"),
    ]
    selected = set(game)
    cell_width, cell_height = 45, 25
    gap_x, gap_y = 7, 5
    grid_width = cell_width * 5 + gap_x * 4
    grid_x = x + (width - grid_width) / 2
    grid_y = top + 53
    for row in range(5):
        for column in range(5):
            number = column * 5 + row + 1
            cell_x = grid_x + column * (cell_width + gap_x)
            cell_y = grid_y + row * (cell_height + gap_y)
            marked = number in selected
            commands.append(pdf_rect(cell_x, cell_y, cell_width, cell_height, "0.40 0.10 0.30" if marked else "1 1 1"))
            commands.append(pdf_rect(cell_x, cell_y, cell_width, cell_height, "0.60 0.20 0.45", fill=False))
            label_color = "1 1 1" if marked else "0.40 0.10 0.30"
            commands.append(pdf_text(cell_x + 14, cell_y + 17, f"{number:02d}", 10, label_color))
    commands.extend([
        pdf_text(x + 18, top + 212, "Jogo:", 8, "0.20 0.10 0.20"),
        pdf_text(x + 55, top + 212, " ".join(f"{number:02d}" for number in game), 8, "0.20 0.10 0.20"),
        pdf_text(x + 18, top + 224, "Use esta folha apenas para organizacao e conferencia pessoal.", 7, "0.35 0.35 0.35"),
    ])
    return "\n".join(commands)


def build_games_pdf(games: list[list[int]]) -> bytes:
    """Cria um PDF A4 autocontido, sem dependências externas."""
    page_streams = []
    for first_game in range(0, len(games), 3):
        commands = [pdf_text(38, 25, "Jogos Lotofacil - conferencia pessoal", 12, "0.25 0.12 0.20")]
        for offset, game in enumerate(games[first_game:first_game + 3]):
            commands.append(draw_pdf_game_card(game, first_game + offset + 1, 48 + offset * 245))
        page_streams.append("\n".join(commands).encode("cp1252", "replace"))

    objects = [b"<< /Type /Catalog /Pages 2 0 R >>", None, b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    page_object_numbers = []
    for stream in page_streams:
        content_number = len(objects) + 1
        page_number = content_number + 1
        objects.append(b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream")
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PDF_PAGE_WIDTH} {PDF_PAGE_HEIGHT}] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_number} 0 R >>".encode()
        )
        page_object_numbers.append(page_number)
    objects[1] = ("<< /Type /Pages /Kids [" + " ".join(f"{number} 0 R" for number in page_object_numbers) + f"] /Count {len(page_object_numbers)} >>").encode()

    output = bytearray(b"%PDF-1.4\n%" + bytes([0xE2, 0xE3, 0xCF, 0xD3]) + b"\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{index} 0 obj\n".encode())
        output.extend(obj)
        output.extend(b"\nendobj\n")
    xref_offset = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    output.extend(b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets[1:]))
    output.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF".encode())
    return bytes(output)


def render_generator():
    st.markdown(MODERN_CSS, unsafe_allow_html=True)
    st.subheader("Gerador de Combinações")
    st.caption("Marque as dezenas no volante interativo: 1º clique fixa a dezena (vinho), 2º clique torna variável (azul) e 3º clique remove.")

    fixed, variables, order = render_unified_ticket("main_ticket")
    
    st.markdown("---")
    variable_pick = st.number_input(
        "Quantas dezenas variáveis entram em cada cartela gerada?",
        min_value=0,
        max_value=len(variables),
        value=min(1, len(variables)) if variables else 0,
        step=1,
        help="As combinações serão geradas escolhendo essa quantidade entre as dezenas azuis.",
    )

    configured_count = len(fixed) + int(variable_pick)
    combination_count = math.comb(len(variables), int(variable_pick)) if variables else (1 if fixed else 0)
    
    first_metric, second_metric = st.columns(2)
    first_metric.metric("Dezenas por Cartela", configured_count)
    second_metric.metric("Combinações Previstas", f"{combination_count:,}".replace(",", "."))

    if configured_count and not 15 <= configured_count <= 20:
        st.warning("Uma aposta Lotofácil válida deve ter entre 15 e 20 dezenas por cartela.")

    st.markdown("---")
    st.markdown("#### Filtros Avançados")
    enable_sequence_filter = st.checkbox("Filtrar por sequência de números", key="main_enable_seq")
    sequence_limit = 0
    if enable_sequence_filter:
        sequence_limit = st.number_input(
            "Eliminar jogos que tenham uma sequência de pelo menos (dezenas):",
            min_value=2,
            max_value=15,
            value=3,
            step=1,
            key="main_seq_limit",
            help="Se 3 for escolhido, jogos contendo 1,2,3 ou 5,6,7 serão eliminados."
        )

    st.markdown("<br>", unsafe_allow_html=True)
    generate_column, checker_column = st.columns(2)
    generate_clicked = generate_column.button("⚡ Gerar Combinações", type="primary", use_container_width=True)
    checker_column.button(
        "🔍 Conferir Jogos Gerados", use_container_width=True,
        help="Abre o conferidor, carrega os jogos gerados e busca os últimos resultados.",
        on_click=open_generated_games_in_checker,
    )
    if st.session_state.pop("checker_navigation_error", False):
        st.warning("Gere as combinações antes de enviá-las ao conferidor.")

    if generate_clicked:
        if not fixed and not variables:
            st.error("Marque pelo menos uma dezena na cartela.")
            return
        if not variables and fixed:
            variable_pick = 0
        try:
            games = generate_ticket_combinations(fixed, variables, int(variable_pick), order)
            if enable_sequence_filter and sequence_limit > 0:
                games = filter_games_by_sequence(games, sequence_limit, fixed=fixed)
        except ValueError as exc:
            st.error(str(exc))
            return
        if not games:
            st.warning("Nenhuma combinação gerada, ou todas foram filtradas.")
            return
        st.session_state["generated_games"] = games
        st.session_state["generated_games_txt"] = "\n".join(format_game(game) for game in games)
        st.success(f"🎉 {len(games):,} combinação(ões) gerada(s) com sucesso!".replace(",", "."))

    if st.session_state.get("generated_games"):
        games = st.session_state["generated_games"]
        st.info(f"✨ **{len(games):,}** jogos prontos para download.".replace(",", "."))
        unique_sizes = sorted({len(game) for game in games})
        st.caption("Dezenas por jogo: " + ", ".join(str(size) for size in unique_sizes))
        preview_count = min(10, len(games))
        st.markdown(f"**Prévia** (primeiros {preview_count} de {len(games)} jogos):")
        for game in games[:preview_count]:
            st.code(format_game(game), language="text")
            
        text_column, pdf_column = st.columns(2)
        text_column.download_button(
            label="📄 Baixar todos os jogos (.txt)",
            data=st.session_state["generated_games_txt"],
            file_name="jogos_lotofacil.txt",
            mime="text/plain",
            use_container_width=True,
        )
        pdf_column.download_button(
            label="🖨️ Baixar Folha Loto (.pdf)",
            data=build_games_pdf(games),
            file_name="jogos_lotofacil_conferencia.pdf",
            mime="application/pdf",
            use_container_width=True,
            help="PDF para organização e conferência pessoal.",
        )


def render_intersection_group(letter: str) -> None:
    state_prefix = f"intersection_{letter.lower()}"
    st.markdown(f"### Arquivo {letter}")
    st.caption("1º clique = fixa (vinho); 2º clique = variável (azul).")
    fixed, variables, order = render_unified_ticket(f"{state_prefix}_ticket")
    pick = st.number_input(
        f"Variáveis por jogo do Arquivo {letter}",
        min_value=0,
        max_value=len(variables),
        value=min(1, len(variables)) if variables else 0,
        key=f"{state_prefix}_pick",
    )
    total = len(fixed) + int(pick)
    count = math.comb(len(variables), int(pick)) if variables else (1 if fixed else 0)
    metric_a, metric_b = st.columns(2)
    metric_a.metric("Dezenas por Aposta", total)
    metric_b.metric("Jogos Previstos", f"{count:,}".replace(",", "."))
    if total and total not in BET_PRICES:
        st.warning("Cada jogo de A ou B deve ter de 15 a 20 dezenas.")

    st.markdown("##### Filtro")
    enable_sequence_filter = st.checkbox(f"Filtrar por sequência de números (Arquivo {letter})", key=f"{state_prefix}_enable_seq")
    sequence_limit = 0
    if enable_sequence_filter:
        sequence_limit = st.number_input(
            "Tamanho máximo de dezenas consecutivas:",
            min_value=2,
            max_value=15,
            value=3,
            step=1,
            key=f"{state_prefix}_seq_limit",
        )

    if st.button(f"🚀 Gerar Arquivo {letter}", key=f"generate_{state_prefix}", type="primary"):
        if total not in BET_PRICES:
            st.error("Configure de 15 a 20 dezenas por jogo antes de gerar.")
        else:
            games = generate_ticket_combinations(fixed, variables, int(pick), order)
            if enable_sequence_filter and sequence_limit > 0:
                games = filter_games_by_sequence(games, sequence_limit, fixed=fixed)
            st.session_state[f"{state_prefix}_games"] = games
            st.session_state[f"{state_prefix}_fixed"] = fixed
            if not games:
                st.warning(f"O Arquivo {letter} não gerou jogos (ou todos foram filtrados).")
            else:
                st.success(f"Arquivo {letter} gerado com {len(games):,} jogo(s).".replace(",", "."))

    games = st.session_state.get(f"{state_prefix}_games", [])
    if games:
        download_col, checker_col = st.columns(2)
        download_col.download_button(
            f"📄 Baixar Arquivo {letter} (.txt)",
            data="\n".join(format_game(game) for game in games),
            file_name=f"arquivo_{letter.lower()}_lotofacil.txt",
            mime="text/plain",
            key=f"download_{state_prefix}",
            use_container_width=True,
        )
        checker_col.button(
            f"🔍 Conferir Jogos do Arquivo {letter}",
            key=f"checker_{state_prefix}",
            on_click=make_open_intersection_ab_in_checker(letter),
            use_container_width=True,
            help="Abre o conferidor com os jogos do Arquivo {}, busca os últimos resultados automaticamente.".format(letter),
        )
        if st.session_state.pop("checker_navigation_error", False):
            st.warning(f"Gere o Arquivo {letter} antes de enviá-lo ao conferidor.")


def render_intersection_module():
    st.markdown(MODERN_CSS, unsafe_allow_html=True)
    st.subheader("Módulo A/B/C - Interseção & Variáveis Extras")
    st.caption("Gere os Arquivos A e B. No Passo 3, o sistema combina os miolos variáveis e acrescenta as dezenas extras escolhidas.")

    with st.expander("Passo 1 — Gerar Arquivo A", expanded=True):
        render_intersection_group("A")
    with st.expander("Passo 2 — Gerar Arquivo B"):
        render_intersection_group("B")
    with st.expander("Passo 3 — Gerar Arquivo C", expanded=True):
        games_a = st.session_state.get("intersection_a_games", [])
        games_b = st.session_state.get("intersection_b_games", [])
        fixed_a = st.session_state.get("intersection_a_fixed", [])
        fixed_b = st.session_state.get("intersection_b_fixed", [])
        if not games_a or not games_b:
            st.info("💡 Gere os Arquivos A e B primeiro para habilitar a combinação do Arquivo C.")
            return

        st.markdown("#### Dezenas Variáveis Extras (Opcional)")
        extra_variables = render_extra_ticket("intersection_extra_variables")
        target_size = st.number_input(
            "Total de dezenas por aposta do Arquivo C",
            min_value=15,
            max_value=20,
            value=15,
            step=1,
            key="intersection_target_size",
        )
        st.caption(
            f"Miolo de A: sem {len(fixed_a)} fixa(s). Miolo de B: sem {len(fixed_b)} fixa(s). "
            f"Extras selecionadas: {len(extra_variables)}."
        )

        st.markdown("#### Filtro")
        enable_sequence_filter = st.checkbox("Filtrar por sequência de números (Arquivo C)", key="intersection_c_enable_seq")
        sequence_limit = 0
        if enable_sequence_filter:
            sequence_limit = st.number_input(
                "Tamanho máximo de dezenas consecutivas:",
                min_value=2,
                max_value=15,
                value=3,
                step=1,
                key="intersection_c_seq_limit",
            )

        gen_col_c, check_col_c = st.columns(2)
        if gen_col_c.button("✨ Gerar Arquivo C", type="primary", key="generate_intersection_c", use_container_width=True):
            games_c = generate_file_c(
                games_a, games_b, fixed_a, fixed_b, extra_variables, int(target_size)
            )
            if enable_sequence_filter and sequence_limit > 0:
                games_c = filter_games_by_sequence(games_c, sequence_limit)

            if not games_c:
                st.error(
                    "Nenhum jogo gerado. Os miolos de A e B excedem o total, ou os filtros removeram tudo."
                )
            else:
                st.session_state["intersection_c_games"] = games_c
                sizes = [len(game) for game in games_c]
                incomplete = [size for size in sizes if size < int(target_size)]
                if incomplete:
                    missing = max(int(target_size) - size for size in incomplete)
                    st.warning(
                        f"Arquivo C gerado com a junção A+B, mas {len(incomplete)} jogo(s) ainda não atingem "
                        f"{int(target_size)} dezenas. Faltam até {missing} dezena(s); selecione extras se quiser completá-los."
                    )
                else:
                    st.success(f"🎉 Arquivo C gerado com {len(games_c):,} jogo(s) de {int(target_size)} dezenas.".replace(",", "."))
        check_col_c.button(
            "🔍 Conferir Jogos do Arquivo C",
            key="checker_intersection_c_quick",
            on_click=open_intersection_c_in_checker,
            use_container_width=True,
            help="Abre o conferidor com os jogos do Arquivo C e busca os últimos resultados automaticamente.",
        )
        if st.session_state.pop("checker_navigation_error", False):
            st.warning("Gere o Arquivo C antes de enviá-lo ao conferidor.")

        games_c = st.session_state.get("intersection_c_games", [])
        if games_c:
            text_column, pdf_column, checker_column = st.columns(3)
            text_column.download_button(
                "📄 Baixar Arquivo C (.txt)",
                data="\n".join(format_game(game) for game in games_c),
                file_name="arquivo_c_lotofacil.txt",
                mime="text/plain",
                key="download_intersection_c",
                use_container_width=True,
            )
            pdf_column.download_button(
                "🖨️ Baixar Arquivo C (.pdf)",
                data=build_games_pdf(games_c),
                file_name="arquivo_c_lotofacil_conferencia.pdf",
                mime="application/pdf",
                key="download_intersection_c_pdf",
                use_container_width=True,
            )
            checker_column.button(
                "🔍 Conferir Arquivo C",
                key="checker_intersection_c",
                on_click=open_intersection_c_in_checker,
                use_container_width=True,
                disabled=any(len(game) not in BET_PRICES for game in games_c),
            )
            if any(len(game) not in BET_PRICES for game in games_c):
                st.caption("Complete as dezenas extras para habilitar a conferência do Arquivo C.")
            st.caption("Prévia do Arquivo C:")
            for game in games_c[:10]:
                st.code(format_game(game), language="text")


def render_checker():
    st.markdown(MODERN_CSS, unsafe_allow_html=True)
    st.subheader("Conferidor Oficial de Concursos")
    st.caption("Selecione no calendário as datas ou busque pelos últimos concursos. A premiação considera a tabela oficial da CAIXA.")

    auto_check = st.session_state.get("auto_check_pending", False)
    if auto_check:
        with st.spinner("🔄 Buscando os 10 últimos concursos e conferindo os jogos..."):
            try:
                st.session_state["calendar_results"] = fetch_recent_results(10)
                st.session_state["checker_selected_contests"] = [
                    int(result["concurso"]) for result in st.session_state["calendar_results"]
                ]
            except requests.RequestException as exc:
                st.session_state["auto_check_pending"] = False
                st.error(f"Erro ao buscar os últimos concursos: {exc}")
                return

    today = date.today()
    selected_dates = st.date_input(
        "📅 Calendário de Concursos",
        value=(today - timedelta(days=7), today),
        max_value=today,
        format="DD/MM/YYYY",
        help="Selecione uma data ou período; o app busca os concursos realizados nele.",
    )
    if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
        start_date, end_date = selected_dates
    else:
        start_date = end_date = selected_dates

    if start_date > end_date:
        st.error("A data inicial deve ser anterior à final.")
        return
    if (end_date - start_date).days > 120:
        st.warning("Para evitar muitas consultas, selecione até 120 dias.")
        return

    if st.button("🔍 Buscar Concursos no Calendário"):
        with st.spinner("Consultando resultados na API..."):
            try:
                st.session_state["calendar_results"] = fetch_results_for_dates(start_date, end_date)
            except requests.RequestException as exc:
                st.error(f"Erro ao buscar resultados: {exc}")
                return

    found_results = st.session_state.get("calendar_results", [])
    result_by_contest = {int(item["concurso"]): item for item in found_results}
    if result_by_contest:
        selected_contests = st.multiselect(
            "Concursos a Conferir",
            options=list(result_by_contest),
            default=list(result_by_contest),
            format_func=lambda contest: f"Concurso {contest} — {result_by_contest[contest]['data']}",
            key="checker_selected_contests",
        )
        for contest in selected_contests:
            result = result_by_contest[contest]
            drawn = sorted(int(d) for d in result["dezenas"])
            st.caption(f"📌 **Concurso {contest} ({result['data']})**: {', '.join(f'{d:02d}' for d in drawn)}")
    else:
        selected_contests = []

    st.markdown("---")
    st.markdown("**Seus Jogos**")
    input_method = st.radio(
        "Como deseja enviar os jogos?", ["Colar texto", "Enviar arquivo .txt"],
        horizontal=True, key="checker_input_method",
    )
    games_text = ""
    if input_method == "Colar texto":
        games_text = st.text_area(
            "Cole os jogos (um por linha)", height=180,
            placeholder="01,02,03,04,05,06,07,08,09,10,11,12,13,14,15",
            key="checker_games_text",
        )
    else:
        uploaded = st.file_uploader("Arquivo .txt", type=["txt"])
        if uploaded:
            games_text = uploaded.read().decode("utf-8")

    run_check = st.button("🚀 Conferir Jogos", type="primary")
    if auto_check:
        st.session_state["auto_check_pending"] = False
        run_check = True

    if run_check:
        if not selected_contests:
            st.warning("Busque e selecione pelo menos um concurso no calendário.")
            return
        lines = games_text.strip().splitlines()
        if not lines:
            st.warning("Nenhum jogo informado.")
            return

        games, invalid_lines = [], []
        for idx, line in enumerate(lines, start=1):
            game = parse_game_line(line)
            if game is None:
                continue
            if len(game) not in BET_PRICES:
                invalid_lines.append(f"Linha {idx}: informe de 15 a 20 dezenas únicas.")
                continue
            games.append(game)
        for message in invalid_lines:
            st.warning(message)
        if not games:
            st.warning("Nenhum jogo válido para conferir.")
            return

        investment_per_contest = sum(BET_PRICES[len(game)] for game in games)
        total_investment = investment_per_contest * len(selected_contests)
        overall_units = {points: 0 for points in range(11, 16)}
        total_received = 0.0
        all_rows = []

        for contest in selected_contests:
            result = result_by_contest[contest]
            drawn_set = set(int(d) for d in result["dezenas"])
            contest_prizes = prizes_by_points(result)
            contest_units = {points: 0 for points in range(11, 16)}
            contest_received = 0.0
            for game_index, game in enumerate(games, start=1):
                hits = count_hits(game, drawn_set)
                units = prize_units(len(game), hits)
                received = sum(units[p] * contest_prizes.get(p, 0) for p in units)
                contest_received += received
                for points in contest_units:
                    contest_units[points] += units[points]
                    overall_units[points] += units[points]
                all_rows.append({
                    "Concurso": contest, "Data": result["data"], "Jogo": game_index,
                    "Dezenas": len(game), "Acertos": hits,
                    "Prêmios (11–15)": sum(units.values()), "Valor Recebido": brl(received),
                })
            total_received += contest_received
            st.markdown(f"#### Concurso {contest} — {result['data']}")
            columns = st.columns(5)
            for index, points in enumerate(range(11, 16)):
                columns[index].metric(f"{points} Pontos", contest_units[points])
            st.caption(f"💰 Recebido neste concurso: **{brl(contest_received)}**")

        st.markdown("---")
        st.markdown("### 📊 Resumo Financeiro & Desempenho")
        games_col, invested_col, prizes_col, balance_col = st.columns(4)
        games_col.metric("Total de Jogos", len(games))
        invested_col.metric("Investimento Total", brl(total_investment))
        prizes_col.metric("Premiação Total", brl(total_received))
        
        balance_val = total_received - total_investment
        balance_col.metric("Saldo Final", brl(balance_val), delta=f"{balance_val:+,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

        columns = st.columns(5)
        for index, points in enumerate(range(11, 16)):
            columns[index].metric(f"Total {points} Pts", overall_units[points])

        winners = [row for row in all_rows if row["Prêmios (11–15)"]]
        if winners:
            st.markdown("#### 🏆 Jogos Premiados")
            st.dataframe(winners, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum prêmio de 11 a 15 pontos nos concursos selecionados.")
        st.markdown("#### 📋 Todos os Jogos Conferidos")
        st.dataframe(all_rows, use_container_width=True, hide_index=True)


def main():
    st.set_page_config(
        page_title="Lotofácil Pro — Gerador & Conferidor",
        page_icon="🎱",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    # Hero Header Sem Imagem de Logo
    st.markdown(
        """
        <div class="hero-container">
            <div class="hero-badge">🎱 LOTOFÁCIL INTELIGENTE</div>
            <h1 class="hero-title">Gerador & Conferidor Pro</h1>
            <p class="hero-subtitle">Geração de combinações estratégicas, interseções de arquivos e conferência de concursos da Lotofácil.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if "active_section" not in st.session_state:
        st.session_state["active_section"] = "Gerador de Combinações"

    active_section = st.radio(
        "Navegação",
        ["Gerador de Combinações", "Módulo A/B/C", "Conferidor"],
        horizontal=True,
        key="active_section",
        label_visibility="collapsed",
    )

    st.markdown("<br>", unsafe_allow_html=True)

    if active_section == "Gerador de Combinações":
        render_generator()
    elif active_section == "Módulo A/B/C":
        render_intersection_module()
    else:
        render_checker()


if __name__ == "__main__":
    main()
