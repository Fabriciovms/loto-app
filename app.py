import itertools
import math
import re
from datetime import date, datetime, timedelta
from itertools import combinations
from pathlib import Path

import requests
import streamlit as st

LOTOFACIL_MIN = 1
LOTOFACIL_MAX = 25
ALL_NUMBERS = list(range(LOTOFACIL_MIN, LOTOFACIL_MAX + 1))
API_URL = "https://loteriascaixa-api.herokuapp.com/api/lotofacil/latest"
API_CONTEST_URL = "https://loteriascaixa-api.herokuapp.com/api/lotofacil/{contest}"
LOGO_PATH = Path(__file__).parent / "logo" / "lotoapp.png"

# Tabela vigente da aposta da Lotofácil (CAIXA). Uma aposta com mais de 15
# dezenas equivale a várias apostas simples e por isso tem preço próprio.
BET_PRICES = {15: 3.50, 16: 56.00, 17: 476.00, 18: 2856.00, 19: 13566.00, 20: 54264.00}

NUMBER_BUTTON_CSS = """
<style>
    [class*="st-key-ticket_"] button {
        background: #fffef7 !important;
        border: 1.5px solid #ae496b !important;
        border-radius: 0 !important;
        color: #6e2541 !important;
        box-shadow: inset 0 0 0 2px #fffef7 !important;
        font-family: Arial, sans-serif !important;
        font-size: 0.9rem !important;
        font-weight: 700 !important;
        height: 2.3rem !important;
        min-height: 2.3rem !important;
        padding: 0 !important;
    }
    [class*="st-key-ticket_"] button:hover {
        background: #ffe8ef !important;
        border-color: #6e2541 !important;
    }
    [class*="st-key-ticket_fixed_"] button {
        background: #762043 !important;
        border-color: #762043 !important;
        box-shadow: inset 0 0 0 2px #762043 !important;
        color: #ffffff !important;
    }
    [class*="st-key-ticket_variable_"] button {
        background: #21678a !important;
        border-color: #21678a !important;
        box-shadow: inset 0 0 0 2px #21678a !important;
        color: #ffffff !important;
    }
    [class*="st-key-ticket_extra_"] button[kind="primary"] {
        background: #177b63 !important;
        border-color: #177b63 !important;
        box-shadow: inset 0 0 0 2px #177b63 !important;
        color: #ffffff !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:has([class*="st-key-ticket_"]) {
        background: #f7f8d9 !important;
        border: 2px solid #8e3158 !important;
        border-radius: 0.25rem !important;
        box-shadow: 0 3px 0 #dfc4a4 !important;
    }
    .ticket-title {
        background: linear-gradient(100deg, #762043, #a34169);
        color: #fff;
        font: 800 1.25rem/1 Arial, sans-serif;
        letter-spacing: 0.08em;
        margin: -0.5rem -0.5rem 0.65rem;
        padding: 0.75rem 1rem;
        text-align: center;
    }
    .ticket-instruction {
        color: #6e2541;
        font-size: 0.78rem;
        font-weight: 700;
        margin-bottom: 0.6rem;
        text-align: center;
    }
    .ticket-footer {
        border-top: 1px solid #c48a9c;
        color: #6e2541;
        font-size: 0.75rem;
        margin-top: 0.7rem;
        padding-top: 0.5rem;
        text-align: center;
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
        # Compatibilidade com seleções guardadas antes de a ordem dos cliques ser registrada.
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


def render_number_selector(key: str, label: str) -> list[int]:
    init_selection(key)
    st.markdown(f"**{label}**")

    # Centraliza o volante e preserva as proporções de uma cartela física.
    side_left, ticket_column, side_right = st.columns([1, 2.4, 1])
    with ticket_column:
        with st.container(border=True):
            st.markdown('<div class="ticket-title">LOTOFÁCIL</div>', unsafe_allow_html=True)
            st.markdown(
                '<div class="ticket-instruction">MARQUE DE 15 A 20 NÚMEROS · APOSTA 1</div>',
                unsafe_allow_html=True,
            )
            # A cartela oficial organiza as dezenas em cinco colunas verticais.
            for row in range(5):
                cols = st.columns(5, gap="small")
                for col_idx in range(5):
                    num = col_idx * 5 + row + 1
                    with cols[col_idx]:
                        is_selected = num in st.session_state[key]
                        if st.button(
                            f"{num:02d}",
                            key=f"ticket_{key}_{num}",
                            type="primary" if is_selected else "secondary",
                            use_container_width=True,
                        ):
                            toggle_number(key, num)
                            st.rerun()
            st.markdown(
                '<div class="ticket-footer">Toque no quadrado da dezena para marcar ou desmarcar.</div>',
                unsafe_allow_html=True,
            )

    selected = get_selection(key)
    if selected:
        st.caption(f"Selecionados ({len(selected)}): {', '.join(f'{n:02d}' for n in selected)}")
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
    # Ao mudar de categoria, a dezena passa a valer a partir deste clique.
    order[number] = st.session_state.get("ticket_click_counter", 0)
    st.session_state["ticket_click_counter"] = order[number] + 1


def render_unified_ticket(key: str) -> tuple[list[int], list[int], dict[int, int]]:
    fixed, variables, order = ticket_state(key)
    side_left, ticket_column, side_right = st.columns([1, 2.4, 1])
    with ticket_column:
        with st.container(border=True):
            st.markdown('<div class="ticket-title">LOTOFÁCIL</div>', unsafe_allow_html=True)
            st.markdown(
                '<div class="ticket-instruction">1º CLIQUE: FIXA · 2º CLIQUE: VARIÁVEL · 3º CLIQUE: DESMARCA</div>',
                unsafe_allow_html=True,
            )
            states = st.session_state[f"{key}_states"]
            for row in range(5):
                columns = st.columns(5, gap="small")
                for column_index in range(5):
                    number = column_index * 5 + row + 1
                    state = states.get(number, 0)
                    state_name = ("empty", "fixed", "variable")[state]
                    with columns[column_index]:
                        if st.button(
                            f"{number:02d}",
                            key=f"ticket_{state_name}_{key}_{number}",
                            type="primary" if state else "secondary",
                            use_container_width=True,
                        ):
                            cycle_ticket_number(key, number)
                            st.rerun()
            st.markdown(
                '<div class="ticket-footer"><b>Fixa</b> = vinho · <b>Variável</b> = azul · vazio = não selecionada</div>',
                unsafe_allow_html=True,
            )

    fixed, variables, order = ticket_state(key)
    st.caption(
        f"Fixas ({len(fixed)}): {', '.join(f'{n:02d}' for n in fixed) or 'nenhuma'}  |  "
        f"Variáveis ({len(variables)}): {', '.join(f'{n:02d}' for n in variables) or 'nenhuma'}"
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
    side_left, ticket_column, side_right = st.columns([1, 2.4, 1])
    with ticket_column:
        with st.container(border=True):
            st.markdown('<div class="ticket-title">VARIAVEIS EXTRAS - ARQUIVO C</div>', unsafe_allow_html=True)
            st.markdown(
                '<div class="ticket-instruction">CLIQUE PARA MARCAR OU DESMARCAR AS DEZENAS EXTRAS</div>',
                unsafe_allow_html=True,
            )
            for row in range(5):
                columns = st.columns(5, gap="small")
                for column_index in range(5):
                    number = column_index * 5 + row + 1
                    with columns[column_index]:
                        selected = number in st.session_state[key]
                        if st.button(
                            f"{number:02d}",
                            key=f"ticket_extra_{key}_{number}",
                            type="primary" if selected else "secondary",
                            use_container_width=True,
                        ):
                            toggle_number(key, number)
                            st.rerun()
            st.markdown('<div class="ticket-footer">Verde = variavel extra selecionada.</div>', unsafe_allow_html=True)
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
                # Os miolos já excederam o tamanho final configurado; não é
                # possível reduzir um deles sem descaracterizar A ou B.
                continue
            candidates = [number for number in extra_variables if number not in base]
            # Extras são opcionais. Sem dezenas suficientes, preservamos a
            # junção A+B (e as extras já escolhidas) para o usuário completar
            # depois, exibindo o aviso de que o jogo ainda não é válido.
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
    """Busca concursos pela faixa de datas, partindo do último publicado."""
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
    """Busca os últimos concursos publicados, incluindo o mais recente."""
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
    """Quantidade de apostas premiadas embutidas em uma aposta múltipla."""
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
    """Desenha uma cartela de conferência; não replica nem substitui volante oficial."""
    x, width, height = 38, 519, 228
    commands = [
        pdf_rect(x, top, width, height, "0.97 0.97 0.86"),
        pdf_rect(x, top, width, height, "0.45 0.12 0.27", fill=False),
        pdf_rect(x, top, width, 30, "0.45 0.12 0.27"),
        pdf_text(x + 16, top + 20, "LOTOFACIL - FOLHA DE CONFERENCIA", 13, "1 1 1"),
        pdf_text(x + 360, top + 19, f"JOGO {game_number:03d}", 10, "1 1 1"),
        pdf_text(x + 18, top + 51, "NAO OFICIAL - NAO VALIDA PARA REGISTRO", 8, "0.45 0.12 0.27"),
        pdf_text(x + 18, top + 68, "Dezenas marcadas", 9, "0.30 0.15 0.22"),
    ]
    selected = set(game)
    # Grade inteira cabe dentro do cartão: 5 colunas x 5 linhas, sem invadir
    # o rodapé nem a cartela seguinte.
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
            commands.append(pdf_rect(cell_x, cell_y, cell_width, cell_height, "0.45 0.12 0.27" if marked else "1 1 1"))
            commands.append(pdf_rect(cell_x, cell_y, cell_width, cell_height, "0.62 0.25 0.40", fill=False))
            label_color = "1 1 1" if marked else "0.45 0.12 0.27"
            commands.append(pdf_text(cell_x + 14, cell_y + 17, f"{number:02d}", 10, label_color))
    commands.extend([
        pdf_text(x + 18, top + 212, "Jogo:", 8, "0.30 0.15 0.22"),
        pdf_text(x + 55, top + 212, " ".join(f"{number:02d}" for number in game), 8, "0.30 0.15 0.22"),
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
        # Helvetica padrão usa a tabela WinAnsi; cp1252 preserva os acentos
        # em português sem introduzir caracteres de substituição.
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

    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
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


def render_generator_legacy():
    st.markdown(NUMBER_BUTTON_CSS, unsafe_allow_html=True)

    st.subheader("Gerador de Combinações")
    st.caption(
        "Selecione as dezenas fixas e configure grupos variáveis. "
        "Clique nos botões para marcar ou desmarcar cada dezena."
    )

    fixed = render_number_selector("fixed_nums", "Dezenas fixas")

    st.markdown("**Grupos variáveis**")
    num_groups = st.number_input(
        "Quantidade de grupos",
        min_value=0,
        max_value=10,
        value=1,
        step=1,
        key="num_groups",
    )

    groups: list[tuple[list[int], int]] = []
    for i in range(int(num_groups)):
        st.divider()
        st.markdown(f"**Grupo {i + 1}**")
        group_nums = render_number_selector(f"group_nums_{i}", f"Dezenas do grupo {i + 1}")

        max_pick = len(group_nums)
        pick = st.number_input(
            "Quantidade a escolher neste grupo",
            min_value=0,
            max_value=max(max_pick, 0),
            value=min(1, max_pick) if max_pick else 0,
            key=f"group_pick_{i}",
        )

        if group_nums:
            groups.append((group_nums, int(pick)))

    dezenas_config = configured_dezenas_count(fixed, groups)
    combo_count = expected_combination_count(groups) if groups else (1 if fixed else 0)

    m1, m2 = st.columns(2)
    m1.metric("Dezenas por combinação (configurado)", dezenas_config)
    m2.metric("Combinações previstas", f"{combo_count:,}".replace(",", "."))

    overlap_warnings = find_overlap_warnings(fixed, groups)
    if overlap_warnings:
        for warning in overlap_warnings:
            st.warning(
                f"{warning} Isso reduz a quantidade de dezenas únicas em cada jogo gerado."
            )

    variable_priorities = [
        priority
        for i in range(int(num_groups))
        if (priority := selection_priority(f"group_nums_{i}")) is not None
    ]
    fixed_priority = selection_priority("fixed_nums")
    fixed_first = not variable_priorities or (
        fixed_priority is None or fixed_priority < min(variable_priorities)
    )

    if fixed and groups:
        first_group = "fixas" if fixed_first else "variáveis"
        st.caption(f"No TXT, as dezenas {first_group} aparecerão primeiro.")

    generate_column, checker_column = st.columns(2)
    generate_clicked = generate_column.button("Gerar combinações", type="primary", use_container_width=True)
    open_checker = checker_column.button(
        "Conferir jogos gerados", use_container_width=True,
        help="Abre o conferidor, usa os jogos gerados e consulta os 10 últimos concursos.",
    )

    if open_checker:
        generated_text = st.session_state.get("generated_games_txt")
        if not generated_text:
            st.warning("Gere as combinações antes de enviá-las ao conferidor.")
        else:
            st.session_state["checker_games_text"] = generated_text
            st.session_state["checker_input_method"] = "Colar texto"
            st.session_state["active_section"] = "Conferidor"
            st.session_state["auto_check_pending"] = True
            st.rerun()

    if generate_clicked:
        if not fixed and not groups:
            st.error("Selecione ao menos dezenas fixas ou configure um grupo variável.")
            return

        if groups and combo_count == 0:
            st.error("Revise os grupos variáveis: quantidade a escolher inválida.")
            return

        try:
            games = generate_combinations(fixed, groups, fixed_first=fixed_first)
        except ValueError as exc:
            st.error(str(exc))
            return

        if not games:
            st.warning("Nenhuma combinação gerada.")
            return

        st.session_state["generated_games"] = games
        st.session_state["generated_games_txt"] = "\n".join(format_game(g) for g in games)
        st.success(f"{len(games):,} combinação(ões) gerada(s)!".replace(",", "."))

    if st.session_state.get("generated_games"):
        games = st.session_state["generated_games"]
        st.info(f"**{len(games):,}** jogos prontos para download.".replace(",", "."))

        unique_sizes = sorted({len(g) for g in games})
        if len(unique_sizes) == 1:
            st.caption(f"Cada jogo terá **{unique_sizes[0]}** dezenas únicas.")
        else:
            st.caption(
                "Tamanho dos jogos (dezenas únicas): "
                + ", ".join(str(size) for size in unique_sizes)
            )

        preview_count = min(10, len(games))
        st.markdown(f"**Prévia** (primeiros {preview_count} de {len(games)} jogos):")
        for game in games[:preview_count]:
            st.text(format_game(game))

        st.download_button(
            label="Baixar todos os jogos (.txt)",
            data=st.session_state["generated_games_txt"],
            file_name="jogos_lotofacil.txt",
            mime="text/plain",
        )


def render_generator():
    st.markdown(NUMBER_BUTTON_CSS, unsafe_allow_html=True)
    st.subheader("Gerador de Combinações")
    st.caption("Use uma única cartela: primeiro clique fixa a dezena, segundo clique a torna variável e terceiro clique a remove.")

    fixed, variables, order = render_unified_ticket("main_ticket")
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
    first_metric.metric("Dezenas por cartela", configured_count)
    second_metric.metric("Combinações previstas", f"{combination_count:,}".replace(",", "."))

    if configured_count and not 15 <= configured_count <= 20:
        st.warning("Uma aposta Lotofácil válida deve ter entre 15 e 20 dezenas por cartela.")

    generate_column, checker_column = st.columns(2)
    generate_clicked = generate_column.button("Gerar combinações", type="primary", use_container_width=True)
    checker_column.button(
        "Conferir jogos gerados", use_container_width=True,
        help="Abre o conferidor, usa os jogos gerados e consulta os 10 últimos concursos.",
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
        except ValueError as exc:
            st.error(str(exc))
            return
        if not games:
            st.warning("Nenhuma combinação gerada.")
            return
        st.session_state["generated_games"] = games
        st.session_state["generated_games_txt"] = "\n".join(format_game(game) for game in games)
        st.success(f"{len(games):,} combinação(ões) gerada(s)!".replace(",", "."))

    if st.session_state.get("generated_games"):
        games = st.session_state["generated_games"]
        st.info(f"**{len(games):,}** jogos prontos para download.".replace(",", "."))
        unique_sizes = sorted({len(game) for game in games})
        st.caption("Dezenas por jogo: " + ", ".join(str(size) for size in unique_sizes))
        preview_count = min(10, len(games))
        st.markdown(f"**Prévia** (primeiros {preview_count} de {len(games)} jogos):")
        for game in games[:preview_count]:
            st.text(format_game(game))
        text_column, pdf_column = st.columns(2)
        text_column.download_button(
            label="Baixar todos os jogos (.txt)",
            data=st.session_state["generated_games_txt"],
            file_name="jogos_lotofacil.txt",
            mime="text/plain",
            use_container_width=True,
        )
        pdf_column.download_button(
            label="Baixar todos os jogos Loto (.pdf)",
            data=build_games_pdf(games),
            file_name="jogos_lotofacil_conferencia_nao_oficial.pdf",
            mime="application/pdf",
            use_container_width=True,
            help="PDF para organização e conferência pessoal; não é um volante válido para registrar apostas.",
        )


def render_intersection_group(letter: str) -> None:
    state_prefix = f"intersection_{letter.lower()}"
    st.markdown(f"### Arquivo {letter}")
    st.caption("Primeiro clique = fixa (vinho); segundo clique = variavel (azul).")
    fixed, variables, order = render_unified_ticket(f"{state_prefix}_ticket")
    pick = st.number_input(
        f"Variaveis por jogo do Arquivo {letter}",
        min_value=0,
        max_value=len(variables),
        value=min(1, len(variables)) if variables else 0,
        key=f"{state_prefix}_pick",
    )
    total = len(fixed) + int(pick)
    count = math.comb(len(variables), int(pick)) if variables else (1 if fixed else 0)
    metric_a, metric_b = st.columns(2)
    metric_a.metric("Dezenas por aposta", total)
    metric_b.metric("Jogos previstos", f"{count:,}".replace(",", "."))
    if total and total not in BET_PRICES:
        st.warning("Cada jogo de A ou B deve ter de 15 a 20 dezenas.")

    if st.button(f"Gerar Arquivo {letter}", key=f"generate_{state_prefix}", type="primary"):
        if total not in BET_PRICES:
            st.error("Configure de 15 a 20 dezenas por jogo antes de gerar.")
        else:
            games = generate_ticket_combinations(fixed, variables, int(pick), order)
            st.session_state[f"{state_prefix}_games"] = games
            st.session_state[f"{state_prefix}_fixed"] = fixed
            st.success(f"Arquivo {letter} gerado com {len(games):,} jogo(s).".replace(",", "."))

    games = st.session_state.get(f"{state_prefix}_games", [])
    if games:
        st.download_button(
            f"Baixar Arquivo {letter} (.txt)",
            data="\n".join(format_game(game) for game in games),
            file_name=f"arquivo_{letter.lower()}_lotofacil.txt",
            mime="text/plain",
            key=f"download_{state_prefix}",
        )


def render_intersection_module():
    st.markdown(NUMBER_BUTTON_CSS, unsafe_allow_html=True)
    st.subheader("Modulo A/B/C - Intersecao e Variaveis Extras")
    st.caption("Gere A e B; no Passo 3 o sistema usa somente os miolos variaveis e acrescenta as dezenas extras selecionadas.")

    with st.expander("Passo 1 - Gerar Arquivo A", expanded=True):
        render_intersection_group("A")
    with st.expander("Passo 2 - Gerar Arquivo B"):
        render_intersection_group("B")
    with st.expander("Passo 3 - Gerar Arquivo C", expanded=True):
        games_a = st.session_state.get("intersection_a_games", [])
        games_b = st.session_state.get("intersection_b_games", [])
        fixed_a = st.session_state.get("intersection_a_fixed", [])
        fixed_b = st.session_state.get("intersection_b_fixed", [])
        if not games_a or not games_b:
            st.info("Gere os Arquivos A e B para habilitar a combinacao do Arquivo C.")
            return

        st.markdown("#### Dezenas variaveis extras (opcional)")
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
            f"Miolo de A: A sem {len(fixed_a)} fixa(s). Miolo de B: B sem {len(fixed_b)} fixa(s). "
            f"Extras selecionadas: {len(extra_variables)}. Sem extras, o Arquivo C sera a juncao direta dos miolos."
        )

        if st.button("Gerar Arquivo C", type="primary", key="generate_intersection_c"):
            games_c = generate_file_c(
                games_a, games_b, fixed_a, fixed_b, extra_variables, int(target_size)
            )
            if not games_c:
                st.error(
                    "Os miolos de A e B excedem o total configurado; escolha um total maior ou reveja A e B."
                )
            else:
                st.session_state["intersection_c_games"] = games_c
                sizes = [len(game) for game in games_c]
                incomplete = [size for size in sizes if size < int(target_size)]
                if incomplete:
                    missing = max(int(target_size) - size for size in incomplete)
                    st.warning(
                        f"Arquivo C gerado com a juncao A+B, mas {len(incomplete)} jogo(s) ainda nao atingem "
                        f"{int(target_size)} dezenas. Faltam ate {missing} dezena(s); selecione extras se quiser completa-los."
                    )
                else:
                    st.success(f"Arquivo C gerado com {len(games_c):,} jogo(s) de {int(target_size)} dezenas.".replace(",", "."))

        games_c = st.session_state.get("intersection_c_games", [])
        if games_c:
            text_column, pdf_column, checker_column = st.columns(3)
            text_column.download_button(
                "Baixar Arquivo C (.txt)",
                data="\n".join(format_game(game) for game in games_c),
                file_name="arquivo_c_lotofacil.txt",
                mime="text/plain",
                key="download_intersection_c",
                use_container_width=True,
            )
            pdf_column.download_button(
                "Baixar Arquivo C Loto (.pdf)",
                data=build_games_pdf(games_c),
                file_name="arquivo_c_lotofacil_conferencia_nao_oficial.pdf",
                mime="application/pdf",
                key="download_intersection_c_pdf",
                use_container_width=True,
            )
            checker_column.button(
                "Conferir Arquivo C",
                key="checker_intersection_c",
                on_click=open_intersection_c_in_checker,
                use_container_width=True,
                disabled=any(len(game) not in BET_PRICES for game in games_c),
            )
            if any(len(game) not in BET_PRICES for game in games_c):
                st.caption("Complete as dezenas extras para habilitar a conferencia do Arquivo C.")
            st.caption("Previa do Arquivo C:")
            for game in games_c[:10]:
                st.text(format_game(game))


def render_checker_legacy():
    st.subheader("Conferidor")
    st.caption("Busca o último resultado da Lotofácil e confere seus jogos.")

    if st.button("Buscar último concurso"):
        with st.spinner("Consultando API..."):
            try:
                st.session_state["latest_result"] = fetch_latest_result()
            except requests.RequestException as exc:
                st.error(f"Erro ao buscar resultado: {exc}")
                return

    result = st.session_state.get("latest_result")
    if result:
        drawn = sorted(int(d) for d in result["dezenas"])
        st.markdown(
            f"**Concurso {result['concurso']}** — {result['data']}  \n"
            f"Dezenas sorteadas: **{', '.join(f'{d:02d}' for d in drawn)}**"
        )

    st.markdown("**Seus jogos**")
    input_method = st.radio(
        "Como enviar os jogos?",
        ["Colar texto", "Enviar arquivo .txt"],
        horizontal=True,
    )

    games_text = ""
    if input_method == "Colar texto":
        games_text = st.text_area(
            "Cole os jogos (um por linha)",
            height=200,
            placeholder="01,02,03,04,05,06,07,08,09,10,11,12,13,14,15",
        )
    else:
        uploaded = st.file_uploader("Arquivo .txt", type=["txt"])
        if uploaded:
            games_text = uploaded.read().decode("utf-8")

    if st.button("Conferir jogos", type="primary"):
        if not result:
            st.warning("Busque o último concurso antes de conferir.")
            return

        drawn_set = set(int(d) for d in result["dezenas"])
        lines = games_text.strip().splitlines()
        if not lines:
            st.warning("Nenhum jogo informado.")
            return

        results = []
        invalid_lines = []
        for idx, line in enumerate(lines, start=1):
            game = parse_game_line(line)
            if game is None:
                continue
            if len(game) < 1:
                invalid_lines.append(f"Linha {idx}: jogo vazio.")
                continue
            hits = count_hits(game, drawn_set)
            results.append({"Jogo": format_game(game), "Dezenas": len(game), "Acertos": hits})

        if invalid_lines:
            for msg in invalid_lines:
                st.warning(msg)

        if not results:
            st.warning("Nenhum jogo válido para conferir.")
            return

        st.markdown(f"**{len(results)}** jogo(s) conferido(s)")

        summary = {11: 0, 12: 0, 13: 0, 14: 0, 15: 0, "outros": 0}
        for r in results:
            h = r["Acertos"]
            if h in summary:
                summary[h] += 1
            else:
                summary["outros"] += 1

        cols = st.columns(5)
        for i, col in enumerate(cols):
            pts = 11 + i
            col.metric(f"{pts} pts", summary[pts])

        if summary["outros"]:
            st.caption(f"Jogos com menos de 11 acertos: {summary['outros']}")

        winners = [r for r in results if r["Acertos"] >= 11]
        if winners:
            st.markdown("**Jogos premiados (11+ acertos)**")
            st.dataframe(winners, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum jogo com 11 ou mais acertos.")

        st.markdown("**Todos os jogos**")
        st.dataframe(results, use_container_width=True, hide_index=True)


def render_checker():
    st.subheader("Conferidor")
    st.caption("Escolha no calendário as datas dos sorteios. A premiação considera os valores publicados em cada concurso.")

    auto_check = st.session_state.get("auto_check_pending", False)
    if auto_check:
        with st.spinner("Buscando os 10 últimos concursos e conferindo os jogos gerados..."):
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
        "Calendário de concursos",
        value=(today - timedelta(days=7), today),
        max_value=today,
        format="DD/MM/YYYY",
        help="Selecione uma data ou período; o app localiza os concursos realizados nele.",
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

    if st.button("Buscar concursos no calendário"):
        with st.spinner("Consultando resultados..."):
            try:
                st.session_state["calendar_results"] = fetch_results_for_dates(start_date, end_date)
            except requests.RequestException as exc:
                st.error(f"Erro ao buscar resultados: {exc}")
                return

    found_results = st.session_state.get("calendar_results", [])
    result_by_contest = {int(item["concurso"]): item for item in found_results}
    if result_by_contest:
        selected_contests = st.multiselect(
            "Concursos a conferir",
            options=list(result_by_contest),
            default=list(result_by_contest),
            format_func=lambda contest: f"Concurso {contest} — {result_by_contest[contest]['data']}",
            key="checker_selected_contests",
        )
        for contest in selected_contests:
            result = result_by_contest[contest]
            drawn = sorted(int(d) for d in result["dezenas"])
            st.caption(f"Concurso {contest} ({result['data']}): {', '.join(f'{d:02d}' for d in drawn)}")
    else:
        selected_contests = []

    st.markdown("**Seus jogos**")
    input_method = st.radio(
        "Como enviar os jogos?", ["Colar texto", "Enviar arquivo .txt"],
        horizontal=True, key="checker_input_method",
    )
    games_text = ""
    if input_method == "Colar texto":
        games_text = st.text_area(
            "Cole os jogos (um por linha)", height=200,
            placeholder="01,02,03,04,05,06,07,08,09,10,11,12,13,14,15",
            key="checker_games_text",
        )
    else:
        uploaded = st.file_uploader("Arquivo .txt", type=["txt"])
        if uploaded:
            games_text = uploaded.read().decode("utf-8")

    run_check = st.button("Conferir jogos", type="primary")
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
                    "Prêmios (11–15)": sum(units.values()), "Valor recebido": brl(received),
                })
            total_received += contest_received
            st.markdown(f"**Concurso {contest} — {result['data']}**")
            columns = st.columns(5)
            for index, points in enumerate(range(11, 16)):
                columns[index].metric(f"{points} pontos", contest_units[points])
            st.caption(f"Recebido neste concurso: {brl(contest_received)}")

        st.divider()
        st.markdown("**Resumo financeiro e de premiações**")
        games_col, invested_col, prizes_col, balance_col = st.columns(4)
        games_col.metric("Jogos lidos", len(games))
        invested_col.metric("Investimento total", brl(total_investment))
        prizes_col.metric("Premiação total", brl(total_received))
        balance_col.metric("Saldo", brl(total_received - total_investment))
        columns = st.columns(5)
        for index, points in enumerate(range(11, 16)):
            columns[index].metric(f"Prêmios de {points} pts", overall_units[points])

        winners = [row for row in all_rows if row["Prêmios (11–15)"]]
        if winners:
            st.markdown("**Jogos premiados**")
            st.dataframe(winners, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum prêmio de 11 a 15 pontos nos concursos selecionados.")
        st.markdown("**Todos os jogos conferidos**")
        st.dataframe(all_rows, use_container_width=True, hide_index=True)


def main():
    st.set_page_config(page_title="Lotofácil — Gerador & Conferidor", page_icon="🎱", layout="wide")
    if LOGO_PATH.exists():
        st.image(str(LOGO_PATH), width=360)
    st.title("Lotofácil")
    st.markdown("Gerador de combinações e conferidor de jogos.")

    if "active_section" not in st.session_state:
        st.session_state["active_section"] = "Gerador de Combinações"
    active_section = st.radio(
        "Navegação",
        ["Gerador de Combinações", "Modulo A/B/C", "Conferidor"],
        horizontal=True,
        key="active_section",
        label_visibility="collapsed",
    )

    if active_section == "Gerador de Combinações":
        render_generator()
    elif active_section == "Modulo A/B/C":
        render_intersection_module()
    else:
        render_checker()


if __name__ == "__main__":
    main()
