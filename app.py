import itertools
import math
import re
from itertools import combinations
from pathlib import Path

import requests
import streamlit as st

LOTOFACIL_MIN = 1
LOTOFACIL_MAX = 25
ALL_NUMBERS = list(range(LOTOFACIL_MIN, LOTOFACIL_MAX + 1))
API_URL = "https://loteriascaixa-api.herokuapp.com/api/lotofacil/latest"
LOGO_PATH = Path(__file__).parent / "logo" / "lotoapp.png"

NUMBER_BUTTON_CSS = """
<style>
    div[data-testid="column"] button[kind="primary"],
    div[data-testid="column"] button[kind="primaryFormSubmit"] {
        background-color: #9333ea !important;
        border-color: #7e22ce !important;
        color: #ffffff !important;
        border-radius: 50% !important;
        min-height: 2.75rem !important;
        font-weight: 700 !important;
    }
    div[data-testid="column"] button[kind="secondary"] {
        background-color: #f3f4f6 !important;
        border-color: #d1d5db !important;
        color: #374151 !important;
        border-radius: 50% !important;
        min-height: 2.75rem !important;
        font-weight: 600 !important;
    }
    div[data-testid="column"] button[kind="secondary"]:hover {
        background-color: #e5e7eb !important;
        border-color: #9333ea !important;
        color: #6b21a8 !important;
    }
</style>
"""


def parse_numbers(text: str) -> list[int]:
    return [int(n) for n in re.findall(r"\d+", text)]


def format_game(numbers: list[int]) -> str:
    return ",".join(f"{n:02d}" for n in sorted(numbers))


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
        st.session_state[key] = set()


def toggle_number(key: str, num: int) -> None:
    init_selection(key)
    if num in st.session_state[key]:
        st.session_state[key].discard(num)
    else:
        st.session_state[key].add(num)


def get_selection(key: str) -> list[int]:
    init_selection(key)
    return sorted(st.session_state[key])


def render_number_selector(key: str, label: str) -> list[int]:
    init_selection(key)
    st.markdown(f"**{label}**")

    for row_start in range(0, 25, 5):
        cols = st.columns(5)
        for col_idx, num in enumerate(range(row_start + 1, row_start + 6)):
            with cols[col_idx]:
                is_selected = num in st.session_state[key]
                if st.button(
                    f"{num:02d}",
                    key=f"btn_{key}_{num}",
                    type="primary" if is_selected else "secondary",
                    use_container_width=True,
                ):
                    toggle_number(key, num)
                    st.rerun()

    selected = get_selection(key)
    if selected:
        st.caption(f"Selecionados ({len(selected)}): {', '.join(f'{n:02d}' for n in selected)}")
    else:
        st.caption("Nenhuma dezena selecionada.")
    return selected


def generate_combinations(fixed: list[int], groups: list[tuple[list[int], int]]) -> list[list[int]]:
    fixed_unique = sorted(set(fixed))

    if not groups:
        return [fixed_unique] if fixed_unique else []

    group_combos = []
    for numbers, pick in groups:
        unique = sorted(set(numbers))
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
        game = sorted(set(fixed_unique + [n for group in picks for n in group]))
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


def count_hits(game: list[int], drawn: set[int]) -> int:
    return len(set(game) & drawn)


def render_generator():
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

    if st.button("Gerar combinações", type="primary"):
        if not fixed and not groups:
            st.error("Selecione ao menos dezenas fixas ou configure um grupo variável.")
            return

        if groups and combo_count == 0:
            st.error("Revise os grupos variáveis: quantidade a escolher inválida.")
            return

        try:
            games = generate_combinations(fixed, groups)
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


def render_checker():
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


def main():
    st.set_page_config(page_title="Lotofácil — Gerador & Conferidor", page_icon="🎱", layout="wide")
    if LOGO_PATH.exists():
        st.image(str(LOGO_PATH), width=360)
    st.title("Lotofácil")
    st.markdown("Gerador de combinações e conferidor de jogos.")

    tab_gerador, tab_conferidor = st.tabs(["Gerador de Combinações", "Conferidor"])

    with tab_gerador:
        render_generator()

    with tab_conferidor:
        render_checker()


if __name__ == "__main__":
    main()
